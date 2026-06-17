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
from .metrics import (
    AGGREGATES,
    LEGACY_RESOURCE_HEADERS,
    RESOURCE_ALIASES,
    canonical_resource,
    metric_label,
)

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
    """All `res_<...>` snapshot keys that could hold this resource metric, across
    report formats and versions. A resource column may be keyed by:

    * the stable building id (`res_building_oil_rig`) — id-format reports, and the
      raw-id fallback older reports used when that version's loc lacked an entry
      (e.g. `res_bg_gold_fields`);
    * the building's localized name in the *report's own* language
      (`res_<header_loc name>`) — the common name-format case;
    * a historical localized name for a renamed/retranslated building
      (`res_石油精炼厂` for today's `building_oil_rig`) — see LEGACY_RESOURCE_HEADERS.

    Folds gold_field + gold_mine (+ legacy bg_gold_fields) into one canonical
    resource, matching the live choropleth. Returns de-duplicated candidates; a
    given report row only carries one form per resource, so summing is safe."""
    canon = canonical_resource(metric_key)
    raws = [canon] + [raw for raw, c in RESOURCE_ALIASES.items() if c == canon]
    out: list[str] = []
    for b in raws:
        out.append(f"res_{b}")                                    # stable id / raw-id form
        if header_loc is not None:
            out.append(f"res_{header_loc.get_clean(b)}")          # localized-name form
    for hist, c in LEGACY_RESOURCE_HEADERS.items():               # renamed across versions
        if canonical_resource(c) == canon:
            out.append(f"res_{hist}")
    seen: set[str] = set()
    return [k for k in out if not (k in seen or seen.add(k))]


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


def comparable_deltas(
    old_vals: dict[str, float],
    new_vals: dict[str, float],
    index: R.ProvinceIndex,
    *,
    old_ids: set[str] | None = None,
    new_ids: set[str] | None = None,
) -> dict[str, float]:
    """Per-state delta, restricted to states that EXIST in BOTH versions *and* in
    the current game's geometry.

    A state present in only one version is not a "change" — it was renamed,
    split/merged, or is new/removed content. Treating its missing side as 0
    (``old_vals.get(sid, 0.0)``) paints it as a full-value spike: e.g. 1.0.6's
    Bengal (NORTH/SOUTH) became 1.13.8's WEST/EAST, so the new ids would light up
    bright green for capacity that merely moved next door. Restricting to states
    present in both removes those artifacts and leaves only like-for-like deltas.

    Comparability is keyed on state *presence* — pass ``old_ids``/``new_ids`` (the
    full set of state rows in each snapshot). A missing *value* then defaults to 0,
    so a persisting state that gained/lost a resource (0 <-> N) is still a real
    change worth showing. When the id sets are omitted we fall back to the value
    keys, which is exact for aggregates (every land state has one) but would drop
    gained-from-0 resource changes — so callers with the snapshots should pass
    the full id sets."""
    oid = old_ids if old_ids is not None else set(old_vals)
    nid = new_ids if new_ids is not None else set(new_vals)
    out: dict[str, float] = {}
    for sid in oid & nid:
        if sid not in index.state_to_colors:
            continue
        dv = new_vals.get(sid, 0.0) - old_vals.get(sid, 0.0)
        if abs(dv) > 1e-9:
            out[sid] = dv
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
    old_ids: set[str] | None = None,
    new_ids: set[str] | None = None,
) -> tuple[Image.Image, float]:
    changed = comparable_deltas(old_vals, new_vals, index, old_ids=old_ids, new_ids=new_ids)
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

    # Comparability is keyed on state *presence* (every snapshot row), not on the
    # metric value — so a persisting state that gained/lost a resource (0 <-> N)
    # still counts, while renamed/split/new states are excluded.
    old_ids = {sid for (sid,) in old.states}
    new_ids = {sid for (sid,) in new.states}
    only_new = len(new_ids - old_ids)
    only_old = len(old_ids - new_ids)
    if only_new or only_old:
        log.info("Comparing %d states present in both v%s and v%s; excluding %d new + "
                 "%d removed (renamed/split — not a like-for-like change).",
                 len(old_ids & new_ids), old_v, new_v, only_new, only_old)

    title = metric_label(game, ui, metric_key)   # aggregate -> UI label, resource -> loc name (no raw "_")
    R.set_swatch_labels(nodata=ui["map_nodata"], water=ui["map_water"])
    index = R.ProvinceIndex.build(game, game_root, width=width)
    sub = f"{ui['map_change']}  ·  {old_v} → {new_v}"
    img, maxabs = render_change_map(
        index, old_vals, new_vals, title=title, subtitle=sub, ui=ui, old_ids=old_ids, new_ids=new_ids,
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
        changed = comparable_deltas(old_vals, new_vals, index, old_ids=old_ids, new_ids=new_ids)
        state_fill: dict[str, tuple[int, int, int]] = {}
        labels_list = []
        for sid, dv in changed.items():
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
