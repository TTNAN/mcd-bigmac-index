#!/usr/bin/env python3
"""巨无霸指数 · 每日价格快照.

通过麦当劳官方 MCP Server (Streamable HTTP) 采集固定篮子的到手总价,
追加写入 data/prices.jsonl. Token 只从环境变量 MCD_MCP_TOKEN 读取,
绝不落盘、不进仓库.

调用链 (到店自取口径, beType=1/orderType=1):
    query-nearby-stores -> query-meals -> calculate-price

用法:
    MCD_MCP_TOKEN=xxx python scripts/snapshot.py
"""

import datetime
import json
import os
import sys
import urllib.request

MCP_URL = os.environ.get("MCD_MCP_URL", "https://mcp.mcd.cn")
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")
# 采样门店定位 (到店自取)
CITY = os.environ.get("MCD_CITY", "上海市")
KEYWORD = os.environ.get("MCD_KEYWORD", "南京东路")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

# 篮子: (关键词, 排除词, 规格偏好)
BASKET = [
    ("巨无霸", ("套餐", "双层", "早餐"), None),
    ("薯条", ("套餐",), "中"),
    ("可乐", ("套餐", "雪碧", "美年达"), "中"),
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
            return json.loads(text[i:])
    # 兜底: 整个 text 当 JSON 试一次
    return json.loads(text)


def call_tool(session, name, arguments):
    data, session = rpc("tools/call",
                        {"name": name, "arguments": arguments}, session)
    if "error" in data:
        raise RuntimeError(f"工具 {name} 报错: {data['error']}")
    return extract_payload(data.get("result", {})), session


def match_product(meals, keyword, excludes, spec_pref):
    """meals: {code: {name, currentPrice, ...}}, 按关键词找最匹配的单品."""
    cands = []
    for code, m in meals.items():
        if not isinstance(m, dict):
            continue
        name = str(m.get("name") or "")
        if keyword not in name:
            continue
        if any(e in name for e in excludes):
            continue
        score = 0
        if spec_pref and spec_pref in name:
            score += 10
        if "套餐" in name:
            score -= 5
        cands.append((score, code, name, m))
    if not cands:
        return None
    cands.sort(key=lambda t: -t[0])
    return cands[0]


def main():
    if not TOKEN:
        print("缺少 MCD_MCP_TOKEN 环境变量, 退出.", file=sys.stderr)
        return 2

    # 1. 建连
    _, session = rpc("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "mcd-bigmac-index", "version": "0.1.0"},
    })
    try:
        rpc("notifications/initialized", {}, session)
    except Exception:
        pass
    print("已连接 MCP")

    # 2. 找一家固定门店 (取第一家在营业的)
    stores, session = call_tool(session, "query-nearby-stores", {
        "searchType": 2, "city": CITY, "keyword": KEYWORD, "beType": 1,
    })
    store_list = stores.get("data", []) if isinstance(stores, dict) else []
    store = next((s for s in store_list if s.get("businessStatus")), None)
    store = store or (store_list[0] if store_list else None)
    if not store:
        print("附近没有可用门店", file=sys.stderr)
        return 4
    store_code = store["storeCode"]
    store_name = store.get("storeName", "")
    print(f"采样门店: {store_name} ({store_code})")

    # 3. 拉菜单, 匹配篮子单品
    menu, session = call_tool(
        session, "query-meals", {"storeCode": store_code, **ORDER_CTX})
    meals = menu.get("data", {}).get("meals", {}) if isinstance(menu, dict) else {}
    if not isinstance(meals, dict) or not meals:
        print("菜单为空或结构异常", file=sys.stderr)
        return 5
    with open(os.path.join(DATA, "menu-latest.json"), "w",
              encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)

    basket = []
    for keyword, excludes, spec in BASKET:
        hit = match_product(meals, keyword, excludes, spec)
        if not hit:
            print(f"菜单中未找到 [{keyword}] (可能当前时段未售), 跳过今日.",
                  file=sys.stderr)
            return 5
        _, code, name, _ = hit
        basket.append({"productCode": code, "quantity": 1, "name": name})
        print(f"篮子成分: {name} ({code})")

    # 4. 算到手总价
    total_info, session = call_tool(session, "calculate-price", {
        "storeCode": store_code,
        **ORDER_CTX,
        "items": [{"productCode": b["productCode"], "quantity": 1}
                  for b in basket],
    })
    data = total_info.get("data", total_info) if isinstance(total_info, dict) \
        else {}
    total = None
    if isinstance(data, dict):
        for k in ("totalAmount", "total", "payAmount", "actualAmount",
                  "amount", "realPayAmount", "price", "totalPrice"):
            if isinstance(data.get(k), (int, float)):
                total = float(data[k])
                break
        if total is None:
            for k, v in data.items():
                if isinstance(v, (int, float)) and "amount" in k.lower():
                    total = float(v)
                    break
    # MCP 金额单位为分, 折算成元
    if total is not None and total > 200:
        total = round(total / 100, 2)
    print(f"篮子总价: {total} 元")
    if total is None:
        print(f"未能解析总价, 原始返回: "
              f"{json.dumps(total_info, ensure_ascii=False)[:400]}",
              file=sys.stderr)
        return 6

    # 5. 落盘
    today = datetime.date.today().isoformat()
    record = {"date": today, "store": store_name, "storeCode": store_code,
              "basket": basket, "total": total}
    with open(os.path.join(DATA, "prices.jsonl"), "a",
              encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"已写入 data/prices.jsonl ({today})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
