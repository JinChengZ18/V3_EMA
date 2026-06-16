from __future__ import annotations
from typing import Mapping
from ..model import Building, GameData, Good, PopType, ProductionMethod


def gross_value(goods_qty: Mapping[str, float], goods: Mapping[str, Good]) -> float:
    total = 0.0
    for gid, qty in goods_qty.items():
        g = goods.get(gid)
        if g is None:
            continue
        total += qty * g.cost
    return total


def output_value(pm: ProductionMethod, goods: Mapping[str, Good]) -> float:
    return gross_value(pm.outputs, goods)


def input_value(pm: ProductionMethod, goods: Mapping[str, Good]) -> float:
    return gross_value(pm.inputs, goods)


def net_value(pm: ProductionMethod, goods: Mapping[str, Good]) -> float:
    return output_value(pm, goods) - input_value(pm, goods)


def total_employment(pm: ProductionMethod) -> int:
    return sum(pm.employment.values())


def weighted_wage(pm: ProductionMethod, pops: Mapping[str, PopType]) -> float | None:
    total_emp = total_employment(pm)
    if total_emp <= 0:
        return None
    weighted = 0.0
    for pid, emp in pm.employment.items():
        p = pops.get(pid)
        if p is None:
            continue
        weighted += emp * p.wage_weight
    return weighted / total_emp


def construction_points(b: Building, costs: Mapping[str, float]) -> float | None:
    rc = b.required_construction
    if rc is None:
        return None
    if rc in costs:
        return costs[rc]
    try:
        return float(rc)
    except (TypeError, ValueError):
        return None


def roi(net: float, cp: float | None) -> float | None:
    if cp is None or cp == 0:
        return None
    return net / cp


WEEKS_PER_YEAR = 52


def per_capita(net: float, emp: int) -> float | None:
    """Annualized per-capita output: weekly profit × 52 / employment.

    V3's economic flows are weekly; this matches the in-game tooltip definition
    of 「人均年产值」 which annualizes the building's net output.
    """
    if emp <= 0:
        return None
    return net * WEEKS_PER_YEAR / emp
