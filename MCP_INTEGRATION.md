# 麦当劳 MCP 接入说明

## 使用的 MCP Server

- **Server**: 麦当劳中国官方 MCP Server
- **接入地址**: `https://mcp.mcd.cn`
- **传输协议**: Streamable HTTP（JSON-RPC over HTTP POST）
- **鉴权**: 请求头 `Authorization: Bearer <MCD_MCP_TOKEN>`

## 使用的 Tool

| Tool | 用途 |
| --- | --- |
| `query-nearby-stores` | 按「城市 + 核心商圈关键词」搜索门店（`searchType=2`），取前 3 家营业中门店的 `storeCode` |
| `query-meals` | 拉取每家门店当前可售菜单（到店自取 `orderType=1, beType=1`），按名称匹配篮子单品和「巨无霸三件套」套餐 |
| `calculate-price` | 对篮子（巨无霸 ×1 + 中薯条 ×1 + 中可乐 ×1）做官方核价，返回到手总价（单位：分） |

## 调用流程

```
initialize（建连，拿 Mcp-Session-Id）
  │
  ├─ for 城市 in 10 个采样城市（上海·南京东路 / 北京·王府井 / 广州·天河城 / 深圳·华强北 / 杭州·湖滨 /
  │                         成都·春熙路 / 重庆·解放碑 / 武汉·江汉路 / 南京·新街口 / 西安·钟楼）:
  │     query-nearby-stores(city, keyword) → 营业中门店列表
  │     for 门店 in 前 3 家可用门店（某店缺货则顺延下一家）:
  │         query-meals(storeCode) → 菜单 → 匹配 巨无霸 / 中薯条 / 中可乐 / 巨无霸三件套
  │         calculate-price(items=[巨无霸×1, 中薯条×1, 中可乐×1]) → 该店到手价
  │     城市价 = 3 家门店到手价的中位数；套餐价同样取中位数
  │
  ├─ data/cities/日期.json、data/cities-latest.json ← 当天 10 城 × 3 店明细
  ├─ data/prices.jsonl ← 主序列：上海第一家锚定门店的到手价（保证时间可比）
  │
  └─ scripts/render.py → 指数 = 当日锚定价 / 基期锚定价 × 100
                       → 封面图 / 走势图 / 城市榜 SVG、README 动态区块、在线看板 docs/data.json
```

一次完整采集约 10 次门店搜索 + 30 次菜单查询 + 30 次官方核价。单店失败自动换下一家，单城失败不影响其它城市。

## 业务价值

把「今天麦当劳多少钱」变成一份可追踪、可验证的开放数据：

- **消费者**：一眼看到同一份巨无霸在不同城市、不同门店差多少，点套餐能省几成；
- **学生 / 研究者**：每天自动更新的 10 城 × 3 店真实到手价，可直接用于经济学作业或分析；
- **开发者**：一个完整的「MCP 多工具串联 → 数据落盘 → 自动出图 → 静态网页」实战样例。

在线看板：https://ttnan.github.io/mcd-bigmac-index/

## 安全说明

- MCP Token 仅通过环境变量 `MCD_MCP_TOKEN` 传入，不写入代码、日志或 Git 仓库；
- 示例配置与文档中不包含任何真实凭据；
- 仓库的 GitHub Action 从 Secrets 读取 Token，日志中不打印。
