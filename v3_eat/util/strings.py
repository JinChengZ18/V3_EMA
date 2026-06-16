from __future__ import annotations

from ..i18n import UI

# Internal canonical category / bucket identifiers. Translated to display
# strings via the UI lookup at render time.
CAT_BASE = "base"
CAT_SECONDARY = "secondary"
CAT_AUTOMATION = "automation"
CAT_OWNERSHIP = "ownership"

BUCKET_AGRICULTURE = "agriculture"
BUCKET_PLANTATIONS = "plantations"
BUCKET_EXTRACTION = "extraction"
BUCKET_MANUFACTURING = "manufacturing"
BUCKET_SERVICE = "service"
BUCKET_INFRASTRUCTURE = "infrastructure"
BUCKET_GOVERNMENT = "government"
BUCKET_MILITARY = "military"
BUCKET_MONUMENTS = "monuments"
BUCKET_OTHER = "other"

BUCKET_ORDER = [
    BUCKET_AGRICULTURE, BUCKET_PLANTATIONS, BUCKET_EXTRACTION,
    BUCKET_MANUFACTURING, BUCKET_SERVICE, BUCKET_INFRASTRUCTURE,
    BUCKET_GOVERNMENT, BUCKET_MILITARY, BUCKET_MONUMENTS, BUCKET_OTHER,
]

# Buildings whose localized name exceeds this length are dummy/debug entries
# whose loc keys resolve to the body of an English description (~165 chars).
DUMMY_NAME_LEN = 30


# Map V3 bg_* identifiers to canonical bucket ids.
BG_BUCKET = {
    "bg_agriculture": BUCKET_AGRICULTURE,
    "bg_ranching": BUCKET_AGRICULTURE,
    "bg_staple_crops": BUCKET_AGRICULTURE,
    "bg_subsistence_agriculture": BUCKET_AGRICULTURE,
    "bg_plantations": BUCKET_PLANTATIONS,
    "bg_extraction": BUCKET_EXTRACTION,
    "bg_mining": BUCKET_EXTRACTION,
    "bg_logging": BUCKET_EXTRACTION,
    "bg_fishing": BUCKET_EXTRACTION,
    "bg_whaling": BUCKET_EXTRACTION,
    "bg_oil_extraction": BUCKET_EXTRACTION,
    "bg_rubber": BUCKET_EXTRACTION,
    "bg_gold_fields": BUCKET_EXTRACTION,
    "bg_manufacturing": BUCKET_MANUFACTURING,
    "bg_light_industry": BUCKET_MANUFACTURING,
    "bg_heavy_industry": BUCKET_MANUFACTURING,
    "bg_military_industry": BUCKET_MANUFACTURING,
    "bg_munitions": BUCKET_MANUFACTURING,
    "bg_power": BUCKET_INFRASTRUCTURE,
    "bg_power_industry": BUCKET_INFRASTRUCTURE,
    "bg_infrastructure": BUCKET_INFRASTRUCTURE,
    "bg_construction": BUCKET_INFRASTRUCTURE,
    "bg_urbanization": BUCKET_INFRASTRUCTURE,
    "bg_urban_facilities": BUCKET_INFRASTRUCTURE,
    "bg_canals": BUCKET_INFRASTRUCTURE,
    "bg_government": BUCKET_GOVERNMENT,
    "bg_government_buildings": BUCKET_GOVERNMENT,
    "bg_bureaucracy": BUCKET_GOVERNMENT,
    "bg_subsistence": BUCKET_GOVERNMENT,
    "bg_military": BUCKET_MILITARY,
    "bg_army": BUCKET_MILITARY,
    "bg_navy": BUCKET_MILITARY,
    "bg_garrisons": BUCKET_MILITARY,
    "bg_trade": BUCKET_SERVICE,
    "bg_service": BUCKET_SERVICE,
    "bg_financial_districts": BUCKET_SERVICE,
    "bg_monuments": BUCKET_MONUMENTS,
    "bg_monuments_hidden": BUCKET_MONUMENTS,
}

# Substring fallback (lower priority than parent-chain lookup).
_BG_PATTERNS: list[tuple[str, str]] = [
    ("plantation", BUCKET_PLANTATIONS),
    ("_farm", BUCKET_AGRICULTURE),
    ("ranch", BUCKET_AGRICULTURE),
    ("livestock", BUCKET_AGRICULTURE),
    ("_mining", BUCKET_EXTRACTION),
    ("_mine", BUCKET_EXTRACTION),
    ("logging", BUCKET_EXTRACTION),
    ("fishing", BUCKET_EXTRACTION),
    ("whaling", BUCKET_EXTRACTION),
    ("oil_", BUCKET_EXTRACTION),
    ("rubber", BUCKET_EXTRACTION),
    ("monument", BUCKET_MONUMENTS),
    ("army", BUCKET_MILITARY),
    ("navy", BUCKET_MILITARY),
    ("military", BUCKET_MILITARY),
    ("garrison", BUCKET_MILITARY),
    ("government", BUCKET_GOVERNMENT),
    ("bureau", BUCKET_GOVERNMENT),
    ("urban", BUCKET_INFRASTRUCTURE),
    ("infrastructure", BUCKET_INFRASTRUCTURE),
    ("construction", BUCKET_INFRASTRUCTURE),
    ("power", BUCKET_INFRASTRUCTURE),
    ("manufactur", BUCKET_MANUFACTURING),
    ("industry", BUCKET_MANUFACTURING),
    ("trade", BUCKET_SERVICE),
    ("financial", BUCKET_SERVICE),
]


def building_bucket(chain: list[str]) -> str:
    """Return the canonical bucket id (caller translates via ui[f'bucket_{id}'])."""
    if not chain:
        return BUCKET_OTHER
    for bg in chain:
        if bg in BG_BUCKET:
            return BG_BUCKET[bg]
    for pattern, bucket in _BG_PATTERNS:
        if pattern in chain[0]:
            return bucket
    return BUCKET_OTHER


def category_from_pmg_name(pmg_id: str) -> str:
    """Return a canonical category id (base/secondary/automation/ownership)."""
    name = pmg_id
    if name.startswith("pmg_base") or name == "pmg_dummy":
        return CAT_BASE
    if "_automation" in name or "_harvesting_process" in name:
        return CAT_AUTOMATION
    if name.startswith("pmg_ownership") or name.startswith("pmg_additional_ownership") or name == "pmg_serfdom":
        return CAT_OWNERSHIP
    return CAT_SECONDARY


def is_dummy_building_name(localized: str) -> bool:
    return len(localized) > DUMMY_NAME_LEN


def fmt_goods_dict(goods_qty: dict[str, float], loc_name) -> str:
    if not goods_qty:
        return ""
    parts = []
    for gid, qty in goods_qty.items():
        name = loc_name(gid)
        parts.append(f"{name} ×{_fmt_num(qty)}")
    return ", ".join(parts)


def _fmt_num(x: float) -> str:
    if x == int(x):
        return str(int(x))
    return f"{x:.2f}".rstrip("0").rstrip(".")


# --- PM notes formatting ----------------------------------------------------

# Each modifier key maps to a UI-translation key (resolved via i18n at render).
_NOTE_LABEL_KEYS: dict[str, str] = {
    "country_prestige_add": "mod_prestige",
    "country_authority_add": "mod_authority",
    "country_authority_mult": "mod_authority_pct",
    "country_influence_add": "mod_influence",
    "country_bureaucracy_add": "mod_bureaucracy",
    "country_bureaucracy_mult": "mod_bureaucracy_pct",
    "country_loan_interest_rate_add": "mod_loan_rate",
    "country_loan_interest_rate_mult": "mod_loan_rate_pct",
    "country_legitimacy_base_add": "mod_legitimacy",
    "country_max_declared_interests_add": "mod_max_interests",
    "country_aristocrats_pol_str_mult": "mod_aristo_pol",
    "country_capitalists_pol_str_mult": "mod_capi_pol",
    "country_clergymen_pol_str_mult": "mod_clergy_pol",
    "country_intelligentsia_pol_str_mult": "mod_intel_pol",
    "state_decree_cost_mult": "mod_decree_cost",
    "state_pollution_generation_add": "mod_pollution",
    "state_radicals_from_sol_change_mult": "mod_radicals_sol",
    "state_loyalists_from_sol_change_mult": "mod_loyalists_sol",
    "state_birth_rate_mult": "mod_birth_rate",
    "state_mortality_mult": "mod_mortality",
    "state_population_premium_standard_of_living_add": "mod_high_sol",
    "building_throughput_add": "mod_throughput",
    "building_throughput_mult": "mod_throughput_pct",
    "building_production_mult": "mod_production_pct",
    "building_input_mult": "mod_input_pct",
}

_IG_PREFIX = "interest_group_ig_"
_IG_KEYS = {
    "devout": "ig_devout",
    "rural_folk": "ig_rural_folk",
    "intelligentsia": "ig_intelligentsia",
    "industrialists": "ig_industrialists",
    "armed_forces": "ig_armed_forces",
    "petite_bourgeoisie": "ig_petite_bourgeoisie",
    "trade_unions": "ig_trade_unions",
    "landowners": "ig_landowners",
}


def _format_modifier(key: str, value: float, ui: UI, loc=None) -> str | None:
    label: str | None = None
    label_key = _NOTE_LABEL_KEYS.get(key)
    if label_key is not None:
        label = ui[label_key]
    elif key.startswith(_IG_PREFIX):
        rest = key[len(_IG_PREFIX):]
        for short, ig_key in _IG_KEYS.items():
            if rest.startswith(short + "_"):
                tail = rest[len(short) + 1:]
                ig_name = ui[ig_key]
                if tail == "pol_str_mult":
                    label = f"{ig_name}{ui['ig_pol_suffix']}"
                elif tail == "approval_add":
                    label = f"{ig_name}{ui['ig_app_suffix']}"
                else:
                    label = f"{ig_name} {tail}"
                break

    # If we still don't have a label, try the game's own modifier loc files —
    # they cover hundreds of modifier keys we don't manually translate.
    is_pct = False
    if label is None and loc is not None:
        translated = loc.get_clean(key)
        if translated and translated != key:
            label = translated
            is_pct = key.endswith("_mult")

    if label is None:
        # Generic English fallback (last resort)
        clean = key
        for p in ("country_", "state_", "building_"):
            if clean.startswith(p):
                clean = clean[len(p):]
                break
        clean = clean.replace("_add", "").replace("_mult", "%").replace("_", " ")
        label = clean

    sign = "+" if value > 0 else ""
    if label.endswith("%"):
        return f"{sign}{value*100:.0f}% {label[:-1]}"
    if is_pct:
        return f"{sign}{value*100:.0f}% {label}"
    return f"{sign}{_fmt_num(value)} {label}"


def pm_notes(pm, ui: UI, loc=None) -> str:
    parts: list[str] = []
    for k, v in pm.country_modifiers.items():
        if k == "country_construction_add" or v == 0:
            continue
        s = _format_modifier(k, v, ui, loc)
        if s:
            parts.append(s)
    for k, v in pm.state_modifiers.items():
        if v == 0:
            continue
        s = _format_modifier(k, v, ui, loc)
        if s:
            parts.append(s)
    return "; ".join(parts)


def is_passive_pm(pm) -> bool:
    return (
        not pm.outputs and not pm.inputs
        and not pm.employment
        and pm.construction_output == 0
    )
