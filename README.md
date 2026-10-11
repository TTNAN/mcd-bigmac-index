# 🍔 巨无霸指数 · mcd-bigmac-index

> 一个汉堡，一面镜子。每天自动追踪麦当劳"三件套"的到手价，算给你看麦门通胀。

参赛作品：麦当劳程序员创意开发大赛（基于麦当劳官方 MCP Server）。

<!-- INDEX-START -->
## 📈 实时指数

*等待首次采集…*
<!-- INDEX-END -->

## 这是什么

《经济学人》1986 年发明了 Big Mac Index，用一个巨无霸的价格衡量各国货币购买力。
我们把它本土化、实时化：**每天上午 11 点**（午餐时段，巨无霸在售），机器人通过麦当劳官方 MCP 自动查询固定篮子
（巨无霸单点 + 中薯条 + 中可乐）的**真实到手价**，算出"巨无霸指数"并更新上面的曲线。

- 基期 = 首次采集日，指数 100
- 数据来自麦当劳官方 MCP Server 的实时接口，不是爬虫，不是估算
- 编制方法见 [methodology.md](methodology.md)

## 目录结构

```
├── scripts/
│   ├── snapshot.py      # 每日采集: 查门店 → 拉菜单 → 篮子计价 → 写 data/prices.jsonl
│   └── render.py        # 指数计算 + SVG 曲线生成 + README 自动更新
├── .github/workflows/
│   └── daily.yml        # 每天 09:00 (北京时间) 自动运行
├── data/
│   ├── prices.jsonl     # 每日原始快照 (append-only)
│   ├── index.json       # 基期信息
│   └── menu-latest.json # 最近一次菜单快照
├── assets/index.svg     # 自动生成的指数走势图
├── methodology.md       # 指数编制方法
├── MCP_INTEGRATION.md   # MCP 接入说明
└── CONTEST_DECLARATION.md
```

## 本地运行

```bash
# 1. 去 https://open.mcd.cn/mcp 用手机号登录, 点"激活"拿到 Token
# 2. 运行 (Token 只走环境变量, 不会写入任何文件)
MCD_MCP_TOKEN=你的token python scripts/snapshot.py
python scripts/render.py
```

定时任务需要把 `MCD_MCP_TOKEN` 加到仓库 Settings → Secrets and variables → Actions → New repository secret；
采样门店地址可在 Variables 里加 `MCD_ADDRESS` 覆盖默认值。

## 目标用户

- 好奇"我的早餐是不是变贵了"的麦门信徒
- 想给经济学作业找真实数据源的学生
- 喜欢把梗做成产品的程序员

## 参赛信息

- 活动：麦当劳程序员创意开发大赛
- 报名 Issue：（待提交后填写链接）
- 许可证：MIT
