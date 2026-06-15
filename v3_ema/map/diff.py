"""Cross-version resource *change* map.

Reads two regions xlsx reports (the same ones `regions diff` consumes — bundled
baselines work), computes each state's per-metric delta, and renders a diverging
choropleth on the current game's province bitmap: red = the resource was cut,
green = it grew, neutral = unchanged. The numbers come from the reports; the
shapes come from the live game files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from ..analysis.regions_diff import RegionsSnapshot, read_regions_report
from ..i18n import UI
from ..model import GameData
from ..parser.yml_loc import load_localization
from ..util.logging import get_logger
from . import colormap as cm
from . import render as R
from .metrics import AGGREGATES, RESOURCE_ALIASES, canonical_resource, metric_label

log = get_logger()

# Aggregate metric key -> the canonical numeric field stored in a snapshot row.
_AGG_FIELD = {k: v[0] for k, v in AGGREGATES.items()}


def snapshot_lang(meta: dict) -> str:
    """The data-language a regions report was written in (for resource headers)."""
    for k in ("数据语言", "Data Language"):
        if k in meta and meta[k]:
            return str(meta[k])
    return "english"


def _contributing_headers(header_loc, metric_key: str) -> list[str]:
    """`res_<localized name>` snapshot fields that make up a resource metric, using
    the *report's own* language for the column header text. Folds gold_field +
    gold_mine into one (matching the live choropleth)."""
    canon = canonical_resource(metric_key)
    raws = [canon] + [raw for raw, c in RESOURCE_ALIASES.items() if c == canon]
    out = []
    for b in raws:
        h = header_loc.get_clean(b) if header_loc is not None else b
        out.append(f"res_{h}")
    return out


def state_metric_values(snap: RegionsSnapshot, metric_key: str, *, header_loc) -> dict[str, float]:
    """Extract {state_id: value} for a metric from a regions snapshot.

    `header_loc` must localize building ids in the snapshot's own language so the
    `res_<name>` columns are found regardless of the map's render language.
    """
    out: dict[str, float] = {}
    if metric_key in _AGG_FIELD:
        field = _AGG_FIELD[metric_key]
        for (sid,), row in snap.states.items():
            v = row.get(field)
            if isinstance(v, (int, float)):
                out[sid] = float(v)
        return out
    headers = _contributing_headers(header_loc, metric_key)
    for (sid,), row in snap.states.items():
        total = 0.0
        seen = False
        for hk in headers:
            v = row.get(hk)
            if isinstance(v, (int, float)):
                total += v
                seen = True
        if seen:
            out[sid] = total
    return out


def render_change_map(
    index: R.ProvinceIndex,
    old_vals: dict[str, float],
    new_vals: dict[str, float],
    *,
    title: str,
    subtitle: str,
    ui: UI,
    clip_percentile: float = 99.0,
    labels: bool = True,
    borders: bool = True,
    grid: bool = False,
    national_borders: bool = False,
    min_country_provinces: int = 12,
    country_filter: str = "civilized",
) -> tuple[Image.Image, float]:
    sids = set(old_vals) | set(new_vals)
    deltas = {
        sid: new_vals.get(sid, 0.0) - old_vals.get(sid, 0.0)
        for sid in sids
        if sid in index.state_to_colors
    }
    changed = {sid: dv for sid, dv in deltas.items() if abs(dv) > 1e-9}
    table = cm.as_table("diverging")
    compose_kw = dict(borders=borders, grid=grid, national_borders=national_borders,
                      min_country_provinces=min_country_provinces, country_filter=country_filter)
    if not changed:
        img = index.compose({}, **compose_kw)
        return R.draw_legend(img, title=title, subtitle=subtitle, table=table,
                             vmax=1, fonts=index.fonts, diverging=True), 0.0

    mags = np.asarray([abs(dv) for dv in changed.values()])
    maxabs = float(np.percentile(mags, clip_percentile)) if clip_percentile < 100 else float(mags.max())
    if maxabs <= 0:
        maxabs = float(mags.max()) or 1.0

    state_fill: dict[str, tuple[int, int, int]] = {}
    labels_text: dict[str, str] = {}
    for sid, dv in changed.items():
        t = (min(max(dv / maxabs, -1.0), 1.0) + 1.0) / 2.0
        rgb = cm.colorize(np.array([t]), table)[0]
        state_fill[sid] = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        sign = "+" if dv > 0 else "−"
        labels_text[sid] = sign + R._fmt_val(abs(dv))

    img = index.compose(state_fill, labels_text=labels_text if labels else None, **compose_kw)
    legend = R.draw_legend(img, title=title, subtitle=subtitle, table=table,
                           vmax=maxabs, fonts=index.fonts, diverging=True)
    return legend, maxabs


def generate_diff(
    game: GameData,
    game_root: Path,
    ui: UI,
    old_path: Path,
    new_path: Path,
    out_dir: Path,
    *,
    metric_key: str = "total_capacity",
    width: int = 2400,
    clip_percentile: float = 99.0,
    labels: bool = True,
    borders: bool = True,
    grid: bool = False,
    national_borders: bool = False,
    min_country_provinces: int = 12,
    country_filter: str = "civilized",
    svg: bool = False,
) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    old = read_regions_report(old_path)
    new = read_regions_report(new_path)

    def ver(meta: dict) -> str:
        for k in ("数据版本", "Raw Version", "游戏版本", "Game Version"):
            if k in meta:
                return str(meta[k])
        return "?"

    old_v, new_v = ver(old.meta), ver(new.meta)
    old_loc = load_localization(game_root, snapshot_lang(old.meta))
    new_loc = load_localization(game_root, snapshot_lang(new.meta))
    old_vals = state_metric_values(old, metric_key, header_loc=old_loc)
    new_vals = state_metric_values(new, metric_key, header_loc=new_loc)
    if not old_vals and not new_vals:
        log.error("Metric %s not found in either report (resource headers are "
                  "language-specific; old/new/current game should share --lang).", metric_key)
        return None

    title = metric_label(game, ui, metric_key)   # aggregate -> UI label, resource -> loc name (no raw "_")
    R.set_swatch_labels(nodata=ui["map_nodata"], water=ui["map_water"])
    index = R.ProvinceIndex.build(game, game_root, width=width)
    sub = f"{ui['map_change']}  ·  {old_v} → {new_v}"
    img, maxabs = render_change_map(
        index, old_vals, new_vals, title=title, subtitle=sub, ui=ui,
        clip_percentile=clip_percentile, labels=labels, borders=borders, grid=grid,
        national_borders=national_borders, min_country_provinces=min_country_provinces,
        country_filter=country_filter,
    )
    safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in metric_key)
    stem = f"map_diff_{safe}_v{old_v}_to_v{new_v}"
    path = out_dir / f"{stem}.png"
    img.save(path)
    log.info("Wrote change map %s (max |Δ|≈%.0f)", path, maxabs)

    if svg:
        table = cm.as_table("diverging")
        ma = maxabs if maxabs > 0 else 1.0
        changed = {sid: new_vals.get(sid, 0.0) - old_vals.get(sid, 0.0)
                   for sid in set(old_vals) | set(new_vals) if sid in index.state_to_colors}
        state_fill: dict[str, tuple[int, int, int]] = {}
        labels_list = []
        for sid, dv in changed.items():
            if abs(dv) <= 1e-9:
                continue
            t = (min(max(dv / ma, -1.0), 1.0) + 1.0) / 2.0
            rgb = cm.colorize(np.array([t]), table)[0]
            state_fill[sid] = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
            anc = index.anchors.get(sid)
            if anc and anc[2] >= 36:
                lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
                fg, halo = ("#2d2318", "#fdf6ea") if lum > 140 else ("#fdf6ea", "#241a10")
                sz = min(max(anc[2] ** 0.5 * 0.45, 9), 30)
                labels_list.append((anc[0], anc[1], sz,
                                    ("+" if dv > 0 else "−") + R._fmt_val(abs(dv)), fg, halo))
        fill = index.compose(state_fill, labels_text=None, borders=borders, grid=grid,
                             national_borders=national_borders,
                             min_country_provinces=min_country_provinces, country_filter=country_filter)
        legend = R.svg_legend(index, fill, title, sub,
                              table.astype(int).tolist(), maxabs, diverging=True)
        spath = out_dir / f"{stem}.svg"
        spath.write_text(R.svg_document(index, fill, labels_list, legend), encoding="utf-8")
        log.info("Wrote %s", spath.name)
    return path
