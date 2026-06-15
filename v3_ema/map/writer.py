"""Orchestrate map output: build the index once, render PNG/SVG and/or an HTML viewer."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..analysis.regions import build_region_rows
from ..i18n import UI
from ..model import GameData
from ..util.logging import get_logger
from ..util.progress import track
from . import colormap as cm
from . import render as R
from .html_viewer import write_html_viewer
from .metrics import DEFAULT_METRIC, Metric, build_crop_metrics, build_metrics

log = get_logger()


def _safe(name: str) -> str:
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in name)


def render_metric_png(
    index: R.ProvinceIndex,
    metric: Metric,
    *,
    version_label: str,
    cmap: str,
    reverse: bool,
    clip_percentile: float,
    log_scale: bool,
    gamma: float = 0.7,
    labels: bool = True,
    borders: bool = True,
    grid: bool = False,
    national_borders: bool = False,
    min_country_provinces: int = 8,
    country_filter: str = "civilized",
):
    """Render one metric to a finished PIL image (map + embedded legend)."""
    img, vmax = index.render(
        metric, cmap=cmap, reverse=reverse, clip_percentile=clip_percentile,
        log_scale=log_scale, gamma=gamma, labels=labels, borders=borders, grid=grid,
        national_borders=national_borders, min_country_provinces=min_country_provinces,
        country_filter=country_filter,
    )
    subtitle = version_label
    if metric.nonzero:
        subtitle = f"{version_label}  ·  {metric.nonzero} states"
    table = cm.table_for(cmap, metric.key, metric.is_resource, metric.is_crop)
    return R.draw_legend(
        img, title=metric.label, subtitle=subtitle, table=table, vmax=vmax,
        reverse=reverse, fonts=index.fonts,
    )


def render_metric_svg(
    index: R.ProvinceIndex,
    metric: Metric,
    *,
    version_label: str,
    cmap: str,
    reverse: bool,
    clip_percentile: float,
    log_scale: bool,
    gamma: float,
    borders: bool,
    grid: bool,
    national_borders: bool,
    min_country_provinces: int,
    country_filter: str = "civilized",
    label_min_area: float = 36.0,
) -> str:
    """Hybrid SVG: a high-res raster fill (with borders) + crisp VECTOR value
    labels and legend (in the game's embedded fonts)."""
    img, vmax = index.render(
        metric, cmap=cmap, reverse=reverse, clip_percentile=clip_percentile,
        log_scale=log_scale, gamma=gamma, labels=False, borders=borders, grid=grid,
        national_borders=national_borders, min_country_provinces=min_country_provinces,
        country_filter=country_filter,
    )
    table = cm.table_for(cmap, metric.key, metric.is_resource, metric.is_crop)
    scale_max = vmax if vmax > 0 else 1.0
    labels = []
    for sid, val in metric.values.items():
        if val <= 0:
            continue
        anc = index.anchors.get(sid)
        if anc is None or anc[2] < label_min_area:
            continue
        x, y, area = anc
        k = index.size[0] / 2400.0
        sz = min(max(area ** 0.5 * 0.45, 9 * k), 30 * k)
        s = min(max(((np.log1p(val) if log_scale else val) / scale_max), 0.0), 1.0) ** gamma
        rgb = cm.colorize(np.array([s]), table, reverse)[0]
        lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        fg, halo = ("#2d2318", "#fdf6ea") if lum > 140 else ("#fdf6ea", "#241a10")
        labels.append((x, y, sz, R._fmt_val(val), fg, halo))
    subtitle = f"{version_label}  ·  {metric.nonzero} states" if metric.nonzero else version_label
    legend = R.svg_legend(index, img, metric.label, subtitle,
                          table.astype(int).tolist(), vmax)
    return R.svg_document(index, img, labels, legend)


def render_atlas_files(
    game: GameData,
    game_root: Path,
    ui: UI,
    out_dir: Path,
    *,
    metric_keys: list[str] | None = None,
    width: int = 1200,
    cmap: str = cm.DEFAULT,
    gamma: float = 0.7,
    labels: bool = False,
    borders: bool = True,
    grid: bool = False,
    national_borders: bool = False,
    min_country_provinces: int = 8,
    country_filter: str = "civilized",
    version_label: str = "",
) -> list[tuple[str, Path]]:
    """Render a curated set of maps to PNG files (for embedding into the xlsx).

    Returns [(label, png_path), ...]. Default set: total-potential + one per resource.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    R.set_swatch_labels(nodata=ui["map_nodata"], water=ui["map_water"])
    rows = list(build_region_rows(game, ui))
    if metric_keys is None:
        all_metrics = build_metrics(game, ui, rows=rows)
        metrics = [m for m in all_metrics if m.key == "total_capacity" or m.is_resource]
    else:
        metrics = [m for k in metric_keys for m in build_metrics(game, ui, rows=rows, only=k)]
    if not metrics:
        return []

    index = R.ProvinceIndex.build(game, game_root, width=width)
    out: list[tuple[str, Path]] = []
    for m in track(metrics, label="atlas"):
        finished = render_metric_png(
            index, m, version_label=version_label, cmap=cmap, reverse=False,
            clip_percentile=99.0, log_scale=False, gamma=gamma, labels=labels,
            borders=borders, grid=grid, national_borders=national_borders,
            min_country_provinces=min_country_provinces, country_filter=country_filter,
        )
        path = out_dir / f"atlas_{_safe(m.key)}.png"
        finished.save(path)
        out.append((m.label, path))
    return out


def render_crop_maps(
    game: GameData,
    game_root: Path,
    ui: UI,
    out_dir: Path,
    *,
    width: int = 2400,
    cmap: str = cm.DEFAULT,
    gamma: float = 0.7,
    labels: bool = True,
    borders: bool = True,
    grid: bool = False,
    national_borders: bool = False,
    min_country_provinces: int = 8,
    country_filter: str = "civilized",
    svg: bool = False,
    version_label: str = "",
) -> list[Path]:
    """Render one map per arable crop (distribution × arable land) into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    R.set_swatch_labels(nodata=ui["map_nodata"], water=ui["map_water"])
    metrics = build_crop_metrics(game, ui)
    if not metrics:
        log.error("No arable crops found")
        return []
    index = R.ProvinceIndex.build(game, game_root, width=width)
    common = dict(cmap=cmap, reverse=False, clip_percentile=99.0, log_scale=False, gamma=gamma,
                  borders=borders, grid=grid, national_borders=national_borders,
                  min_country_provinces=min_country_provinces, country_filter=country_filter)
    written: list[Path] = []
    for m in track(metrics, label="crop"):
        finished = render_metric_png(index, m, version_label=version_label, labels=labels, **common)
        path = out_dir / f"crop_{_safe(m.key)}.png"
        finished.save(path)
        written.append(path)
        log.info("Wrote %s  (states=%d)", path.name, m.nonzero)
        if svg:
            sp = out_dir / f"crop_{_safe(m.key)}.svg"
            sp.write_text(render_metric_svg(index, m, version_label=version_label, **common), encoding="utf-8")
            written.append(sp)
    return written


def generate(
    game: GameData,
    game_root: Path,
    ui: UI,
    out_dir: Path,
    *,
    metric_key: str | None = None,
    all_resources: bool = False,
    width: int = 2400,
    cmap: str = cm.DEFAULT,
    reverse: bool = False,
    clip_percentile: float = 99.0,
    log_scale: bool = False,
    gamma: float = 0.7,
    labels: bool = True,
    borders: bool = True,
    grid: bool = False,
    national_borders: bool = False,
    min_country_provinces: int = 8,
    country_filter: str = "civilized",
    svg: bool = False,
    fmt: str = "both",          # png | html | both
    version_label: str = "",
    html_dir: Path | None = None,
    html_width: int = 4096,
) -> list[Path]:
    """Generate resource map output. Returns the list of written files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    R.set_swatch_labels(nodata=ui["map_nodata"], water=ui["map_water"])
    rows = list(build_region_rows(game, ui))

    if all_resources:
        metrics = build_metrics(game, ui, rows=rows, include_aggregates=True, include_resources=True)
    elif metric_key:
        metrics = build_metrics(game, ui, rows=rows, only=metric_key)
        if not metrics:
            log.error("Unknown or empty metric: %s", metric_key)
            return []
    else:
        metrics = build_metrics(game, ui, rows=rows, only=DEFAULT_METRIC)

    log.info("Building province index (width=%d) ...", width)
    index = R.ProvinceIndex.build(game, game_root, width=width)

    common = dict(cmap=cmap, reverse=reverse, clip_percentile=clip_percentile,
                  log_scale=log_scale, gamma=gamma, borders=borders, grid=grid,
                  national_borders=national_borders, min_country_provinces=min_country_provinces,
                  country_filter=country_filter)

    if fmt in ("png", "both"):
        for m in track(metrics, label="render"):
            finished = render_metric_png(index, m, version_label=version_label, labels=labels, **common)
            path = out_dir / f"map_{_safe(m.key)}.png"
            finished.save(path)
            written.append(path)
            log.info("Wrote %s  (states=%d)", path.name, m.nonzero)

    if svg:
        for m in track(metrics, label="svg"):
            svg_str = render_metric_svg(index, m, version_label=version_label, **common)
            spath = out_dir / f"map_{_safe(m.key)}.svg"
            spath.write_text(svg_str, encoding="utf-8")
            written.append(spath)
            log.info("Wrote %s", spath.name)

    if fmt in ("html", "both"):
        html_metrics = (build_metrics(game, ui, rows=rows, include_aggregates=True, include_resources=True)
                        + build_crop_metrics(game, ui))
        hdir = html_dir or out_dir
        hdir.mkdir(parents=True, exist_ok=True)
        html_path = hdir / "resource_map.html"
        write_html_viewer(
            html_path, game, game_root, ui, rows, html_metrics,
            cmap=cmap, clip_percentile=clip_percentile, log_scale=log_scale,
            gamma=gamma, version_label=version_label, html_width=html_width,
        )
        written.append(html_path)
        log.info("Wrote %s  (%d layers)", html_path.name, len(html_metrics))

    return written
