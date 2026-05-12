from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Good:
    id: str
    cost: float
    category: str = ""


@dataclass(frozen=True)
class PopType:
    id: str
    wage_weight: float


@dataclass
class ProductionMethod:
    id: str
    inputs: dict[str, float] = field(default_factory=dict)
    outputs: dict[str, float] = field(default_factory=dict)
    employment: dict[str, int] = field(default_factory=dict)
    construction_output: float = 0.0   # country_construction_add (workforce_scaled)
    # Notable extra effects flattened across workforce_scaled / level_scaled /
    # throughput_scaled / unscaled blocks; key = raw modifier name.
    country_modifiers: dict[str, float] = field(default_factory=dict)
    state_modifiers: dict[str, float] = field(default_factory=dict)
    # Building-level multipliers / mortality / etc that aren't goods or jobs.
    building_extras: dict[str, float] = field(default_factory=dict)


@dataclass
class ProductionMethodGroup:
    id: str
    pm_ids: list[str] = field(default_factory=list)


@dataclass
class Building:
    id: str
    pmg_ids: list[str] = field(default_factory=list)
    required_construction: str | None = None
    building_group: str | None = None


@dataclass
class BuildingGroup:
    id: str
    parent_group: str | None = None


@dataclass
class StateTrait:
    """A geographical / cultural trait that a state region can carry, granting
    a static modifier set (typically goods throughput bonuses)."""
    id: str
    modifiers: dict[str, float] = field(default_factory=dict)


@dataclass
class StrategicRegion:
    """A continent-level region that groups state regions for AI / map purposes."""
    id: str
    state_ids: list[str] = field(default_factory=list)


@dataclass
class StateResource:
    """A single resource block from a state region (discoverable / depletable)."""
    type: str                               # building_*  (e.g. building_oil_rig)
    amount: float = 0.0
    discovered_amount: float = 0.0
    undiscovered_amount: float = 0.0
    depleted_amount: float = 0.0
    depleted_type: str | None = None


@dataclass
class StateRegion:
    """One STATE_* block from map_data/state_regions/*.txt."""
    id: str                                 # STATE_SVEALAND
    numeric_id: int = 0                     # game's id field
    is_sea: bool = False                    # only id + provinces, skip from analysis
    arable_land: int = 0
    arable_resources: list[str] = field(default_factory=list)   # building_* keys
    capped_resources: dict[str, int] = field(default_factory=dict)  # building_* -> cap
    resources: list[StateResource] = field(default_factory=list)
    traits: list[str] = field(default_factory=list)             # state_trait_* keys
    subsistence_building: str | None = None
    naval_exit_id: int | None = None
    province_count: int = 0


@dataclass
class GameData:
    goods: dict[str, Good] = field(default_factory=dict)
    pops: dict[str, PopType] = field(default_factory=dict)
    pms: dict[str, ProductionMethod] = field(default_factory=dict)
    pmgs: dict[str, ProductionMethodGroup] = field(default_factory=dict)
    buildings: dict[str, Building] = field(default_factory=dict)
    building_groups: dict[str, BuildingGroup] = field(default_factory=dict)
    construction_costs: dict[str, float] = field(default_factory=dict)
    state_regions: dict[str, StateRegion] = field(default_factory=dict)
    state_traits: dict[str, StateTrait] = field(default_factory=dict)
    strategic_regions: dict[str, StrategicRegion] = field(default_factory=dict)
    loc: object | None = None
    version: str = ""              # e.g. "1.13.4 (Matcha)"
    raw_version: str = ""          # e.g. "1.13.4"

    def strategic_region_of(self, state_id: str) -> str | None:
        for sr in self.strategic_regions.values():
            if state_id in sr.state_ids:
                return sr.id
        return None

    def root_group(self, bg_id: str | None) -> str | None:
        """Walk up parent_group chain to find the top-level building group."""
        seen: set[str] = set()
        cur = bg_id
        while cur and cur not in seen:
            seen.add(cur)
            bg = self.building_groups.get(cur)
            if bg is None or bg.parent_group is None:
                return cur
            cur = bg.parent_group
        return cur

    def group_chain(self, bg_id: str | None) -> list[str]:
        """Return the ancestry chain [self, parent, ..., root] for a building group."""
        seen: set[str] = set()
        out: list[str] = []
        cur = bg_id
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur)
            bg = self.building_groups.get(cur)
            if bg is None or bg.parent_group is None:
                break
            cur = bg.parent_group
        return out
