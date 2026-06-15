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
RESOURCE_ALIASES: dict[str, str] = {
    "building_gold_field": "building_gold_mine",
}

DEFAULT_METRIC = "total_capacity"


def canonical_resource(bld: str) -> str:
    return RESOURCE_ALIASES.get(bld, bld)


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
        return game.loc.get_clean(bld) if game.loc is not None else bld

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
        return game.loc.get_clean(b) if game.loc is not None else b

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
