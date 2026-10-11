<p align="center"><img src="assets/banner.svg" alt="巨无霸指数" width="100%"></p>

# 🍔 巨无霸指数 · mcd-bigmac-index

> 一个汉堡，一面镜子。每天自动追踪麦当劳"三件套"的真实到手价，算给你看麦门通胀，也比给你看哪座城市的巨无霸最贵。

[![每日采集](https://github.com/TTNAN/mcd-bigmac-index/actions/workflows/daily.yml/badge.svg)](https://github.com/TTNAN/mcd-bigmac-index/actions/workflows/daily.yml)
![数据来源](https://img.shields.io/badge/数据来源-麦当劳官方_MCP-ffbc0d)
![依赖](https://img.shields.io/badge/依赖-纯标准库-1a9e54)
![License](https://img.shields.io/badge/license-MIT-blue)

**🌐 在线看板：https://ttnan.github.io/mcd-bigmac-index/** （打开即看城市价格榜、套餐省多少、逐项明细，每天自动更新）

参赛作品：麦当劳程序员创意开发大赛（基于麦当劳官方 MCP Server）。

## 🔎 首日发现（2026-10-11）

很多人以为麦当劳全国一个价。第一天的真实数据说：**不是。**

- **同一份三件套，城市间最多差 12.4%**：杭州、上海、深圳 ¥48.5，北京、广州、武汉、南京、西安 ¥50.5，重庆采样门店 ¥54.5。
- **一线城市不一定更贵**：上海、深圳和杭州同在最低一档，北京、广州反而贵 ¥2。
- **差价主要出在汉堡和薯条**：巨无霸 ¥25.5–29.0，中薯 ¥13.5–14.5；可乐多数城市都是 ¥9.5，只有重庆采样门店是 ¥11.0。
- **点套餐通常能省 25%–26%**：巨无霸三件套 ¥36.5–37.5，比单点便宜 ¥12–13；但重庆采样门店的套餐价和单点一样，都是 ¥54.5。

> 重庆这家门店的价格明显高出一截，可能是商场/特殊定价门店。每城目前只采一家门店，结论会随每日数据更新。

<!-- INDEX-START -->
## 📈 今日指数

**100.00**（2026-10-11 更新，较基期 2026-10-11 ▲ 0.00 点）

![巨无霸指数走势](assets/index.svg)
<!-- INDEX-END -->

<!-- CITIES-START -->
## 🗺️ 城市价格榜（2026-10-11）

同一份「巨无霸 + 中薯条 + 中可乐」，在不同城市核心商圈门店的**到手价**：

![城市价格榜](assets/cities.svg)

| # | 城市 | 采样门店 | 三件套单点到手价 | 巨无霸套餐 | 买套餐省 |
| --- | --- | --- | --- | --- | --- |
| 1 | 重庆 | 重庆金鹰财富中心餐厅 | ¥54.5 | ¥54.5 | 0% |
| 2 | 北京 | 北京新东安二号餐厅 | ¥50.5 | ¥37.5 | 26% |
| 3 | 广州 | 广州今日广场餐厅 | ¥50.5 | ¥37.5 | 26% |
| 4 | 武汉 | 武汉HAPPY站台餐厅(江汉路地铁H出口) | ¥50.5 | ¥37.5 | 26% |
| 5 | 南京 | 南京新百餐厅 | ¥50.5 | ¥37.5 | 26% |
| 6 | 西安 | 西安开元餐厅 | ¥50.5 | ¥37.5 | 26% |
| 7 | 成都 | 成都锦江区联升巷(京都大厦)餐厅 | ¥50.0 | ¥37.0 | 26% |
| 8 | 上海 | 上海黄浦悦荟广场餐厅 | ¥48.5 | ¥36.5 | 25% |
| 9 | 深圳 | 深圳华强北茂业餐厅 | ¥48.5 | ¥36.5 | 25% |
| 10 | 杭州 | 杭州上城区延安路东坡宾馆餐厅 | ¥48.5 | ¥36.5 | 25% |

> 今天最贵的是 **重庆**（¥54.5），最便宜的是 **杭州**（¥48.5），相差 12.4%。
<!-- CITIES-END -->

<!-- BASKET-START -->
## 🧺 指数篮子

<p align="center"><img src="docs/items/1100.png" width="140" alt="巨无霸"> <img src="docs/items/4810.png" width="140" alt="薯条"> <img src="docs/items/9900008751.gif" width="140" alt="可乐"></p>

<p align="center">巨无霸 ¥25.5 ＋ 薯条 ¥13.5 ＋ 可乐 ¥9.5 ＝ <b>¥48.5</b>（上海，到手价）</p>

图片与价格均来自麦当劳官方 MCP 实时菜单。
<!-- BASKET-END -->

## 💡 这是什么

1986 年，《经济学人》发明了 Big Mac Index：用同一个巨无霸在各国的价格，衡量货币的真实购买力。

我们把它**本土化、实时化、开源化**：

| | 《经济学人》原版 | 巨无霸指数（本项目） |
| --- | --- | --- |
| 比较对象 | 各国货币 | 中国各城市 + 时间序列 |
| 更新频率 | 一年两次 | **每天** |
| 价格口径 | 菜单标价 | **下单前官方核价的到手价**（`calculate-price`） |
| 数据 | 人工收集 | 麦当劳官方 MCP 接口自动采集，全部开放 |

它回答三个问题：

1. **麦当劳变贵了吗？** 以首次采集日为基期 100，每天看上海核心商圈同一份三件套的到手价涨跌。
2. **哪座城市的巨无霸最贵？** 每天同时采 10 个城市核心商圈门店，做一张城市价格榜。
3. **套餐到底帮你省了多少？** 把"单点三件套"和官方"巨无霸三件套"套餐放在一起比，告诉你点套餐能省几成。

## ⚙️ 怎么做到的

```
每天 11:00（北京时间，午餐时段，巨无霸在售）
        │  GitHub Actions 定时触发
        ▼
┌──────────────── 每个城市跑一遍 ────────────────┐
│ query-nearby-stores  找核心商圈一家营业中的门店 │
│ query-meals          拉实时菜单，匹配篮子单品   │
│ calculate-price      官方核价，得到真实到手价   │
└────────────────────────────────────────────────┘
        ▼
data/prices.jsonl  主序列（上海）    data/cities/日期.json  当日 10 城快照
        ▼
scripts/render.py → 封面图 / 走势图 / 城市榜 SVG + 自动改写本 README
```

- **不是爬虫，不是估算**：所有价格来自麦当劳官方 MCP 的实时接口，到手价由官方 `calculate-price` 计算。
- **零依赖**：只用 Python 标准库，clone 下来就能跑。
- **开放数据**：每天的原始快照都提交在 `data/` 目录，任何人都可以拿去做分析、写作业、画图。
- 编制方法和局限性见 [methodology.md](methodology.md)。

## 🙋 谁会用到

- 好奇"我常吃的那份是不是又涨价了"的麦门信徒
- 想知道换城市生活，快餐成本差多少的打工人
- 需要真实、可复现、按天更新的价格数据做经济学作业的学生
- 想看一个"把梗做成产品"的 MCP 实战案例的开发者

## 🚀 自己跑一份

```bash
# 1. 去 https://open.mcd.cn/mcp 用手机号登录，点"激活"拿到 Token
# 2. 采集 + 出图（Token 只走环境变量，不会写入任何文件）
MCD_MCP_TOKEN=你的token python scripts/snapshot.py
python scripts/render.py
```

换城市或商圈：

```bash
MCD_CITIES="上海市:南京东路,北京市:王府井,长沙市:五一广场" MCD_MCP_TOKEN=你的token python scripts/snapshot.py
```

让它每天自动更新：Fork 本仓库 → Settings → Secrets and variables → Actions → New repository secret，名称 `MCD_MCP_TOKEN`。
想换采样城市，在 Variables 里加 `MCD_CITIES`（格式同上）。

## 📁 目录结构

```
├── scripts/
│   ├── snapshot.py          # 每日采集：门店 → 菜单 → 官方核价，10 城
│   └── render.py            # 指数计算 + 封面/走势/城市榜 SVG + README 自动更新
├── .github/workflows/
│   └── daily.yml            # 每天 11:00（北京时间）自动运行
├── data/
│   ├── prices.jsonl         # 主序列（上海），每天一行
│   ├── cities/YYYY-MM-DD.json  # 每日多城市快照
│   └── cities-latest.json   # 最近一次多城市快照
├── assets/                  # 自动生成的图（banner / index / cities）
├── methodology.md           # 指数编制方法与局限性
├── MCP_INTEGRATION.md       # MCP 接入说明
└── CONTEST_DECLARATION.md
```

## 🔌 用到的 MCP 工具

| 工具 | 用途 |
| --- | --- |
| `query-nearby-stores` | 按城市 + 商圈关键词找营业中的门店 |
| `query-meals` | 拉门店实时菜单，按名称匹配篮子单品和巨无霸套餐 |
| `calculate-price` | 官方核价，返回到手总价（单位：分） |

## 参赛信息

- 活动：麦当劳程序员创意开发大赛
- 报名 Issue：https://github.com/M-China/mcd-developer-innovation-challenge/issues/408
- 许可证：MIT

> 指数仅供娱乐与观察，不构成任何消费或投资建议。如果你觉得有意思，点个 ⭐ 让更多人看到。
