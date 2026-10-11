# 麦当劳 MCP 接入说明

## 使用的 MCP Server

- **Server**: 麦当劳中国官方 MCP Server
- **接入地址**: `https://mcp.mcd.cn`
- **传输协议**: Streamable HTTP（JSON-RPC over HTTP POST）
- **鉴权**: 请求头 `Authorization: Bearer <MCD_MCP_TOKEN>`

## 使用的 Tool

| Tool | 用途 |
| --- | --- |
| `query-nearby-stores` | 按采样地址定位一家固定门店，拿到 `storeCode` / `beCode` |
| `query-meals` | 拉取该门店当前可售菜单，按关键词匹配篮子单品的 `productCode` |
| `calculate-price` | 对固定篮子（巨无霸单点 + 中薯条 + 中可乐）计算真实到手总价 |
| `now-time-info` | 采集时校准日期（写入快照的 `date` 字段） |

> 实际 Tool 名以官方 MCP 文档为准；首次运行会把 `tools/list` 结果存档到 `data/tool-schemas.json` 备查。

## 调用流程

```
initialize（建连）
  → tools/list（工具清单留档）
  → query-nearby-stores(address) → 固定门店 storeCode/beCode
  → query-meals(storeCode, beCode) → 菜单 → 关键词匹配篮子 productCode
  → calculate-price(items=[巨无霸×1, 中薯条×1, 中可乐×1]) → 到手总价
  → 追加写入 data/prices.jsonl → 指数 = 当日总价 / 基期总价 × 100
```

## 业务价值

把"今天麦当劳多少钱"变成一条可追踪、可验证的时间序列：
消费者能直观看到到手价的波动，开发者能拿到一份真实、每日更新的开放数据集
（`data/prices.jsonl`），可用于分析、教学或二次创作。

## 安全说明

- MCP Token 仅通过环境变量 `MCD_MCP_TOKEN` 传入，不写入代码、日志或 Git 仓库；
- 示例配置与文档中不包含任何真实凭据；
- 仓库的 GitHub Action 从 Secrets 读取 Token，日志中不打印。
