"""Which per-state quantities can be drawn on the map, and their values.

A *metric* is one map layer: a label plus a {state_id -> value} mapping. We reuse
`build_region_rows` so a map shows exactly the numbers the Excel regions report
shows — `res_by_id` (capped + discoverable + undiscovered, merged per resource
building) for per-resource layers, and the row aggregates for the summary layers.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..analysis.regions import RegionRow, build_region_rows, discover_dynamic_resources
from ..i18n import UI
from ..model import GameData

# Aggregate metric key -> (RegionRow attribute, i18n label key).
AGGREGATES: dict[str, tuple[str, str]] = {
    "total_capacity": ("total_capacity", "rcol_total_capacity"),
    "capped_total": ("capped_total", "rcol_capped_total"),
    "arable_land": ("arable_land", "rcol_arable_land"),
    "resource_kinds": ("resource_kinds", "rcol_resource_kinds"),
}

# Resources that are the same thing at a different discovery/depletion stage,
# folded into a single canonical layer. `building_gold_field` (the discoverable
# surface deposit) depletes into `building_gold_mine` (see the `depleted_type`
# in game/map_data/state_regions/*.txt), so the two are summed into one "gold".
# `bg_gold_fields` is the building-group id older versions stored for gold (and
# left untranslated in 1.0.6/1.3.6 reports) — folded into the same canonical.
RESOURCE_ALIASES: dict[str, str] = {
    "building_gold_field": "building_gold_mine",
    "bg_gold_fields": "building_gold_mine",
}

# Cross-version compatibility: a regions report stores each resource column under
# the building's *localized name* (e.g. "捕鲸业"), so a report written by an older
# game labels a renamed/retranslated building differently than the current game
# — and matching by the current name silently misses it (the layer reads empty
# for that version). This maps the historical column header (localized name, or
# a raw id when that version's loc lacked the entry) to the current canonical
# building id, so timeline/diff align resources across versions. Verified against
# the bundled 1.0.6–1.9.8 baselines; harmless once reports carry stable ids.
LEGACY_RESOURCE_HEADERS: dict[str, str] = {
    "捕鲸业": "building_whaling_station",   # -> 捕鲸站
    "林业": "building_logging_camp",        # -> 伐木营地
    "渔业": "building_fishing_wharf",       # -> 渔业码头
    "石油精炼厂": "building_oil_rig",        # -> 油井
}

# Resource kinds that exist in older reports but were removed from the live
# building set (no current layer), so the timeline — which derives its layers
# from the current game — would drop them entirely. Surfaced as historical-only
# layers so the slider shows them fade to zero. Maps each version's column header
# to a synthetic kind id; LEGACY_REMOVED_LABELS gives the display name.
LEGACY_REMOVED_HEADERS: dict[str, str] = {
    "bg_monuments": "monuments",    # raw id (1.0.6 / 1.3.6 loc lacked the entry)
    "奇观": "monuments",            # translated in 1.6.2+
}
LEGACY_REMOVED_LABELS: dict[str, str] = {"monuments": "奇观"}

DEFAULT_METRIC = "total_capacity"


def canonical_resource(bld: str) -> str:
    return RESOURCE_ALIASES.get(bld, bld)


def _humanize(key: str) -> str:
    """Readable fallback name from a raw id when localization is missing: strip
    the `building_` prefix, underscores -> spaces, Title Case (never shows the
    internal '_' id in a map title)."""
    s = key[len("building_"):] if key.startswith("building_") else key
    return s.replace("_", " ").strip().title() or key


def _loc_name(game: GameData, key: str) -> str:
    """Localized name for a building id, with a humanized fallback (so a missing
    loc entry never leaks a `building_..._..` id onto the map)."""
    name = game.loc.get_clean(key) if game.loc is not None else key
    return name if (name and name != key and "_" not in name) else _humanize(key)


def metric_label(game: GameData, ui: UI, key: str) -> str:
    """Display label for any metric key (aggregate or resource). Aggregates use
    the i18n UI label; resources use the localized building name. Used by the
    diff / timeline titles, which otherwise would show the raw key."""
    if key in AGGREGATES:
        return ui[AGGREGATES[key][1]]
    return _loc_name(game, canonical_resource(key))


@dataclass
class Metric:
    key: str                                   # aggregate key or building_* id
    label: str                                 # localized display name
    is_resource: bool                          # True = per-resource building layer
    is_crop: bool = False                      # True = arable crop distribution layer
    values: dict[str, float] = field(default_factory=dict)   # state_id -> value

    @property
    def nonzero(self) -> int:
        return sum(1 for v in self.values.values() if v > 0)

    @property
    def vmax(self) -> float:
        return max(self.values.values(), default=0.0)


def _resource_kinds(row: RegionRow) -> int:
    return sum(1 for v in row.res_by_id.values() if v > 0)


def build_metrics(
    game: GameData,
    ui: UI,
    *,
    rows: list[RegionRow] | None = None,
    only: str | None = None,
    include_aggregates: bool = True,
    include_resources: bool = True,
) -> list[Metric]:
    """Build the list of drawable metrics.

    `only` restricts to a single metric key (aggregate key or building id).
    """
    if rows is None:
        rows = list(build_region_rows(game, ui))

    def loc(bld: str) -> str:
        return _loc_name(game, bld)

    metrics: list[Metric] = []

    if include_aggregates:
        for key, (attr, label_key) in AGGREGATES.items():
            if only is not None and only != key:
                continue
            if attr == "resource_kinds":
                values = {r.state_id: float(_resource_kinds(r)) for r in rows}
            else:
                values = {r.state_id: float(getattr(r, attr)) for r in rows}
            metrics.append(Metric(key=key, label=ui[label_key], is_resource=False, values=values))

    if include_resources:
        # Group raw resource buildings by their canonical id (folds gold_field
        # into gold_mine, summing per-state values).
        canon_to_raw: dict[str, list[str]] = {}
        for bld in discover_dynamic_resources(game):
            canon_to_raw.setdefault(canonical_resource(bld), []).append(bld)

        only_canon = canonical_resource(only) if only is not None else None
        for canon, raws in canon_to_raw.items():
            if only_canon is not None and only_canon != canon:
                continue
            values: dict[str, float] = {}
            for r in rows:
                v = sum(r.res_by_id.get(b, 0.0) for b in raws)
                values[r.state_id] = float(v)
            # Skip resources nobody has (keeps `--all` output tidy).
            if any(v > 0 for v in values.values()):
                metrics.append(Metric(key=canon, label=loc(canon), is_resource=True, values=values))

    return metrics


def resolve_metric(game: GameData, ui: UI, key: str, rows: list[RegionRow] | None = None) -> Metric | None:
    """Build a single metric by key, or None if unknown/empty."""
    ms = build_metrics(game, ui, rows=rows, only=key)
    return ms[0] if ms else None


def build_crop_metrics(game: GameData, ui: UI, *, only: str | None = None) -> list[Metric]:
    """One layer per arable crop (from each state's `arable_resources`), shaded by
    the state's arable_land where the crop can be grown — i.e. the crop's growable
    range + how much farmland is there. Value = arable_land if supported, else 0.
    """
    def loc(b: str) -> str:
        return _loc_name(game, b)

    crops = sorted({
        b for s in game.state_regions.values() if not s.is_sea for b in s.arable_resources
    })
    out: list[Metric] = []
    for b in crops:
        if only is not None and only != b:
            continue
        values: dict[str, float] = {}
        for sid, s in game.state_regions.items():
            if s.is_sea:
                continue
            values[sid] = float(s.arable_land) if b in s.arable_resources else 0.0
        if any(v > 0 for v in values.values()):
            out.append(Metric(key=b, label=loc(b), is_resource=False, is_crop=True, values=values))
    return out
