from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any

from .model import (
    Building,
    BuildingGroup,
    GameData,
    Good,
    PopType,
    ProductionMethod,
    ProductionMethodGroup,
    StateRegion,
    StateResource,
    StateTrait,
    StrategicRegion,
)
from .parser.pdx_parser import load_dir, parse_file
from .parser.yml_loc import LocStore, load_localization
from .util.logging import get_logger

log = get_logger()

_INPUT_RE = re.compile(r"^goods_input_(.+)_add$")
_OUTPUT_RE = re.compile(r"^goods_output_(.+)_add$")
_EMP_RE = re.compile(r"^building_employment_(.+)_add$")


def _to_float(s: Any, default: float = 0.0) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    if isinstance(s, str):
        try:
            return float(s)
        except ValueError:
            return default
    return default


def _flatten_modifiers(node: Any) -> dict[str, float]:
    """Walk a dict that may contain workforce_scaled / level_scaled / unscaled blocks
    and return a flat key->float dict (last write wins for duplicate keys)."""
    out: dict[str, float] = {}
    if not isinstance(node, dict):
        return out
    for k, v in node.items():
        if isinstance(v, dict) and k in ("workforce_scaled", "level_scaled", "unscaled"):
            for kk, vv in v.items():
                out[kk] = _to_float(vv)
        elif isinstance(v, dict):
            out.update(_flatten_modifiers(v))
    return out


_SCALED_BLOCKS = ("workforce_scaled", "level_scaled", "throughput_scaled", "unscaled")


def _flatten_scaled(node: Any) -> dict[str, float]:
    """Flatten a {scaled_kind: {key: value, ...}, ...} block into a flat dict."""
    out: dict[str, float] = {}
    if not isinstance(node, dict):
        return out
    for kind in _SCALED_BLOCKS:
        sub = node.get(kind)
        if isinstance(sub, dict):
            for k, v in sub.items():
                out[k] = _to_float(v)
    return out


def _build_pm(pm_id: str, raw: dict[str, Any]) -> ProductionMethod:
    pm = ProductionMethod(id=pm_id)

    # building_modifiers: goods I/O (workforce_scaled), employment (level_scaled),
    # plus other building-level extras (multipliers, mortality, etc).
    bm = raw.get("building_modifiers")
    if isinstance(bm, dict):
        ws = bm.get("workforce_scaled") if isinstance(bm.get("workforce_scaled"), dict) else {}
        ls = bm.get("level_scaled") if isinstance(bm.get("level_scaled"), dict) else {}
        if isinstance(ws, dict):
            for k, v in ws.items():
                m = _INPUT_RE.match(k)
                if m:
                    pm.inputs[m.group(1)] = _to_float(v); continue
                m = _OUTPUT_RE.match(k)
                if m:
                    pm.outputs[m.group(1)] = _to_float(v); continue
                # Other workforce-scaled building modifier (mortality, etc.)
                pm.building_extras[k] = _to_float(v)
        if isinstance(ls, dict):
            for k, v in ls.items():
                m = _EMP_RE.match(k)
                if m:
                    pm.employment[m.group(1)] = int(_to_float(v))
                    continue
                pm.building_extras[k] = _to_float(v)
        for kind in ("throughput_scaled", "unscaled"):
            sub = bm.get(kind)
            if isinstance(sub, dict):
                for k, v in sub.items():
                    pm.building_extras[k] = _to_float(v)

    # country_modifiers and state_modifiers: country-/state-wide effects.
    cm = raw.get("country_modifiers")
    if isinstance(cm, dict):
        flat = _flatten_scaled(cm)
        if "country_construction_add" in flat:
            pm.construction_output = flat["country_construction_add"]
        for k, v in flat.items():
            pm.country_modifiers[k] = v

    sm = raw.get("state_modifiers")
    if isinstance(sm, dict):
        for k, v in _flatten_scaled(sm).items():
            pm.state_modifiers[k] = v

    return pm


def _build_pmg(pmg_id: str, raw: dict[str, Any]) -> ProductionMethodGroup:
    pms = raw.get("production_methods", [])
    if isinstance(pms, str):
        pms = [pms]
    elif isinstance(pms, dict):
        pms = list(pms.keys())
    elif not isinstance(pms, list):
        pms = []
    return ProductionMethodGroup(id=pmg_id, pm_ids=[str(x) for x in pms])


def _build_building(b_id: str, raw: dict[str, Any]) -> Building:
    pmgs = raw.get("production_method_groups", [])
    if isinstance(pmgs, str):
        pmgs = [pmgs]
    elif isinstance(pmgs, dict):
        pmgs = list(pmgs.keys())
    elif not isinstance(pmgs, list):
        pmgs = []
    rc = raw.get("required_construction")
    if isinstance(rc, list):
        rc = rc[-1] if rc else None
    bg = raw.get("building_group")
    if isinstance(bg, list):
        bg = bg[-1] if bg else None
    return Building(
        id=b_id,
        pmg_ids=[str(x) for x in pmgs],
        required_construction=str(rc) if rc is not None else None,
        building_group=str(bg) if bg is not None else None,
    )


def _build_good(gid: str, raw: dict[str, Any]) -> Good:
    cost = _to_float(raw.get("cost"))
    cat = raw.get("category", "")
    if isinstance(cat, list):
        cat = cat[-1] if cat else ""
    return Good(id=gid, cost=cost, category=str(cat) if cat else "")


def _build_pop(pid: str, raw: dict[str, Any]) -> PopType:
    return PopType(id=pid, wage_weight=_to_float(raw.get("wage_weight"), 0.0))


def _load_version(game_root: Path) -> tuple[str, str]:
    """Read version + rawVersion from launcher/launcher-settings.json.

    Returns ("", "") if the file is missing or malformed.
    """
    f = game_root / "launcher" / "launcher-settings.json"
    if not f.exists():
        return "", ""
    try:
        data = json.loads(f.read_text(encoding="utf-8-sig", errors="replace"))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to parse launcher-settings.json: %s", e)
        return "", ""
    return str(data.get("version", "")), str(data.get("rawVersion", ""))


def _build_state_region(state_id: str, raw: dict[str, Any]) -> StateRegion:
    if not isinstance(raw, dict):
        return StateRegion(id=state_id, is_sea=True)

    arable = _to_float(raw.get("arable_land"), 0.0)

    arable_resources_raw = raw.get("arable_resources", [])
    if isinstance(arable_resources_raw, str):
        arable_resources = [arable_resources_raw]
    elif isinstance(arable_resources_raw, list):
        arable_resources = [str(x) for x in arable_resources_raw]
    else:
        arable_resources = []

    capped: dict[str, int] = {}
    cr = raw.get("capped_resources")
    if isinstance(cr, dict):
        for k, v in cr.items():
            capped[str(k)] = int(_to_float(v))

    # `resource = { ... }` blocks may repeat → loader collects them as a list
    # of dicts (when keys repeat) or a single dict.
    resources: list[StateResource] = []
    res_raw = raw.get("resource")
    res_iter = res_raw if isinstance(res_raw, list) else ([res_raw] if isinstance(res_raw, dict) else [])
    for r in res_iter:
        if not isinstance(r, dict):
            continue
        rtype = r.get("type")
        if isinstance(rtype, list):
            rtype = rtype[-1] if rtype else None
        if rtype is None:
            continue
        depleted_type = r.get("depleted_type")
        if isinstance(depleted_type, list):
            depleted_type = depleted_type[-1] if depleted_type else None
        resources.append(StateResource(
            type=str(rtype).strip('"'),
            amount=_to_float(r.get("amount")),
            discovered_amount=_to_float(r.get("discovered_amount")),
            undiscovered_amount=_to_float(r.get("undiscovered_amount")),
            depleted_amount=_to_float(r.get("depleted_amount")),
            depleted_type=str(depleted_type).strip('"') if depleted_type else None,
        ))

    traits_raw = raw.get("traits", [])
    if isinstance(traits_raw, str):
        traits = [traits_raw]
    elif isinstance(traits_raw, list):
        traits = [str(x).strip('"') for x in traits_raw]
    else:
        traits = []

    provinces_raw = raw.get("provinces", [])
    if isinstance(provinces_raw, str):
        provinces_raw = [provinces_raw]
    elif not isinstance(provinces_raw, list):
        provinces_raw = []
    province_count = len(provinces_raw)
    # Each token is a hex province color like "x0974E5" (quotes already stripped
    # by the tokenizer). Convert to a 0xRRGGBB int for choropleth rendering;
    # silently skip anything that isn't a valid hex color.
    province_colors: list[int] = []
    for tok in provinces_raw:
        s = str(tok).strip().strip('"').lstrip("xX")
        try:
            province_colors.append(int(s, 16))
        except ValueError:
            continue

    naval_exit = raw.get("naval_exit_id")
    naval_exit_id = int(_to_float(naval_exit)) if naval_exit is not None else None

    subsist = raw.get("subsistence_building")
    if isinstance(subsist, list):
        subsist = subsist[-1] if subsist else None

    # Sea regions only have id + provinces; mark them so analysis can skip.
    is_sea = arable == 0 and not capped and not resources and not arable_resources

    return StateRegion(
        id=state_id,
        numeric_id=int(_to_float(raw.get("id"))),
        is_sea=is_sea,
        arable_land=int(arable),
        arable_resources=[s.strip('"') for s in arable_resources],
        capped_resources=capped,
        resources=resources,
        traits=traits,
        subsistence_building=str(subsist).strip('"') if subsist else None,
        naval_exit_id=naval_exit_id,
        province_count=province_count,
        province_colors=province_colors,
    )


def _build_state_trait(trait_id: str, raw: dict[str, Any]) -> StateTrait:
    modifiers: dict[str, float] = {}
    mod_raw = raw.get("modifier") if isinstance(raw, dict) else None
    if isinstance(mod_raw, dict):
        for k, v in mod_raw.items():
            modifiers[k] = _to_float(v)
    return StateTrait(id=trait_id, modifiers=modifiers)


def _build_strategic_region(sr_id: str, raw: dict[str, Any]) -> StrategicRegion:
    states_raw = raw.get("states", []) if isinstance(raw, dict) else []
    if isinstance(states_raw, str):
        states = [states_raw]
    elif isinstance(states_raw, list):
        states = [str(s).strip('"') for s in states_raw]
    else:
        states = []
    return StrategicRegion(id=sr_id, state_ids=states)


def _load_construction_costs(game_root: Path) -> dict[str, float]:
    f = game_root / "game" / "common" / "script_values" / "building_values.txt"
    out: dict[str, float] = {}
    if not f.exists():
        return out
    raw = parse_file(f)
    for k, v in raw.items():
        if k.startswith("construction_cost_") and isinstance(v, str):
            try:
                out[k] = float(v)
            except ValueError:
                pass
    return out


def load(game_root: Path, lang: str = "simp_chinese") -> GameData:
    log.info("Loading game data from %s", game_root)
    common = game_root / "game" / "common"
    goods_raw = load_dir(common / "goods")
    pops_raw = load_dir(common / "pop_types")
    pms_raw = load_dir(common / "production_methods")
    pmgs_raw = load_dir(common / "production_method_groups")
    buildings_raw = load_dir(common / "buildings")
    bgs_raw = load_dir(common / "building_groups")
    state_traits_raw = load_dir(common / "state_traits")
    strategic_regions_raw = load_dir(common / "strategic_regions")
    state_regions_raw = load_dir(game_root / "game" / "map_data" / "state_regions")
    construction = _load_construction_costs(game_root)
    loc = load_localization(game_root, lang)
    version, raw_version = _load_version(game_root)

    game = GameData(
        construction_costs=construction,
        loc=loc,
        version=version,
        raw_version=raw_version,
    )
    for k, v in goods_raw.items():
        if isinstance(v, dict):
            game.goods[k] = _build_good(k, v)
    for k, v in pops_raw.items():
        if isinstance(v, dict):
            game.pops[k] = _build_pop(k, v)
    for k, v in pms_raw.items():
        if isinstance(v, dict):
            game.pms[k] = _build_pm(k, v)
    for k, v in pmgs_raw.items():
        if isinstance(v, dict):
            game.pmgs[k] = _build_pmg(k, v)
    for k, v in buildings_raw.items():
        if isinstance(v, dict):
            game.buildings[k] = _build_building(k, v)
    for k, v in bgs_raw.items():
        if isinstance(v, dict):
            parent = v.get("parent_group")
            if isinstance(parent, list):
                parent = parent[-1] if parent else None
            game.building_groups[k] = BuildingGroup(
                id=k, parent_group=str(parent) if parent else None
            )
    for k, v in state_traits_raw.items():
        if isinstance(v, dict):
            game.state_traits[k] = _build_state_trait(k, v)
    for k, v in strategic_regions_raw.items():
        if isinstance(v, dict):
            game.strategic_regions[k] = _build_strategic_region(k, v)
    for k, v in state_regions_raw.items():
        # state_regions/*.txt may include sea regions whose blocks have no
        # economic content; we still record them with is_sea=True for completeness.
        sr = _build_state_region(k, v) if isinstance(v, dict) else StateRegion(id=k, is_sea=True)
        game.state_regions[k] = sr

    log.info(
        "Loaded V3 %s: %d goods, %d pops, %d PMs, %d PMGs, %d buildings, %d BGs, "
        "%d states (%d land), %d traits, %d strat regions, loc=%d keys",
        version or "(version unknown)",
        len(game.goods), len(game.pops), len(game.pms),
        len(game.pmgs), len(game.buildings), len(game.building_groups),
        len(game.state_regions), sum(1 for s in game.state_regions.values() if not s.is_sea),
        len(game.state_traits), len(game.strategic_regions),
        len(loc.raw),
    )
    return game


__all__ = ["load", "GameData", "LocStore"]
