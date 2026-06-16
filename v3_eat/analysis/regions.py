"""Per-state-region row assembly for the regions report.

Each row corresponds to one land state region, with localized state name,
strategic-region bucket, total arable land, capped resources, discoverable
resources, and state traits (with their static modifier effects).

Resource columns are split into two groups:
- A static set (col_state, col_arable_land, col_capped_total, …)
- A dynamic set, one column per distinct resource building seen across all
  states (e.g., 铁矿 / 煤矿 / 油井 / …) so users can sort & compare
  individual resources directly. Discovered via discover_dynamic_resources()
  at report time.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterator

from ..i18n import UI, get_ui
from ..model import GameData, StateRegion, StateResource
from ..util.logging import get_logger
from ..util.strings import _format_modifier  # reuse modifier formatter

log = get_logger()

# Layout: state name first → key numerics (potential, cap) → per-resource
# columns spliced after capped_total → traits/trait_modifiers context →
# wide text descriptions of resources → identifiers at the end.
REGION_COLUMN_KEYS: list[tuple[str, str]] = [
    ("state",               "rcol_state"),
    ("strategic_region",    "rcol_strategic_region"),
    ("arable_land",         "rcol_arable_land"),
    ("arable_buildings",    "rcol_arable_buildings"),
    ("total_capacity",      "rcol_total_capacity"),    # forward — most important aggregate
    ("capped_total",        "rcol_capped_total"),       # forward — the sort key
    # ↓ dynamic res_<bld> columns inserted here by make_region_columns_with_dynamic
    ("traits",              "rcol_traits"),
    ("trait_modifiers",     "rcol_trait_modifiers"),
    ("subsistence",         "rcol_subsistence"),
    ("provinces",           "rcol_provinces"),
    ("numeric_id",          "rcol_numeric_id"),
    ("capped_resources",    "rcol_capped_resources"),  # text — moved to back
    ("discoverable",        "rcol_discoverable"),       # text — moved to back
    ("known_resources",     "rcol_known_resources"),    # text — moved to back
    ("state_id",            "rcol_state_id"),
    ("traits_ids",          "rcol_traits_ids"),
    ("strat_id",            "rcol_strat_id"),
]


def make_region_columns(ui: UI) -> list[tuple[str, str]]:
    return [(k, ui[lk]) for k, lk in REGION_COLUMN_KEYS]


def make_region_columns_with_dynamic(
    ui: UI,
    resource_ids: list[str],
    loc_get,
) -> list[tuple[str, str]]:
    """Splice per-resource numeric columns into the static layout.

    Per-resource columns land right after `capped_total`. Header for each is
    the localized building name. The value for a state is the union of its
    cap and discoverable amounts for that resource (sum), since for sorting
    & comparison the user just wants "how much of this resource".
    """
    cols: list[tuple[str, str]] = []
    for k, lk in REGION_COLUMN_KEYS:
        cols.append((k, ui[lk]))
        if k == "capped_total":
            for bld in resource_ids:
                cols.append((f"res_{bld}", loc_get(bld)))
    return cols


@dataclass
class RegionRow:
    state: str = ""
    strategic_region: str = ""
    arable_land: int = 0
    arable_buildings: str = ""
    capped_total: int = 0
    capped_resources: str = ""
    discoverable: str = ""
    known_resources: str = ""
    total_capacity: int = 0
    traits: str = ""
    trait_modifiers: str = ""
    subsistence: str = ""
    provinces: int = 0
    numeric_id: int = 0
    state_id: str = ""
    traits_ids: str = ""
    strat_id: str = ""
    bucket: str = ""        # canonical bucket id (translated at writer time)
    # Per-resource potential dict — capped + discoverable amounts merged per
    # building id, since for sorting/comparison the user just wants "how much
    # of this resource can the state support" regardless of how it's gated.
    res_by_id: dict[str, float] = field(default_factory=dict)


def discover_dynamic_resources(game: GameData) -> list[str]:
    """Scan all land states to find every distinct resource building (capped
    or discoverable). Returns a sorted list for stable column ordering."""
    seen: set[str] = set()
    for s in game.state_regions.values():
        if s.is_sea:
            continue
        seen.update(s.capped_resources.keys())
        for r in s.resources:
            seen.add(r.type)
            if r.depleted_type:
                seen.add(r.depleted_type)
    return sorted(seen)


def get_row_value(row: RegionRow, key: str):
    """Resolve a column key against a RegionRow, including dynamic res_ keys."""
    if key.startswith("res_"):
        return row.res_by_id.get(key[4:])
    return getattr(row, key, None)


# Strategic-region id → continent bucket id (canonical, translated via i18n).
# Anything not in this map falls back to the 'other' bucket.
_REGION_BUCKET = {
    "region_western_europe": "western_europe",
    "region_southern_europe": "southern_europe",
    "region_northern_europe": "northern_europe",
    "region_central_europe": "western_europe",
    "region_eastern_europe": "eastern_europe",
    "region_baltic": "eastern_europe",
    "region_balkans": "southern_europe",
    "region_anatolia": "middle_east",
    "region_caucasus": "middle_east",
    "region_levant": "middle_east",
    "region_arabia": "middle_east",
    "region_persia": "middle_east",
    "region_mesopotamia": "middle_east",
    "region_egypt": "middle_east",
    "region_near_east": "middle_east",
    "region_nile_basin": "middle_east",
    "region_greater_persia": "middle_east",
    "region_atlantic_coast": "north_america",
    "region_gran_colombia": "south_america",
    "region_himalayas": "east_asia",
    "region_maghreb": "africa",
    "region_west_africa": "africa",
    "region_east_africa": "africa",
    "region_central_africa": "africa",
    "region_southern_africa": "africa",
    "region_horn_of_africa": "africa",
    "region_great_lakes": "africa",
    "region_west_indies": "central_america",
    "region_central_america": "central_america",
    "region_caribbean": "central_america",
    "region_mexico": "central_america",
    "region_louisiana": "north_america",
    "region_great_lakes_basin": "north_america",
    "region_great_plains": "north_america",
    "region_new_england": "north_america",
    "region_pacific_us": "north_america",
    "region_mid_atlantic": "north_america",
    "region_canadian_pacific": "north_america",
    "region_canadian_atlantic": "north_america",
    "region_canada": "north_america",
    "region_alaska": "north_america",
    "region_brazil": "south_america",
    "region_andes": "south_america",
    "region_la_plata": "south_america",
    "region_amazonas": "south_america",
    "region_central_asia": "central_asia",
    "region_north_central_asia": "central_asia",
    "region_siberia": "central_asia",
    "region_russia": "eastern_europe",
    "region_west_india": "india",
    "region_east_india": "india",
    "region_central_india": "india",
    "region_north_india": "india",
    "region_south_india": "india",
    "region_china": "east_asia",
    "region_north_china": "east_asia",
    "region_south_china": "east_asia",
    "region_korea": "east_asia",
    "region_japan": "east_asia",
    "region_manchuria": "east_asia",
    "region_indochina": "southeast_asia",
    "region_indonesia": "southeast_asia",
    "region_malaya": "southeast_asia",
    "region_philippines": "southeast_asia",
    "region_australia": "oceania",
    "region_oceania": "oceania",
    "region_polynesia": "oceania",
}


REGION_BUCKET_ORDER = [
    "western_europe", "southern_europe", "northern_europe", "eastern_europe",
    "north_america", "central_america", "south_america",
    "africa", "middle_east", "central_asia",
    "india", "east_asia", "southeast_asia", "oceania", "other",
]


def _bucket_of(strat_id: str | None) -> str:
    if not strat_id:
        return "other"
    if strat_id in _REGION_BUCKET:
        return _REGION_BUCKET[strat_id]
    # heuristic fallback by substring
    s = strat_id.lower()
    for needle, bucket in (
        ("europe", "eastern_europe"), ("africa", "africa"),
        ("america", "north_america"), ("asia", "east_asia"),
        ("china", "east_asia"), ("india", "india"),
        ("ocean", "oceania"), ("pacific", "oceania"),
    ):
        if needle in s:
            return bucket
    return "other"


def _fmt_num(x: float) -> str:
    if x == int(x):
        return str(int(x))
    return f"{x:.2f}".rstrip("0").rstrip(".")


def _join_capped(capped: dict[str, int], loc_get) -> tuple[str, int]:
    if not capped:
        return "", 0
    parts = []
    total = 0
    for bld, cap in capped.items():
        parts.append(f"{loc_get(bld)} ×{cap}")
        total += cap
    return ", ".join(parts), total


def _join_resources(resources: list[StateResource], loc_get,
                    discovered_only: bool) -> str:
    """Format `resource = {…}` blocks. discovered_only=True picks the
    discovered+amount portion; False picks undiscovered."""
    parts = []
    for r in resources:
        if discovered_only:
            n = r.amount + r.discovered_amount
        else:
            n = r.undiscovered_amount
        if n <= 0:
            continue
        parts.append(f"{loc_get(r.type)} ×{_fmt_num(n)}")
    return ", ".join(parts)


def _join_arable(arable_resources: list[str], loc_get) -> str:
    return ", ".join(loc_get(b) for b in arable_resources) if arable_resources else ""


def _join_traits(trait_ids: list[str], loc_get) -> str:
    return ", ".join(loc_get(t) for t in trait_ids) if trait_ids else ""


def _join_trait_modifiers(trait_ids: list[str], game: GameData, ui: UI) -> str:
    """For each trait on the state, list its modifier effects."""
    chunks: list[str] = []
    for tid in trait_ids:
        t = game.state_traits.get(tid)
        if t is None:
            continue
        bits = []
        for k, v in t.modifiers.items():
            s = _format_modifier(k, v, ui, game.loc)
            if s:
                bits.append(s)
        if bits:
            chunks.append(f"{game.loc.get_clean(tid) if game.loc else tid}: " + "; ".join(bits))
    return " | ".join(chunks)


def build_region_rows(game: GameData, ui: UI | None = None) -> Iterator[RegionRow]:
    if ui is None:
        ui = get_ui("simp_chinese")
    loc = game.loc

    def L(k: str) -> str:
        return loc.get_clean(k) if loc is not None else k

    skipped_sea = 0
    for sid in sorted(game.state_regions):
        s = game.state_regions[sid]
        if s.is_sea:
            skipped_sea += 1
            continue

        strat_id = game.strategic_region_of(sid) or ""
        bucket = _bucket_of(strat_id)

        capped_str, capped_total = _join_capped(s.capped_resources, L)
        discoverable_str = _join_resources(s.resources, L, discovered_only=False)
        known_str = _join_resources(s.resources, L, discovered_only=True)
        # Total potential capacity = arable_land + capped_total + sum of all resource amounts
        resource_total = sum(
            r.amount + r.discovered_amount + r.undiscovered_amount
            for r in s.resources
        )
        total_capacity = s.arable_land + capped_total + int(resource_total)

        # Per-resource dict (cap + potential merged per building)
        res_by_id: dict[str, float] = dict(s.capped_resources)
        for r in s.resources:
            n = r.amount + r.discovered_amount + r.undiscovered_amount
            if n > 0:
                res_by_id[r.type] = res_by_id.get(r.type, 0.0) + n

        yield RegionRow(
            state=L(sid),
            strategic_region=L(strat_id) if strat_id else "",
            arable_land=s.arable_land,
            arable_buildings=_join_arable(s.arable_resources, L),
            capped_total=capped_total,
            capped_resources=capped_str,
            discoverable=discoverable_str,
            known_resources=known_str,
            total_capacity=total_capacity,
            traits=_join_traits(s.traits, L),
            trait_modifiers=_join_trait_modifiers(s.traits, game, ui),
            subsistence=L(s.subsistence_building) if s.subsistence_building else "",
            provinces=s.province_count,
            numeric_id=s.numeric_id,
            state_id=sid,
            traits_ids=" + ".join(s.traits) if s.traits else "",
            strat_id=strat_id,
            bucket=bucket,
            res_by_id=res_by_id,
        )

    if skipped_sea:
        log.info("Skipped %d sea regions", skipped_sea)
