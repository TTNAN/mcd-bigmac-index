#!/usr/bin/env python3
"""巨无霸指数 · 图表渲染.

读取 data/prices.jsonl 与 data/cities-latest.json, 生成:
    assets/banner.svg   封面图 (今日指数 + 城市价差 + 套餐省多少)
    assets/index.svg    指数走势图
    assets/cities.svg   城市巨无霸篮子价格榜
并更新 README.md 中的 INDEX / CITIES 区块.
纯标准库, 无第三方依赖.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)

FONT = "'PingFang SC','Microsoft YaHei','Noto Sans CJK SC','Source Han Sans SC',sans-serif"
RED, YELLOW, GREEN, BG = "#e4002b", "#ffbc0d", "#1a9e54", "#141414"


def short_city(c):
    return c[:-1] if c.endswith("市") else c


# ---------------------------------------------------------------- data
def load_series():
    path = os.path.join(DATA, "prices.jsonl")
    if not os.path.exists(path):
        return []
    rows = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            total = r.get("total")
            if isinstance(total, (int, float)) and total > 0:
                rows.append((r["date"], float(total)))
        except (json.JSONDecodeError, KeyError):
            continue
    rows.sort(key=lambda t: t[0])
    return rows


def load_cities():
    path = os.path.join(DATA, "cities-latest.json")
    if not os.path.exists(path):
        return None
    snap = json.load(open(path, encoding="utf-8"))
    cities = [c for c in snap.get("cities", []) if c.get("total")]
    cities.sort(key=lambda c: -c["total"])
    snap["cities"] = cities
    return snap if cities else None


def to_index(rows):
    if not rows:
        return []
    base = rows[0][1]
    return [(d, round(v / base * 100, 2)) for d, v in rows]


def combo_saving(c):
    """巨无霸套餐 vs 单点三件套, 省多少 (%)."""
    combo = (c.get("combo") or {}).get("menuPrice")
    if not combo or not c.get("total"):
        return None
    return round((1 - combo / c["total"]) * 100, 1)


# ---------------------------------------------------------------- charts
def svg_index(series, path):
    W, H = 800, 320
    PL, PR, PT, PB = 56, 24, 48, 40
    vals = [v for _, v in series]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 2.0)
    lo, hi = lo - span * 0.3, hi + span * 0.3

    def x(i):
        if len(series) == 1:
            return (PL + W - PR) / 2
        return PL + (W - PL - PR) * (i / (len(series) - 1))

    def y(v):
        return PT + (H - PT - PB) * (1 - (v - lo) / (hi - lo))

    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(series))
    last, first = series[-1][1], series[0][1]
    delta = last - first
    color = RED if delta >= 0 else GREEN  # 涨红跌绿, A 股规矩
    arrow = "▲" if delta >= 0 else "▼"

    ticks = ""
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        yy = y(v)
        ticks += (f'<line x1="{PL}" y1="{yy:.1f}" x2="{W-PR}" y2="{yy:.1f}" stroke="#2a2a2a" stroke-dasharray="4,4"/>'
                  f'<text x="{PL-8}" y="{yy+4:.1f}" text-anchor="end" font-size="11" fill="#888">{v:.1f}</text>')
    step = max(1, len(series) // 8)
    xlabels = "".join(
        f'<text x="{x(i):.1f}" y="{H-PB+20}" text-anchor="middle" font-size="11" fill="#888">{series[i][0][5:]}</text>'
        for i in range(0, len(series), step))
    area = ""
    if len(series) > 1:
        area = (f'<polygon points="{PL},{H-PB} {pts} {x(len(series)-1):.1f},{H-PB}" fill="{color}" opacity="0.15"/>'
                f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>')
    note = ("首日为基期 = 100，曲线将每天自动延长" if len(series) == 1
            else f"较基期 {arrow} {abs(delta):.2f} 点")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>
<text x="{PL}" y="30" font-size="16" fill="{YELLOW}" font-weight="bold">巨无霸指数走势（基期 = 100）</text>
<text x="{W-PR}" y="30" text-anchor="end" font-size="12" fill="#888">{series[0][0]} → {series[-1][0]}</text>
{ticks}{area}
<circle cx="{x(len(series)-1):.1f}" cy="{y(last):.1f}" r="5" fill="{color}"/>
<text x="{x(len(series)-1):.1f}" y="{y(last)-12:.1f}" text-anchor="middle" font-size="14" fill="#fff" font-weight="bold">{last:.2f}</text>
{xlabels}
<text x="{W-PR}" y="{H-8}" text-anchor="end" font-size="11" fill="#777">{note} · 数据来自麦当劳官方 MCP</text>
</svg>"""
    open(path, "w", encoding="utf-8").write(svg)


def svg_cities(snap, path):
    cities = snap["cities"]
    W, ROW, PT, PB = 800, 40, 70, 44
    H = PT + ROW * len(cities) + PB
    LX, BX, BW = 30, 120, 520
    hi = max(c["total"] for c in cities)
    lo = min(c["total"] for c in cities)
    avg = sum(c["total"] for c in cities) / len(cities)
    floor = lo * 0.85

    def bw(v):
        return BW * (v - floor) / (hi - floor)

    rows = ""
    for i, c in enumerate(cities):
        yy = PT + i * ROW
        col = RED if c["total"] == hi else (GREEN if c["total"] == lo else YELLOW)
        rows += (f'<text x="{LX}" y="{yy+25}" font-size="15" fill="#ddd">{i+1}. {short_city(c["city"])}</text>'
                 f'<rect x="{BX}" y="{yy+8}" width="{bw(c["total"]):.1f}" height="24" rx="6" fill="{col}" opacity="0.9"/>'
                 f'<text x="{BX+bw(c["total"])+10:.1f}" y="{yy+26}" font-size="15" fill="#fff" font-weight="bold">¥{c["total"]:.1f}</text>')
    ax = BX + bw(avg)
    gap = (hi - lo) / lo * 100
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<rect width="{W}" height="{H}" rx="14" fill="{BG}"/>
<text x="{LX}" y="34" font-size="18" fill="{YELLOW}" font-weight="bold">同一份三件套，各城市到手价（{snap["date"]}）</text>
<text x="{LX}" y="56" font-size="12" fill="#888">巨无霸单点 + 中薯条 + 中可乐 · 到店自取 · 每城取核心商圈一家门店</text>
{rows}
<line x1="{ax:.1f}" y1="{PT}" x2="{ax:.1f}" y2="{H-PB+6}" stroke="#fff" stroke-dasharray="3,4" opacity="0.5"/>
<text x="{ax:.1f}" y="{H-PB+22}" text-anchor="middle" font-size="11" fill="#aaa">平均 ¥{avg:.1f}</text>
<text x="{W-24}" y="{H-12}" text-anchor="end" font-size="11" fill="#777">最贵比最便宜高 {gap:.1f}% · 数据来自麦当劳官方 MCP</text>
</svg>"""
    open(path, "w", encoding="utf-8").write(svg)


def svg_banner(series, snap, path):
    W, H = 1200, 420
    idx = series[-1][1] if series else 100.0
    date = series[-1][0] if series else (snap or {}).get("date", "")
    base = None
    stats = []
    if snap:
        cities = snap["cities"]
        base = cities[0] if False else next(
            (c for c in cities if c["city"] == "上海市"), cities[0])
        hi, lo = cities[0], cities[-1]
        stats.append(("最贵城市", f'{short_city(hi["city"])} ¥{hi["total"]:.1f}'))
        stats.append(("最便宜城市", f'{short_city(lo["city"])} ¥{lo["total"]:.1f}'))
        savings = [s for s in (combo_saving(c) for c in cities) if s is not None]
        if savings:
            stats.append(("买套餐比单点省", f"{sum(savings)/len(savings):.0f}%"))
    price = f'¥{base["total"]:.1f}' if base else ""
    cards = ""
    for i, (k, v) in enumerate(stats):
        cx = 640 + (i % 3) * 0
        cy = 120 + i * 92
        cards += (f'<rect x="680" y="{cy}" width="470" height="76" rx="14" fill="#ffffff" opacity="0.06"/>'
                  f'<text x="708" y="{cy+31}" font-size="18" fill="#bbb">{k}</text>'
                  f'<text x="708" y="{cy+61}" font-size="26" fill="#fff" font-weight="bold">{v}</text>')
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2b0a06"/><stop offset="1" stop-color="#120404"/></linearGradient>
<linearGradient id="t" x1="0" x2="1"><stop offset="0" stop-color="#ffcf3f"/><stop offset="1" stop-color="#ff7a00"/></linearGradient></defs>
<rect width="{W}" height="{H}" rx="24" fill="url(#g)"/>
<path d="M60 330 q60 -170 120 0 q60 -170 120 0" fill="none" stroke="{YELLOW}" stroke-width="18" stroke-linecap="round" opacity="0.18"/>
<text x="60" y="88" font-size="22" fill="{YELLOW}" letter-spacing="6">MCD BIG MAC INDEX · 麦门通胀观测站</text>
<text x="60" y="170" font-size="72" fill="url(#t)" font-weight="bold">巨无霸指数</text>
<text x="60" y="262" font-size="96" fill="#fff" font-weight="bold">{idx:.2f}</text>
<text x="330" y="262" font-size="22" fill="#aaa">上海三件套 {price}</text>
<text x="60" y="320" font-size="20" fill="#ccc">一个汉堡，一面镜子 · 每天 11:00 通过麦当劳官方 MCP 自动采集真实到手价</text>
<text x="60" y="372" font-size="16" fill="#888">更新于 {date} · 致敬《经济学人》Big Mac Index (1986)</text>
{cards}
</svg>"""
    open(path, "w", encoding="utf-8").write(svg)


# ---------------------------------------------------------------- README
def replace_block(text, name, block):
    start, end = f"<!-- {name}-START -->", f"<!-- {name}-END -->"
    if start in text and end in text:
        return text.split(start)[0] + start + "\n" + block + "\n" + end + text.split(end, 1)[1]
    return text


def index_block(series, snap):
    date, val = series[-1]
    base_date = series[0][0]
    delta = val - 100
    arrow = "▲" if delta >= 0 else "▼"
    lines = ["## 📈 今日指数", "",
             f"**{val:.2f}**（{date} 更新，较基期 {base_date} {arrow} {abs(delta):.2f} 点）", "",
             "![巨无霸指数走势](assets/index.svg)"]
    return "\n".join(lines)


def cities_block(snap):
    cities = snap["cities"]
    lines = [f"## 🗺️ 城市价格榜（{snap['date']}）", "",
             "同一份「巨无霸 + 中薯条 + 中可乐」，在不同城市核心商圈门店的**到手价**：", "",
             "![城市价格榜](assets/cities.svg)", "",
             "| # | 城市 | 采样门店 | 三件套单点到手价 | 巨无霸套餐 | 买套餐省 |",
             "| --- | --- | --- | --- | --- | --- |"]
    for i, c in enumerate(cities):
        combo = c.get("combo") or {}
        cp = f'¥{combo["menuPrice"]:.1f}' if combo.get("menuPrice") else "—"
        sv = combo_saving(c)
        lines.append(f'| {i+1} | {short_city(c["city"])} | {c["store"].replace("麦当劳", "")} | '
                     f'¥{c["total"]:.1f} | {cp} | {f"{sv:.0f}%" if sv is not None else "—"} |')
    hi, lo = cities[0], cities[-1]
    gap = (hi["total"] - lo["total"]) / lo["total"] * 100
    lines += ["", f"> 今天最贵的是 **{short_city(hi['city'])}**（¥{hi['total']:.1f}），"
              f"最便宜的是 **{short_city(lo['city'])}**（¥{lo['total']:.1f}），相差 {gap:.1f}%。"]
    return "\n".join(lines)


def basket_block(snap):
    base = next((c for c in snap["cities"] if c["city"] == "上海市"), snap["cities"][0])
    cells, names = [], []
    for b in base["basket"]:
        img = b.get("image")
        if img:
            cells.append(f'<img src="{img}" width="140" alt="{b["name"]}">')
        price = f' ¥{b["menuPrice"]:.1f}' if b.get("menuPrice") else ""
        names.append(f'{b["name"]}{price}')
    return ("## 🧺 指数篮子\n\n<p align=\"center\">" + " ".join(cells) + "</p>\n\n<p align=\"center\">"
            + " ＋ ".join(names) + f" ＝ <b>¥{base['total']:.1f}</b>（{short_city(base['city'])}，到手价）</p>\n\n"
            "图片与价格均来自麦当劳官方 MCP 实时菜单。")


def main():
    rows = load_series()
    snap = load_cities()
    if not rows and not snap:
        print("暂无数据, 跳过渲染.")
        return
    series = to_index(rows)
    if series:
        svg_index(series, os.path.join(ASSETS, "index.svg"))
    if snap:
        svg_cities(snap, os.path.join(ASSETS, "cities.svg"))
    svg_banner(series, snap, os.path.join(ASSETS, "banner.svg"))
    print("图表已生成")

    path = os.path.join(ROOT, "README.md")
    text = open(path, encoding="utf-8").read()
    if series:
        text = replace_block(text, "INDEX", index_block(series, snap))
    if snap:
        text = replace_block(text, "CITIES", cities_block(snap))
        text = replace_block(text, "BASKET", basket_block(snap))
    open(path, "w", encoding="utf-8").write(text)
    print("README 已更新")


if __name__ == "__main__":
    main()
