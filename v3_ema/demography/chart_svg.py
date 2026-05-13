from __future__ import annotations

import html
import math

from .util import clamp, display_units, integer_percent_ticks, pct, symlog


COLORMAPS = {
    "coolwarm": ["#3b4cc0", "#6687ed", "#a9c6fd", "#d7dce3", "#f2b69e", "#dd6b55", "#b40426"],
    "viridis": ["#440154", "#414487", "#2a788e", "#22a884", "#7ad151", "#fde725"],
    "categorical": ["#2563eb", "#0f766e", "#b45309", "#7c3aed", "#be123c", "#475569", "#0891b2", "#9333ea"],
}


_BASE_LABEL_LOWERCASE = {
    "base",
    "base sol curve",
    "no health system",
    "no health + pollution 50%",
    "基准",
    "基础 sol 曲线",
    "无医疗制度",
    "无医疗 + 污染 50%",
}

STYLE_BASE = "base"
STYLE_BIRTH = "birth"
STYLE_MORTALITY = "mortality"
STYLE_NATURAL_GROWTH = "natural_growth"


def is_base_label(name: str, *, style_key: str | None = None) -> bool:
    """Return True if a series should be drawn as the heavy black reference.

    Prefers the explicit ``style_key`` when provided; otherwise falls back to
    the legacy label-string match for backward compatibility with callers
    that don't pass style keys yet.
    """
    if style_key == STYLE_BASE:
        return True
    return name.lower() in _BASE_LABEL_LOWERCASE


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{clamp(channel, 0, 255):02x}" for channel in rgb)


def interpolate_color(a: str, b: str, t: float) -> str:
    ar, ag, ab = hex_to_rgb(a)
    br, bg, bb = hex_to_rgb(b)
    return rgb_to_hex(
        (
            round(ar + (br - ar) * t),
            round(ag + (bg - ag) * t),
            round(ab + (bb - ab) * t),
        )
    )


def color_from_palette(idx: int, count: int, palette: str) -> str:
    colors = COLORMAPS.get(palette, COLORMAPS["categorical"])
    if palette == "categorical":
        return colors[idx % len(colors)]
    if count <= 1:
        return colors[len(colors) // 2]
    pos = idx * (len(colors) - 1) / (count - 1)
    lo = math.floor(pos)
    hi = min(len(colors) - 1, lo + 1)
    return interpolate_color(colors[lo], colors[hi], pos - lo)


_BIRTH_LABELS = {"birth", "出生率"}
_MORTALITY_LABELS = {"mortality", "死亡率"}
_NATURAL_GROWTH_LABELS = {"natural growth", "自然增长率"}


def _effective_style_key(name: str, style_key: str | None) -> str | None:
    """Resolve which logical style applies. ``style_key`` wins; otherwise we
    fall back to matching translated labels for legacy callers.
    """
    if style_key is not None:
        return style_key
    if is_base_label(name):
        return STYLE_BASE
    if name in _NATURAL_GROWTH_LABELS:
        return STYLE_NATURAL_GROWTH
    if name in _BIRTH_LABELS:
        return STYLE_BIRTH
    if name in _MORTALITY_LABELS:
        return STYLE_MORTALITY
    return None


def series_style(name: str, idx: int, count: int, palette: str, *, style_key: str | None = None) -> dict[str, str | float]:
    key = _effective_style_key(name, style_key)
    if key == STYLE_BASE:
        return {"color": "#111827", "width": 3.8, "dash": "", "opacity": 1.0}
    if key == STYLE_NATURAL_GROWTH:
        return {"color": "#111827", "width": 3.0, "dash": "", "opacity": 0.95}
    if key == STYLE_BIRTH:
        return {"color": "#2563eb", "width": 2.4, "dash": "", "opacity": 0.9}
    if key == STYLE_MORTALITY:
        return {"color": "#dc2626", "width": 2.4, "dash": "", "opacity": 0.9}
    return {
        "color": color_from_palette(idx, count, palette),
        "width": 2.05,
        "dash": "",
        "opacity": 0.88,
    }


def svg_line_chart(
    title: str,
    series: list[tuple[str, list[tuple[float, float]]]],
    *,
    width: int = 1120,
    height: int = 420,
    x_label: str = "",
    y_label: str = "",
    y_as_percent: bool = True,
    y_scale: str = "linear",
    integer_percent_y_ticks: bool = False,
    zero_baseline: bool = False,
    palette: str = "categorical",
    y_min: float | None = None,
    y_max: float | None = None,
    y_ticks: list[float] | None = None,
    style_keys: list[str | None] | None = None,
    series_colors: list[str | None] | None = None,
    series_dashes: list[str | None] | None = None,
) -> str:
    """Render an SVG line chart.

    ``style_keys`` (optional) is a list parallel to ``series`` giving each
    series an explicit style category (``"base"``, ``"birth"``, ``"mortality"``,
    ``"natural_growth"``, or ``None`` for the palette).

    ``series_colors`` / ``series_dashes`` (optional, parallel to ``series``)
    let callers override the auto-assigned color and dash pattern for any
    series — used for the healthcare comparison chart where the four
    health-system curves need a consistent color across the two pollution
    levels, with the 50% pollution variant rendered dashed.
    """
    if style_keys is None:
        style_keys = [None] * len(series)
    if series_colors is None:
        series_colors = [None] * len(series)
    if series_dashes is None:
        series_dashes = [None] * len(series)
    max_label_chars = max((display_units(name) for name, _ in series), default=0)
    left = 78
    right = max(190, min(420, 86 + max_label_chars * 7))
    top, bottom = 38, 58
    plot_w = width - left - right
    plot_h = height - top - bottom
    xs = [x for _, points in series for x, _ in points]
    ys = [y for _, points in series for _, y in points]
    if not xs or not ys:
        return ""
    x_min, x_max = min(xs), max(xs)
    raw_ys = list(ys)
    if zero_baseline:
        raw_ys.append(0.0)
    if y_min is not None:
        raw_ys.append(y_min)
    if y_max is not None:
        raw_ys.append(y_max)

    def ty(y: float) -> float:
        if y_scale == "symlog":
            return symlog(y)
        return y

    y_t_min = ty(y_min) if y_min is not None else min(ty(y) for y in raw_ys)
    y_t_max = ty(y_max) if y_max is not None else max(ty(y) for y in raw_ys)
    if y_t_min == y_t_max:
        y_t_min -= 0.01
        y_t_max += 0.01
    if y_min is None or y_max is None:
        padding = (y_t_max - y_t_min) * 0.08
        y_t_min -= padding
        y_t_max += padding

    def sx(x: float) -> float:
        return left + (x - x_min) / (x_max - x_min or 1.0) * plot_w

    def sy(y: float) -> float:
        transformed = ty(y)
        return top + (y_t_max - transformed) / (y_t_max - y_t_min or 1.0) * plot_h

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        f'<text x="{left}" y="24" class="chart-title">{html.escape(title)}</text>',
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}" class="axis"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}" class="axis"/>',
    ]
    for i in range(6):
        x = x_min + (x_max - x_min) * i / 5
        px = sx(x)
        parts.append(f'<line x1="{px:.1f}" y1="{top}" x2="{px:.1f}" y2="{top + plot_h}" class="grid"/>')
        parts.append(f'<text x="{px:.1f}" y="{top + plot_h + 22}" class="tick" text-anchor="middle">{x:g}</text>')

    if y_ticks is not None:
        shown_y_ticks = y_ticks
    elif integer_percent_y_ticks:
        shown_y_ticks = integer_percent_ticks(raw_ys)
    elif y_scale == "linear":
        y_t_values = [y_t_min + (y_t_max - y_t_min) * i / 5 for i in range(6)]
        shown_y_ticks = y_t_values
    else:
        shown_y_ticks = integer_percent_ticks(raw_ys)

    for y in shown_y_ticks:
        py = sy(y)
        if py < top - 1 or py > top + plot_h + 1:
            continue
        label = f"{int(round(y * 100))}%" if integer_percent_y_ticks and y_as_percent else (pct(y, 1) if y_as_percent else f"{y:.3f}")
        parts.append(f'<line x1="{left}" y1="{py:.1f}" x2="{left + plot_w}" y2="{py:.1f}" class="grid"/>')
        parts.append(f'<text x="{left - 8}" y="{py + 4:.1f}" class="tick" text-anchor="end">{label}</text>')
    if zero_baseline and min(raw_ys) <= 0.0 <= max(raw_ys):
        py = sy(0.0)
        parts.append(f'<line x1="{left}" y1="{py:.1f}" x2="{left + plot_w}" y2="{py:.1f}" class="baseline"/>')
    parts.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 12}" class="axis-label" text-anchor="middle">{html.escape(x_label)}</text>')
    parts.append(f'<text x="16" y="{top + plot_h / 2:.1f}" class="axis-label" transform="rotate(-90 16 {top + plot_h / 2:.1f})" text-anchor="middle">{html.escape(y_label)}</text>')

    draw_order = sorted(
        enumerate(series),
        key=lambda item: 1 if is_base_label(item[1][0], style_key=style_keys[item[0]]) else 0,
    )
    for idx, (name, points) in draw_order:
        style = series_style(name, idx, len(series), palette, style_key=style_keys[idx])
        color = series_colors[idx] if series_colors[idx] else str(style["color"])
        dash = series_dashes[idx] if series_dashes[idx] is not None else str(style["dash"])
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        coords = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in points)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{style["width"]}" opacity="{style["opacity"]}" stroke-linecap="round" stroke-linejoin="round"{dash_attr}/>')
    for idx, (name, _points) in enumerate(series):
        style = series_style(name, idx, len(series), palette, style_key=style_keys[idx])
        color = series_colors[idx] if series_colors[idx] else str(style["color"])
        dash = series_dashes[idx] if series_dashes[idx] is not None else str(style["dash"])
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        lx = left + plot_w + 22
        ly = top + 22 + idx * 22
        parts.append(f'<line x1="{lx}" y1="{ly - 5}" x2="{lx + 20}" y2="{ly - 5}" stroke="{color}" stroke-width="{style["width"]}" opacity="{style["opacity"]}" stroke-linecap="round"{dash_attr}/>')
        parts.append(f'<text x="{lx + 28}" y="{ly}" class="legend">{html.escape(name)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)


def svg_bar_chart(
    title: str,
    rows: list[dict[str, str | float | int]],
    *,
    key_field: str,
    value_field: str,
    width: int = 920,
    height: int = 420,
    top_n: int = 12,
) -> str:
    rows = rows[:top_n]
    left, right, top, bottom = 250, 45, 38, 42
    plot_w = width - left - right
    row_h = (height - top - bottom) / max(1, len(rows))
    max_value = max((float(r[value_field]) for r in rows), default=1.0)
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        f'<text x="{left}" y="24" class="chart-title">{html.escape(title)}</text>',
    ]
    for idx, row in enumerate(rows):
        y = top + idx * row_h
        value = float(row[value_field])
        bar_w = value / max_value * plot_w if max_value else 0.0
        label = str(row[key_field])
        parts.append(f'<text x="{left - 8}" y="{y + row_h * 0.64:.1f}" class="tick" text-anchor="end">{html.escape(label)}</text>')
        parts.append(f'<rect x="{left}" y="{y + row_h * 0.18:.1f}" width="{bar_w:.1f}" height="{row_h * 0.58:.1f}" rx="2" fill="#2563eb"/>')
        parts.append(f'<text x="{left + bar_w + 8:.1f}" y="{y + row_h * 0.64:.1f}" class="legend">{value:g}</text>')
    parts.append("</svg>")
    return "\n".join(parts)
