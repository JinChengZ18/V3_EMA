from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import product
from typing import Iterator

from ..i18n import UI, get_ui
from ..model import GameData, ProductionMethod
from ..util.logging import get_logger
from ..util.strings import (
    CAT_AUTOMATION,
    CAT_BASE,
    CAT_OWNERSHIP,
    building_bucket,
    category_from_pmg_name,
    fmt_goods_dict,
    is_dummy_building_name,
    is_passive_pm,
    pm_notes,
)
from . import metrics

log = get_logger()

# Canonical column ordering: each entry is (field_key, ui_label_key).
# `make_columns(ui)` resolves the ui_label_key to a translated header.
COLUMN_KEYS: list[tuple[str, str]] = [
    ("building",        "col_building"),
    ("base_pms",        "col_base_pms"),
    ("secondary_pms",   "col_secondary_pms"),
    ("automation_pms",  "col_automation_pms"),
    ("ownership_pms",   "col_ownership_pms"),
    ("output_value",    "col_output_value"),
    ("input_value",     "col_input_value"),
    ("net_value",       "col_net_value"),
    ("construction",    "col_construction"),
    ("employment",      "col_employment"),
    ("wage_mult",       "col_wage_mult"),
    ("roi",             "col_roi"),
    ("per_capita",      "col_per_capita"),
    ("building_group",  "col_building_group"),
    ("inputs_str",      "col_inputs_str"),
    ("outputs_str",     "col_outputs_str"),
    ("notes",           "col_notes"),
    ("building_id",     "col_building_id"),
    ("base_ids",        "col_base_ids"),
    ("secondary_ids",   "col_secondary_ids"),
    ("automation_ids",  "col_automation_ids"),
    ("ownership_ids",   "col_ownership_ids"),
]


def make_columns(ui: UI) -> list[tuple[str, str]]:
    """Return [(field_key, translated_header), ...] for the given UI."""
    return [(k, ui[lk]) for k, lk in COLUMN_KEYS]


@dataclass
class Row:
    base_pms: str = ""
    secondary_pms: str = ""
    automation_pms: str = ""
    ownership_pms: str = ""
    inputs_str: str = ""
    outputs_str: str = ""
    notes: str = ""
    building: str = ""
    output_value: float = 0.0
    input_value: float = 0.0
    net_value: float = 0.0
    construction: float | None = None
    employment: int = 0
    wage_mult: float | None = None
    roi: float | None = None
    per_capita: float | None = None
    building_group: str = ""
    building_id: str = ""
    base_ids: str = ""
    secondary_ids: str = ""
    automation_ids: str = ""
    ownership_ids: str = ""
    bucket: str = ""        # canonical bucket id (translated at writer time)


def _loc_name(loc, key: str) -> str:
    if loc is None:
        return key
    return loc.get_clean(key)


def _join_pm_names(pms: list[ProductionMethod], loc_get) -> str:
    return " + ".join(loc_get(pm.id) for pm in pms) if pms else ""


def _join_pm_ids(pms: list[ProductionMethod]) -> str:
    return " + ".join(pm.id for pm in pms) if pms else ""


def _is_informationless(emp: int, ov: float, iv: float,
                        notes_str: str, construction_total: float) -> bool:
    return (
        emp == 0
        and abs(ov) < 1e-9
        and abs(iv) < 1e-9
        and not notes_str
        and abs(construction_total) < 1e-9
    )


_OPT_OUT_HINTS = ("_disabled", "_no_secondary", "_no_effects", "no_secondary")


def _is_conventional_opt_out(pm_id: str) -> bool:
    return any(h in pm_id for h in _OPT_OUT_HINTS)


def _build_notes(annotated: list[tuple[str, ProductionMethod]],
                 loc_get, ui: UI, loc=None) -> str:
    chunks: list[str] = []
    for slot, pm in annotated:
        n = pm_notes(pm, ui, loc)
        if n:
            chunks.append(f"{loc_get(pm.id)}: {n}")
            continue
        if not is_passive_pm(pm):
            continue
        if _is_conventional_opt_out(pm.id):
            continue
        if slot in (CAT_BASE, CAT_OWNERSHIP):
            chunks.append(f"{loc_get(pm.id)}: {ui['notes_passive']}")
    return ui["notes_separator"].join(chunks) if chunks else ""


def build_rows(game: GameData, ui: UI | None = None) -> Iterator[Row]:
    if ui is None:
        ui = get_ui("simp_chinese")
    loc = game.loc

    def L(k: str) -> str:
        return _loc_name(loc, k)

    skipped_dummy = 0
    skipped_no_slots = 0
    skipped_construction = 0
    skipped_empty = 0

    for b_id in sorted(game.buildings):
        b = game.buildings[b_id]
        b_name = L(b_id)
        if is_dummy_building_name(b_name):
            skipped_dummy += 1
            continue
        if b.building_group == "bg_construction":
            skipped_construction += 1
            continue

        cp = metrics.construction_points(b, game.construction_costs)
        bg_loc = L(b.building_group) if b.building_group else ""
        bucket = building_bucket(game.group_chain(b.building_group))

        slots: list[tuple[str, list[ProductionMethod]]] = []
        ownership_defaults: list[ProductionMethod] = []
        for pmg_id in b.pmg_ids:
            pmg = game.pmgs.get(pmg_id)
            if pmg is None:
                continue
            cat = category_from_pmg_name(pmg_id)
            pms = [game.pms[p] for p in pmg.pm_ids if p in game.pms]
            if not pms:
                continue
            if cat == CAT_OWNERSHIP:
                ownership_defaults.append(pms[0])
            else:
                slots.append((cat, pms))

        if not slots:
            skipped_no_slots += 1
            continue

        own_in: dict[str, float] = defaultdict(float)
        own_out: dict[str, float] = defaultdict(float)
        own_emp: dict[str, int] = defaultdict(int)
        for opm in ownership_defaults:
            for g, q in opm.inputs.items():
                own_in[g] += q
            for g, q in opm.outputs.items():
                own_out[g] += q
            for p, e in opm.employment.items():
                own_emp[p] += int(e)

        for combo in product(*(pms for _, pms in slots)):
            base_pms: list[ProductionMethod] = []
            secondary_pms: list[ProductionMethod] = []
            automation_pms: list[ProductionMethod] = []
            sum_in: dict[str, float] = defaultdict(float, own_in)
            sum_out: dict[str, float] = defaultdict(float, own_out)
            sum_emp: dict[str, int] = defaultdict(int, own_emp)

            for (cat, _), pm in zip(slots, combo):
                if cat == CAT_BASE:
                    base_pms.append(pm)
                elif cat == CAT_AUTOMATION:
                    automation_pms.append(pm)
                else:
                    secondary_pms.append(pm)
                for g, q in pm.inputs.items():
                    sum_in[g] += q
                for g, q in pm.outputs.items():
                    sum_out[g] += q
                for p, e in pm.employment.items():
                    sum_emp[p] += int(e)

            for g in list(sum_in.keys()):
                if g in sum_out:
                    diff = sum_out[g] - sum_in[g]
                    if diff > 0:
                        sum_out[g] = diff
                        del sum_in[g]
                    elif diff < 0:
                        sum_in[g] = -diff
                        del sum_out[g]
                    else:
                        del sum_in[g]; del sum_out[g]

            ov = sum(qty * game.goods[g].cost for g, qty in sum_out.items() if g in game.goods)
            iv = sum(qty * game.goods[g].cost for g, qty in sum_in.items() if g in game.goods)
            nv = ov - iv
            emp = sum(sum_emp.values())

            if emp > 0:
                ww_num = sum(e * game.pops[p].wage_weight for p, e in sum_emp.items() if p in game.pops)
                ww = ww_num / emp
            else:
                ww = None

            annotated: list[tuple[str, ProductionMethod]] = []
            for (cat, _), pm in zip(slots, combo):
                annotated.append((cat, pm))
            for opm in ownership_defaults:
                annotated.append((CAT_OWNERSHIP, opm))

            notes_str = _build_notes(annotated, L, ui, loc)
            construction_total = sum(
                pm.construction_output for pm in list(combo) + ownership_defaults
            )
            if _is_informationless(emp, ov, iv, notes_str, construction_total):
                skipped_empty += 1
                continue

            yield Row(
                base_pms=_join_pm_names(base_pms, L),
                secondary_pms=_join_pm_names(secondary_pms, L),
                automation_pms=_join_pm_names(automation_pms, L),
                ownership_pms=_join_pm_names(ownership_defaults, L),
                inputs_str=fmt_goods_dict(dict(sum_in), L),
                outputs_str=fmt_goods_dict(dict(sum_out), L),
                notes=notes_str,
                building=b_name,
                output_value=ov,
                input_value=iv,
                net_value=nv,
                construction=cp,
                employment=emp,
                wage_mult=ww,
                roi=metrics.roi(nv, cp),
                per_capita=metrics.per_capita(nv, emp),
                building_group=bg_loc or (b.building_group or ""),
                building_id=b_id,
                base_ids=_join_pm_ids(base_pms),
                secondary_ids=_join_pm_ids(secondary_pms),
                automation_ids=_join_pm_ids(automation_pms),
                ownership_ids=_join_pm_ids(ownership_defaults),
                bucket=bucket,
            )

    if skipped_dummy:
        log.info("Skipped %d dummy buildings (name length > 30)", skipped_dummy)
    if skipped_no_slots:
        log.info("Skipped %d buildings without usable PMGs", skipped_no_slots)
    if skipped_construction:
        log.info("Skipped %d construction-sector buildings (separate sheet)", skipped_construction)
    if skipped_empty:
        log.info("Skipped %d informationless rows", skipped_empty)
