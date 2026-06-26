"""Tiny dependency-free chart library that emits inline SVG.

Using inline SVG (instead of a JavaScript chart library loaded from a CDN)
keeps the dashboard 100% offline and private: it opens with no internet at all.
"""

from __future__ import annotations

import html
import math
from datetime import datetime

PALETTE = ["#4f8cff", "#34c38f", "#f1b44c", "#f46a6a", "#a78bfa", "#06b6d4",
           "#fb7185", "#84cc16", "#fbbf24", "#38bdf8", "#c084fc", "#2dd4bf",
           "#fca5a5", "#a3e635", "#f472b6"]


def _esc(s: str) -> str:
    return html.escape(str(s))


def _month_label(ym: str) -> str:
    try:
        return datetime.strptime(ym, "%Y-%m").strftime("%b")
    except ValueError:
        return ym


def donut(items: list[tuple[str, float]], size: int = 240) -> str:
    """items: [(label, value)]. Returns an SVG donut with a centered total."""
    total = sum(v for _, v in items) or 1.0
    cx = cy = size / 2
    r, inner = size / 2 - 6, size / 2 - 44
    parts = [f'<svg viewBox="0 0 {size} {size}" class="donut" '
             f'role="img" aria-label="Spending by category">']
    angle = -90.0
    for i, (label, value) in enumerate(items):
        frac = value / total
        sweep = frac * 360
        a0 = math.radians(angle)
        a1 = math.radians(angle + sweep)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        xi0, yi0 = cx + inner * math.cos(a1), cy + inner * math.sin(a1)
        xi1, yi1 = cx + inner * math.cos(a0), cy + inner * math.sin(a0)
        large = 1 if sweep > 180 else 0
        color = PALETTE[i % len(PALETTE)]
        d = (f"M {x0:.2f} {y0:.2f} A {r:.2f} {r:.2f} 0 {large} 1 {x1:.2f} {y1:.2f} "
             f"L {xi0:.2f} {yi0:.2f} A {inner:.2f} {inner:.2f} 0 {large} 0 "
             f"{xi1:.2f} {yi1:.2f} Z")
        parts.append(f'<path d="{d}" fill="{color}">'
                     f'<title>{_esc(label)}: ${value:,.0f} '
                     f'({frac*100:.0f}%)</title></path>')
        angle += sweep
    tot_txt = (f"${total/1e6:.1f}M" if total >= 1e6
               else f"${total/1e3:.0f}k" if total >= 10_000
               else f"${total:,.0f}")
    parts.append(f'<text x="{cx}" y="{cy-4}" text-anchor="middle" '
                 f'class="donut-total">{tot_txt}</text>'
                 f'<text x="{cx}" y="{cy+16}" text-anchor="middle" '
                 f'class="donut-sub">total spend</text></svg>')
    return "".join(parts)


def grouped_bars(cash_flow: list[dict], width: int = 720, height: int = 280) -> str:
    """Income vs expense per month, with a net line on top."""
    if not cash_flow:
        return ""
    pad_l, pad_b, pad_t, pad_r = 52, 34, 16, 12
    plot_w, plot_h = width - pad_l - pad_r, height - pad_b - pad_t
    maxv = max([m["income"] for m in cash_flow] + [m["expense"] for m in cash_flow] + [1])
    n = len(cash_flow)
    group_w = plot_w / n
    bw = min(26, group_w / 3)

    def y(v): return pad_t + plot_h - (v / maxv) * plot_h

    parts = [f'<svg viewBox="0 0 {width} {height}" class="bars" role="img" '
             f'aria-label="Monthly income versus expenses">']
    # gridlines + y labels
    for g in range(5):
        val = maxv * g / 4
        yy = y(val)
        parts.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width-pad_r}" '
                     f'y2="{yy:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad_l-6}" y="{yy+4:.1f}" text-anchor="end" '
                     f'class="axis">${val/1000:.0f}k</text>')
    for i, m in enumerate(cash_flow):
        gx = pad_l + i * group_w + group_w / 2
        xi = gx - bw - 1
        xe = gx + 1
        parts.append(f'<rect x="{xi:.1f}" y="{y(m["income"]):.1f}" width="{bw:.1f}" '
                     f'height="{pad_t+plot_h-y(m["income"]):.1f}" rx="2" '
                     f'fill="#34c38f"><title>{m["month"]} income: '
                     f'${m["income"]:,.0f}</title></rect>')
        parts.append(f'<rect x="{xe:.1f}" y="{y(m["expense"]):.1f}" width="{bw:.1f}" '
                     f'height="{pad_t+plot_h-y(m["expense"]):.1f}" rx="2" '
                     f'fill="#f46a6a"><title>{m["month"]} spend: '
                     f'${m["expense"]:,.0f}</title></rect>')
        parts.append(f'<text x="{gx:.1f}" y="{height-pad_b+18}" text-anchor="middle" '
                     f'class="axis">{_month_label(m["month"])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def line(values: list[float], width: int = 720, height: int = 220,
         color: str = "#4f8cff", x_label_every: int = 6,
         x_unit: str = "mo") -> str:
    """A simple line chart, e.g. total debt balance falling to zero over months."""
    if not values or len(values) < 2:
        return ""
    pad_l, pad_b, pad_t, pad_r = 56, 28, 14, 14
    plot_w, plot_h = width - pad_l - pad_r, height - pad_b - pad_t
    maxv = max(values) or 1
    n = len(values)

    def x(i): return pad_l + (i / (n - 1)) * plot_w
    def y(v): return pad_t + plot_h - (v / maxv) * plot_h

    parts = [f'<svg viewBox="0 0 {width} {height}" class="line" role="img" '
             f'aria-label="Balance over time">']
    for g in range(5):
        val = maxv * g / 4
        yy = y(val)
        parts.append(f'<line x1="{pad_l}" y1="{yy:.1f}" x2="{width-pad_r}" '
                     f'y2="{yy:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad_l-6}" y="{yy+4:.1f}" text-anchor="end" '
                     f'class="axis">${val/1000:.0f}k</text>')
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                 f'stroke-width="2.5"/>')
    area = f"{pad_l},{pad_t+plot_h} " + pts + f" {pad_l+plot_w},{pad_t+plot_h}"
    parts.append(f'<polygon points="{area}" fill="{color}" opacity="0.08"/>')
    for i in range(0, n, max(1, x_label_every)):
        parts.append(f'<text x="{x(i):.1f}" y="{height-8}" text-anchor="middle" '
                     f'class="axis">{i}{x_unit}</text>')
    parts.append("</svg>")
    return "".join(parts)


def hbars(items: list[tuple[str, float, str]], width: int = 720,
          row_h: int = 30) -> str:
    """items: [(label, value, sublabel)] horizontal bars, descending."""
    if not items:
        return ""
    maxv = max(v for _, v, _ in items) or 1
    label_w = 150
    bar_max = width - label_w - 120
    height = row_h * len(items) + 8
    parts = [f'<svg viewBox="0 0 {width} {height}" class="hbars" role="img" '
             f'aria-label="Top items">']
    for i, (label, value, sub) in enumerate(items):
        y = i * row_h + 6
        w = max(2, value / maxv * bar_max)
        color = PALETTE[i % len(PALETTE)]
        parts.append(f'<text x="0" y="{y+16}" class="hbar-label">{_esc(label)}</text>')
        parts.append(f'<rect x="{label_w}" y="{y+3}" width="{w:.1f}" height="18" '
                     f'rx="4" fill="{color}"/>')
        parts.append(f'<text x="{label_w+w+8:.1f}" y="{y+16}" class="hbar-val">'
                     f'${value:,.0f}{("  ·  " + _esc(sub)) if sub else ""}</text>')
    parts.append("</svg>")
    return "".join(parts)
