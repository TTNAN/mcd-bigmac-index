#!/usr/bin/env python3
"""巨无霸指数 · 每日价格快照.

通过麦当劳官方 MCP Server (Streamable HTTP) 采集固定篮子的到手总价,
追加写入 data/prices.jsonl. Token 只从环境变量 MCD_MCP_TOKEN 读取,
绝不落盘、不进仓库.

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
# 采样地址: 用来定位一家固定门店, 可按需更换
ADDRESS = os.environ.get("MCD_ADDRESS", "上海市黄浦区南京东路353号")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

# 篮子: (关键词, 排除词, 规格偏好)
BASKET = [
    ("巨无霸", ("套餐", "双层", "早餐"), None),
    ("薯条", ("套餐",), "中"),
    ("可乐", ("套餐", "雪碧", "美年达"), "中"),
]


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
    # 尝试纯 JSON, 否则按 SSE 解析
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


def call_tool(session, name, arguments):
    data, session = rpc("tools/call",
                        {"name": name, "arguments": arguments}, session)
    if "error" in data:
        raise RuntimeError(f"工具 {name} 报错: {data['error']}")
    result = data.get("result", {})
    # tools/call 的结构化内容一般在 structuredContent, 文本在 content[]
    if isinstance(result, dict):
        if "structuredContent" in result:
            return result["structuredContent"], session
        parts = result.get("content", [])
        texts = [p.get("text", "") for p in parts
                 if isinstance(p, dict) and p.get("type") == "text"]
        if texts:
            try:
                return json.loads("".join(texts)), session
            except json.JSONDecodeError:
                return "".join(texts), session
    return result, session


def pick(d, *keys):
    """从字典里按多个候选键名取值, 兼容字段命名差异."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    # 大小写不敏感再试一次
    low = {str(k).lower(): v for k, v in d.items()}
    for k in keys:
        if k.lower() in low:
            return low[k.lower()]
    return None


def as_list(x):
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        for k in ("items", "list", "data", "stores", "meals", "products"):
            if isinstance(x.get(k), list):
                return x[k]
    return []


def match_product(items, keyword, excludes, spec_pref):
    """在菜单里按关键词找最匹配的单品."""
    cands = []
    for it in items:
        name = str(pick(it, "name", "productName", "title") or "")
        if keyword not in name:
            continue
        if any(e in name for e in excludes):
            continue
        score = 0
        if spec_pref and spec_pref in name:
            score += 10
        if "套餐" in name:
            score -= 5
        cands.append((score, name, it))
    if not cands:
        return None
    cands.sort(key=lambda t: -t[0])
    return cands[0][2]


def main():
    if not TOKEN:
        print("缺少 MCD_MCP_TOKEN 环境变量, 退出.", file=sys.stderr)
        return 2

    # 1. 建连
    data, session = rpc("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "mcd-bigmac-index", "version": "0.1.0"},
    })
    print(f"已连接 MCP, session={session[:12]}..." if session else "已连接 MCP")

    # 2. 工具清单留档 (诊断用)
    data, session = rpc("tools/list", {}, session)
    result = data.get("result", {})
    raw_tools = result.get("tools") if isinstance(result, dict) else None
    tools = [t.get("name") for t in as_list(raw_tools)
             if isinstance(t, dict)]
    with open(os.path.join(DATA, "tool-schemas.json"), "w",
              encoding="utf-8") as f:
        json.dump(data.get("result", data), f, ensure_ascii=False, indent=2)
    print(f"可用工具 {len(tools)} 个")

    need = {"query-nearby-stores", "query-meals", "calculate-price"}
    missing = need - set(tools)
    if missing:
        print(f"缺少关键工具: {missing}", file=sys.stderr)
        return 3

    # 3. 找一家固定门店
    stores, session = call_tool(session, "query-nearby-stores",
                               {"address": ADDRESS})
    store_list = as_list(stores)
    if not store_list:
        print(f"附近没有门店, 原始返回: {json.dumps(stores, ensure_ascii=False)[:300]}",
              file=sys.stderr)
        return 4
    store = store_list[0]
    store_code = pick(store, "storeCode", "store_code", "code", "id")
    be_code = pick(store, "beCode", "be_code")
    store_name = pick(store, "name", "storeName", "title")
    print(f"采样门店: {store_name} ({store_code})")

    # 4. 拉菜单, 匹配篮子单品
    menu, session = call_tool(session, "query-meals",
                              {"storeCode": store_code, "beCode": be_code})
    items = as_list(menu)
    with open(os.path.join(DATA, "menu-latest.json"), "w",
              encoding="utf-8") as f:
        json.dump(menu, f, ensure_ascii=False, indent=2)
    basket = []
    for keyword, excludes, spec in BASKET:
        prod = match_product(items, keyword, excludes, spec)
        if not prod:
            print(f"菜单中未找到 [{keyword}], 跳过今日.", file=sys.stderr)
            return 5
        code = pick(prod, "productCode", "product_code", "code", "id")
        name = pick(prod, "name", "productName", "title")
        basket.append({"productCode": code, "quantity": 1, "name": name})
        print(f"篮子成分: {name} ({code})")

    # 5. 算到手总价
    price_args = {"storeCode": store_code, "beCode": be_code,
                  "items": [{"productCode": b["productCode"],
                             "quantity": b["quantity"]} for b in basket]}
    # 配送地址缺失时用门店自取口径; 若接口要求 addressId 再补
    total_info, session = call_tool(session, "calculate-price", price_args)
    total = pick(total_info, "totalAmount", "total", "payAmount",
                 "actualAmount", "amount")
    if total is None and isinstance(total_info, dict):
        # 兜底: 在返回里找看起来像金额的数字字段
        for k, v in total_info.items():
            if isinstance(v, (int, float)) and "amount" in k.lower():
                total = v
                break
    print(f"篮子总价: {total}")

    # 6. 落盘
    today = datetime.date.today().isoformat()
    record = {
        "date": today,
        "store": store_name,
        "storeCode": store_code,
        "basket": basket,
        "total": total,
        "raw": total_info if isinstance(total_info, dict) else str(total_info),
    }
    with open(os.path.join(DATA, "prices.jsonl"), "a",
              encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"已写入 data/prices.jsonl ({today})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
