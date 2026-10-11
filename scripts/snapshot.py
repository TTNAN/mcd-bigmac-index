#!/usr/bin/env python3
"""巨无霸指数 · 每日价格快照.

通过麦当劳官方 MCP Server (Streamable HTTP) 采集固定篮子的到手总价,
追加写入 data/prices.jsonl. Token 只从环境变量 MCD_MCP_TOKEN 读取,
绝不落盘、不进仓库.

调用链 (到店自取口径, beType=1/orderType=1), 每个采样城市同商圈最多 3 家门店各跑一遍:
    query-nearby-stores -> query-meals -> calculate-price

产出:
    data/prices.jsonl       主序列 (基准城市), 每天一行, append-only
    data/cities/日期.json    当天全部城市的篮子价、单品价、套餐价
    data/cities-latest.json 最近一次多城市快照 (README 城市榜读这个)

用法:
    MCD_MCP_TOKEN=xxx python scripts/snapshot.py
"""

import datetime
import json
import os
import sys
import urllib.error
import urllib.request

MCP_URL = os.environ.get("MCD_MCP_URL", "https://mcp.mcd.cn")
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")
# 采样城市: (城市, 商圈关键词). 第一个城市是指数主序列的基准门店.
# 可用环境变量 MCD_CITIES 覆盖, 格式 "上海市:南京东路,北京市:王府井"
DEFAULT_CITIES = [
    ("上海市", "南京东路"), ("北京市", "王府井"), ("广州市", "天河城"),
    ("深圳市", "华强北"), ("杭州市", "湖滨"), ("成都市", "春熙路"),
    ("重庆市", "解放碑"), ("武汉市", "江汉路"), ("南京市", "新街口"),
    ("西安市", "钟楼"),
]
_env_cities = os.environ.get("MCD_CITIES", "").strip()
CITIES = ([tuple(p.split(":", 1)) for p in _env_cities.split(",") if ":" in p]
          or DEFAULT_CITIES)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

# 篮子: (关键词, 排除词, 规格偏好)
BASKET = [
    ("巨无霸", ("套餐", "双层", "早餐", "随心配", "1+1", "组合"), None),
    ("薯条", ("套餐", "随心配", "1+1", "组合", "分享"), "中"),
    ("可乐", ("套餐", "雪碧", "美年达", "零", "随心配", "1+1", "组合"), "中"),
]

ORDER_CTX = {"orderType": 1, "beType": 1}  # 到店自取


def rpc(method, params=None, session=None, timeout=30):
    """发一次 JSON-RPC, 兼容纯 JSON 与 SSE 两种返回."""
    body = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    ).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {TOKEN}",
    }
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(MCP_URL, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
        new_session = resp.headers.get("Mcp-Session-Id") or session
    try:
        return json.loads(raw), new_session
    except json.JSONDecodeError:
        for line in raw.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                try:
                    return json.loads(line[5:].strip()), new_session
                except json.JSONDecodeError:
                    continue
    raise RuntimeError(f"无法解析 MCP 返回: {raw[:200]}")


def extract_payload(result):
    """从 tools/call 结果里抠出业务 JSON.

    麦当劳 MCP 的 content[0].text 是"说明文字 + JSON"混排,
    JSON 部分形如 {"success":true,...,"data":...}.
    """
    if isinstance(result, dict) and "structuredContent" in result:
        return result["structuredContent"]
    texts = []
    if isinstance(result, dict):
        for p in result.get("content", []):
            if isinstance(p, dict) and p.get("type") == "text":
                texts.append(p.get("text", ""))
    text = "".join(texts)
    for marker in ('{"success"', '{"code"'):
        i = text.find(marker)
        if i >= 0:
            return json.JSONDecoder().raw_decode(text[i:])[0]
    # 兜底: 整个 text 当 JSON 试一次
    return json.loads(text)


USE_MCPCALL = os.environ.get("MCD_USE_MCPCALL") == "1"


def call_tool(session, name, arguments):
    if USE_MCPCALL:  # 本地调试: 走已配置好的 MCP 客户端, 不需要明文 Token
        import subprocess
        out = subprocess.run(["mcpcall", "call", "mcd", name,
                              json.dumps(arguments, ensure_ascii=False)],
                             capture_output=True, text=True, timeout=90)
        return extract_payload({"content": [{"type": "text",
                                             "text": out.stdout}]}), session
    data, session = rpc("tools/call",
                        {"name": name, "arguments": arguments}, session)
    if "error" in data:
        raise RuntimeError(f"工具 {name} 报错: {data['error']}")
    return extract_payload(data.get("result", {})), session


def match_product(meals, keyword, excludes, spec_pref, need=None):
    """meals: {code: {name, currentPrice, ...}}, 按关键词找最匹配的单品."""
    cands = []
    for code, m in meals.items():
        if not isinstance(m, dict):
            continue
        name = str(m.get("name") or "")
        if keyword not in name:
            continue
        if need and need not in name:
            continue
        if any(e in name for e in excludes):
            continue
        score = 0
        if spec_pref and spec_pref in name:
            score += 10
        score -= len(name) * 0.1  # 名字越短越"标准"
        cands.append((score, code, name, m))
    if not cands:
        return None
    cands.sort(key=lambda t: -t[0])
    return cands[0]


def yuan(v):
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


STORES_PER_CITY = max(1, int(os.environ.get("MCD_STORES_PER_CITY", "3")))


def median(vals):
    vals = sorted(v for v in vals if isinstance(v, (int, float)))
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else round((vals[n // 2 - 1] + vals[n // 2]) / 2, 2)


def snapshot_store(session, city, store):
    """采一家门店: 菜单匹配篮子 + 官方核价 + 套餐对照. 返回 (dict | None, session)."""
    store_code = store["storeCode"]
    name = store.get("storeName", store_code)
    menu, session = call_tool(
        session, "query-meals", {"storeCode": store_code, **ORDER_CTX})
    meals = menu.get("data", {}).get("meals", {}) if isinstance(menu, dict) else {}
    if not isinstance(meals, dict) or not meals:
        print(f"[{city}] {name} 菜单为空, 跳过")
        return None, session

    basket = []
    for keyword_, excludes, spec in BASKET:
        hit = match_product(meals, keyword_, excludes, spec)
        if not hit:
            print(f"[{city}] {name} 未找到 [{keyword_}] (可能当前时段未售), 跳过")
            return None, session
        _, code, pname, m = hit
        basket.append({"productCode": code, "quantity": 1, "name": pname,
                       "menuPrice": yuan(m.get("currentPrice")),
                       "image": m.get("image")})

    priced, session = call_tool(session, "calculate-price", {
        "storeCode": store_code, **ORDER_CTX,
        "items": [{"productCode": b["productCode"], "quantity": 1}
                  for b in basket],
    })
    data = priced.get("data", {}) if isinstance(priced, dict) else {}
    total = data.get("price") if isinstance(data, dict) else None  # 单位: 分
    if not isinstance(total, (int, float)):
        print(f"[{city}] {name} 未能解析总价: {json.dumps(priced, ensure_ascii=False)[:300]}",
              file=sys.stderr)
        return None, session

    # 对照组: 官方「巨无霸三件套」套餐的菜单价, 用来算"套餐帮你省多少"
    combo = match_product(meals, "巨无霸", ("双层", "早餐", "1+1", "随心配"),
                          "", need="三件套")
    combo_rec = None
    if combo:
        _, ccode, cname, cm = combo
        combo_rec = {"productCode": ccode, "name": cname,
                     "menuPrice": yuan(cm.get("currentPrice")),
                     "image": cm.get("image")}
    return {"store": name, "storeCode": store_code,
            "address": store.get("address", ""),
            "hours": f'{store.get("businessStartTime", "")}-{store.get("businessEndTime", "")}',
            "basket": basket, "total": round(total / 100, 2),
            "combo": combo_rec}, session


def snapshot_city(session, city, keyword):
    """采一个城市: 同商圈最多 STORES_PER_CITY 家营业中门店, 城市价取中位数.

    返回 (record | None, session). record 顶层的 store/basket/combo 为第一家
    (锚定门店, 用于主序列保持时间可比), total/basket 单价/套餐价为多店中位数,
    stores 列出每家门店的明细.
    """
    stores, session = call_tool(session, "query-nearby-stores", {
        "searchType": 2, "city": city, "keyword": keyword, "beType": 1,
    })
    store_list = stores.get("data", []) if isinstance(stores, dict) else []
    open_ = [s for s in store_list if s.get("businessStatus")] or store_list
    if not open_:
        print(f"[{city}] 附近没有可用门店, 跳过")
        return None, session

    samples = []
    for st in open_:
        if len(samples) >= STORES_PER_CITY:
            break
        try:
            rec, session = snapshot_store(session, city, st)
        except Exception as e:  # 单店失败换下一家
            print(f"[{city}] {st.get('storeName')} 采集失败: {e}", file=sys.stderr)
            rec = None
        if rec:
            samples.append(rec)
    if not samples:
        return None, session

    anchor = samples[0]
    basket = []
    for i, b in enumerate(anchor["basket"]):
        b = dict(b)
        b["anchorPrice"] = b["menuPrice"]
        b["menuPrice"] = median(s["basket"][i]["menuPrice"] for s in samples
                                if len(s["basket"]) > i)
        basket.append(b)
    combo = None
    combos = [s["combo"]["menuPrice"] for s in samples if s.get("combo")]
    if anchor.get("combo") and combos:
        combo = dict(anchor["combo"], menuPrice=median(combos),
                     anchorPrice=anchor["combo"]["menuPrice"])

    rec = {"city": city, "keyword": keyword,
           "store": anchor["store"], "storeCode": anchor["storeCode"],
           "address": anchor["address"], "hours": anchor["hours"],
           "anchorTotal": anchor["total"],
           "total": median(s["total"] for s in samples),
           "basket": basket, "combo": combo,
           "stores": [{k: s[k] for k in ("store", "storeCode", "address", "hours", "total")}
                      | {"comboPrice": (s.get("combo") or {}).get("menuPrice"),
                         "items": {b["name"]: b["menuPrice"] for b in s["basket"]}}
                      for s in samples]}
    print(f"[{city}] {len(samples)} 家门店, 中位数 {rec['total']} 元 "
          "(" + ", ".join(s["store"].replace("麦当劳", "") + " " + str(s["total"]) for s in samples) + ")"
          + (f" | 套餐 {combo['menuPrice']} 元" if combo else ""))
    return rec, session


def main():
    if not TOKEN and not USE_MCPCALL:
        print("缺少 MCD_MCP_TOKEN 环境变量, 退出.", file=sys.stderr)
        return 2

    session = None
    if not USE_MCPCALL:
        try:
            _, session = rpc("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcd-bigmac-index", "version": "0.2.0"},
            })
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            hint = "Token 无效或已过期, 请到 open.mcd.cn/mcp 重新激活并更新仓库 Secret" \
                if e.code in (401, 403) else "MCP 服务暂时不可用"
            print(f"::error::连接麦当劳 MCP 失败 HTTP {e.code}: {hint}. {body}")
            return 1
        except Exception as e:  # noqa: BLE001
            print(f"::error::连接麦当劳 MCP 失败: {type(e).__name__}: {e}")
            return 1
        try:
            rpc("notifications/initialized", {}, session)
        except Exception:
            pass
        print("已连接 MCP")

    today = os.environ.get("SNAPSHOT_DATE") or \
        datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).date().isoformat()
    records = []
    for city, keyword in CITIES:
        try:
            rec, session = snapshot_city(session, city, keyword)
        except Exception as e:  # 单个城市失败不影响其它城市
            print(f"::warning::[{city}] 采集失败: {type(e).__name__}: {str(e)[:200]}")
            rec = None
        if rec:
            records.append(rec)

    if not records:
        print("::warning::今天没有采到任何城市 (可能不在午餐时段或接口异常), 不写数据.")
        return 0

    # 多城市快照
    os.makedirs(os.path.join(DATA, "cities"), exist_ok=True)
    snap = {"date": today, "cities": records}
    for p in (os.path.join(DATA, "cities", f"{today}.json"),
              os.path.join(DATA, "cities-latest.json")):
        with open(p, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)

    # 主序列: 只认基准城市, 同一天只保留一条
    base_city = CITIES[0][0]
    main_rec = next((r for r in records if r["city"] == base_city), None)
    if main_rec:
        path = os.path.join(DATA, "prices.jsonl")
        rows = []
        if os.path.exists(path):
            rows = [l for l in open(path, encoding="utf-8")
                    if l.strip() and json.loads(l).get("date") != today]
        main_row = {k: v for k, v in main_rec.items() if k != "stores"}
        main_row["total"] = main_rec.get("anchorTotal", main_rec["total"])  # 主序列只认锚定门店
        rows.append(json.dumps({"date": today, **main_row},
                               ensure_ascii=False) + "\n")
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(rows)
    print(f"已写入 {len(records)} 个城市 ({today})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
