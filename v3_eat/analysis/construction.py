from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator

from ..i18n import UI, get_ui
from ..model import GameData
from ..util.strings import fmt_goods_dict


CONSTRUCTION_COLUMN_KEYS: list[tuple[str, str]] = [
    ("building",                "ccol_building"),
    ("pm",                      "ccol_pm"),
    ("inputs_str",              "ccol_inputs_str"),
    ("construction_per_lvl",    "ccol_construction_per_lvl"),
    ("employment",              "ccol_employment"),
    ("wage_mult",               "ccol_wage_mult"),
    ("material_cost_per_lvl",   "ccol_material_cost_per_lvl"),
    ("wage_cost_per_lvl",       "ccol_wage_cost_per_lvl"),
    ("material_cost_per_unit",  "ccol_material_cost_per_unit"),
    ("wage_cost_per_unit",      "ccol_wage_cost_per_unit"),
    ("total_cost_per_unit",     "ccol_total_cost_per_unit"),
    ("building_id",             "ccol_building_id"),
    ("pm_id",                   "ccol_pm_id"),
]


def make_construction_columns(ui: UI) -> list[tuple[str, str]]:
    return [(k, ui[lk]) for k, lk in CONSTRUCTION_COLUMN_KEYS]


@dataclass
class ConstructionRow:
    building: str = ""
    pm: str = ""
    inputs_str: str = ""
    construction_per_lvl: float = 0.0
    employment: int = 0
    wage_mult: float | None = None
    material_cost_per_lvl: float = 0.0
    wage_cost_per_lvl: float = 0.0
    material_cost_per_unit: float | None = None
    wage_cost_per_unit: float | None = None
    total_cost_per_unit: float | None = None
    building_id: str = ""
    pm_id: str = ""


def build_construction_rows(game: GameData, ui: UI | None = None) -> Iterator[ConstructionRow]:
    """Yield (construction-sector building × PM) cost-per-unit rows.
    Output is construction points (country_construction_add), not goods."""
    if ui is None:
        ui = get_ui("simp_chinese")
    loc = game.loc

    def L(k: str) -> str:
        return loc.get_clean(k) if loc is not None else k

    for b_id in sorted(game.buildings):
        b = game.buildings[b_id]
        if b.building_group != "bg_construction":
            continue
        for pmg_id in b.pmg_ids:
            pmg = game.pmgs.get(pmg_id)
            if pmg is None:
                continue
            for pm_id in pmg.pm_ids:
                pm = game.pms.get(pm_id)
                if pm is None or pm.construction_output <= 0:
                    continue
                mat_cost = sum(
                    qty * game.goods[g].cost
                    for g, qty in pm.inputs.items()
                    if g in game.goods
                )
                emp = sum(pm.employment.values())
                wage_units = sum(
                    e * game.pops[p].wage_weight
                    for p, e in pm.employment.items()
                    if p in game.pops
                )
                cpu_mat = mat_cost / pm.construction_output
                cpu_wage = wage_units / pm.construction_output
                cpu_total = cpu_mat + cpu_wage
                ww = wage_units / emp if emp > 0 else None
                yield ConstructionRow(
                    building=L(b_id),
                    pm=L(pm_id),
                    inputs_str=fmt_goods_dict(pm.inputs, L),
                    construction_per_lvl=pm.construction_output,
                    employment=emp,
                    wage_mult=ww,
                    material_cost_per_lvl=mat_cost,
                    wage_cost_per_lvl=wage_units,
                    material_cost_per_unit=cpu_mat,
                    wage_cost_per_unit=cpu_wage,
                    total_cost_per_unit=cpu_total,
                    building_id=b_id,
                    pm_id=pm_id,
                )
