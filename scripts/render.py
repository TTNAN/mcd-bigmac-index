#!/usr/bin/env python3
"""巨无霸指数 · 图表渲染.

读取 data/prices.jsonl, 计算指数序列, 生成 assets/index.svg,
并更新 README.md 中 <!-- INDEX-START --> ... <!-- INDEX-END --> 区块.
纯标准库, 无第三方依赖.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
ASSETS = os.path.join(ROOT, "assets")
os.makedirs(ASSETS, exist_ok=True)


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


def to_index(rows):
    if not rows:
        return []
    base = rows[0][1]
    return [(d, round(v / base * 100, 2)) for d, v in rows]


def svg_chart(series, path):
    W, H = 760, 300
    PL, PR, PT, PB = 56, 20, 24, 36
    vals = [v for _, v in series]
    lo, hi = min(vals), max(vals)
    span = max(hi - lo, 0.01)
    lo -= span * 0.15
    hi += span * 0.15

    def x(i):
        return PL + (W - PL - PR) * (i / max(len(series) - 1, 1))

    def y(v):
        return PT + (H - PT - PB) * (1 - (v - lo) / (hi - lo))

    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, (_, v) in enumerate(series))
    area = f"{PL},{H-PB} " + pts + f" {x(len(series)-1):.1f},{H-PB}"

    # y 轴刻度
    ticks = ""
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        yy = y(v)
        ticks += (f'<line x1="{PL}" y1="{yy:.1f}" x2="{W-PR}" y2="{yy:.1f}" '
                  f'stroke="#2a2a2a" stroke-dasharray="4,4"/>'
                  f'<text x="{PL-8}" y="{yy+4:.1f}" text-anchor="end" '
                  f'font-size="11" fill="#888">{v:.1f}</text>')

    # x 轴日期 (最多标 8 个)
    step = max(1, len(series) // 8)
    xlabels = ""
    for i in range(0, len(series), step):
        d = series[i][0][5:]  # MM-DD
        xlabels += (f'<text x="{x(i):.1f}" y="{H-PB+20}" text-anchor="middle" '
                    f'font-size="11" fill="#888">{d}</text>')

    last = series[-1][1]
    first = series[0][1]
    delta = last - first
    color = "#e4002b" if delta >= 0 else "#1a9e54"  # 涨红跌绿, A 股规矩
    arrow = "▲" if delta >= 0 else "▼"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<rect width="{W}" height="{H}" fill="#111"/>
<text x="{PL}" y="18" font-size="14" fill="#f5c518" font-weight="bold">巨无霸指数 (基期=100)</text>
{ticks}
<polygon points="{area}" fill="{color}" opacity="0.15"/>
<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2.5"/>
<circle cx="{x(len(series)-1):.1f}" cy="{y(last):.1f}" r="4" fill="{color}"/>
<text x="{x(len(series)-1):.1f}" y="{y(last)-10:.1f}" text-anchor="middle" font-size="13" fill="#fff" font-weight="bold">{last:.2f}</text>
{xlabels}
<text x="{W-PR}" y="{H-8}" text-anchor="end" font-size="11" fill="#666">较基期 {arrow} {abs(delta):.2f} 点 · 数据来自麦当劳官方 MCP</text>
</svg>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)


def update_readme(series):
    path = os.path.join(ROOT, "README.md")
    if not os.path.exists(path):
        return
    date, val = series[-1]
    base_date = series[0][0]
    delta = val - 100
    arrow = "▲" if delta >= 0 else "▼"
    block = (f"<!-- INDEX-START -->\n"
             f"## 📈 实时指数\n\n"
             f"**{val:.2f}**（{date} 更新，较基期 {base_date} {arrow} {abs(delta):.2f} 点）\n\n"
             f"![巨无霸指数走势](assets/index.svg)\n"
             f"<!-- INDEX-END -->")
    text = open(path, encoding="utf-8").read()
    start, end = "<!-- INDEX-START -->", "<!-- INDEX-END -->"
    if start in text and end in text:
        head = text.split(start)[0]
        tail = text.split(end)[1]
        text = head + block + tail
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("README 指数区块已更新")


def main():
    rows = load_series()
    if not rows:
        print("暂无数据, 跳过渲染.")
        return
    series = to_index(rows)
    svg_chart(series, os.path.join(ASSETS, "index.svg"))
    print(f"已生成 assets/index.svg ({len(series)} 个数据点)")
    update_readme(series)


if __name__ == "__main__":
    main()
