"""Assemble Scenarios from live game files (M1 in the improvement plan).

The hardcoded ``default_scenarios`` / ``workforce_sensitivity_scenarios`` in
``scenarios.py`` ship known-good defaults so tests run without the game install.
This module reads the same modifier blocks out of ``game/common`` and builds
scenarios using parsed values; the CLI prefers this path so a future patch that
changes e.g. ``law_public_health.state_mortality_mult`` is reflected immediately.

Anything not found in the game files falls back to the hardcoded value, with a
warning printed to stderr (so the user notices when their game version has
diverged from the assumptions baked into ``scenarios.py``).
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from .constants import PopGrowthConstants
from .model import Scenario
from .modifier_lookup import parse_modifier_block
from .scenarios import (
    default_scenarios,
    workforce_sensitivity_scenarios,
)


# (file relative to game root, block name, attributes we care about)
_HEALTH_LAWS_FILE = Path("game/common/laws/00_health_system.txt")
_RIGHTS_OF_WOMEN_FILE = Path("game/common/laws/00_rights_of_women.txt")
_STATIC_MODIFIERS_FILE = Path("game/common/static_modifiers/00_code_static_modifiers.txt")


def _maybe_parse(path: Path, block: str) -> dict[str, float]:
    if not path.exists():
        print(f"warning: game file not found, falling back to hardcoded values: {path}", file=sys.stderr)
        return {}
    result = parse_modifier_block(path, block)
    if result is None:
        print(f"warning: block {block} not found in {path}, using hardcoded fallback", file=sys.stderr)
        return {}
    return result


def load_game_modifiers(game_root: Path) -> dict[str, dict[str, float]]:
    """Return a dict mapping logical scenario keys to their parsed numeric maps."""
    health_path = game_root / _HEALTH_LAWS_FILE
    women_path = game_root / _RIGHTS_OF_WOMEN_FILE
    static_path = game_root / _STATIC_MODIFIERS_FILE
    return {
        "charitable": _maybe_parse(health_path, "law_charitable_health_system"),
        "public": _maybe_parse(health_path, "law_public_health_insurance"),
        "private": _maybe_parse(health_path, "law_private_health_insurance"),
        "women_in_the_workplace": _maybe_parse(women_path, "law_women_in_the_workplace"),
        "womens_suffrage": _maybe_parse(women_path, "law_womens_suffrage"),
        "literacy": _maybe_parse(static_path, "literacy_penalty"),
        "starvation": _maybe_parse(static_path, "starvation_penalty"),
        "severe_starvation": _maybe_parse(static_path, "severe_starvation_penalty"),
        "pollution_health": _maybe_parse(static_path, "state_region_pollution_health"),
    }


def _g(d: dict[str, float], key: str, fallback: float) -> float:
    """Get ``d[key]`` if present, else ``fallback``."""
    if key in d:
        return d[key]
    return fallback


def _replace_by_name(scenarios: list[Scenario], name: str, **overrides) -> list[Scenario]:
    """Return a copy of ``scenarios`` with the scenario matching ``name`` replaced."""
    return [replace(s, **overrides) if s.name == name else s for s in scenarios]


def build_scenarios_from_game(
    game_root: Path, constants: PopGrowthConstants
) -> list[Scenario]:
    """Like ``default_scenarios`` but with values parsed from ``game/common``."""
    mods = load_game_modifiers(game_root)
    base = constants.working_adult_ratio_base
    scenarios = default_scenarios(constants)

    # Women's workplace: hardcoded ``birth=-0.05, target=base+0.10`` should
    # match game; override from parsed values just in case.
    wiw = mods["women_in_the_workplace"]
    if wiw:
        scenarios = _replace_by_name(
            scenarios,
            "Women's workplace",
            birth_mult=_g(wiw, "state_birth_rate_mult", -0.05),
            target_workforce_ratio=base + _g(wiw, "state_working_adult_ratio_add", 0.10),
        )

    # Severe starvation
    severe = mods["severe_starvation"]
    if severe:
        scenarios = _replace_by_name(
            scenarios,
            "Severe starvation",
            birth_mult=_g(severe, "state_birth_rate_mult", -0.90),
            mortality_mult=_g(severe, "state_mortality_mult", 1.00),
        )

    # Starvation (partial)
    starv = mods["starvation"]
    if starv:
        scenarios = _replace_by_name(
            scenarios,
            "Starvation (partial)",
            birth_mult=_g(starv, "state_birth_rate_mult", -0.25),
            mortality_mult=_g(starv, "state_mortality_mult", 0.60),
        )

    return scenarios


def build_sensitivity_scenarios_from_game(
    game_root: Path, constants: PopGrowthConstants
) -> dict[str, list[Scenario]]:
    """Like ``workforce_sensitivity_scenarios`` but health-system values come
    from the parsed laws."""
    mods = load_game_modifiers(game_root)
    base = constants.working_adult_ratio_base
    groups = workforce_sensitivity_scenarios(constants)

    charitable = mods["charitable"]
    public = mods["public"]
    private = mods["private"]

    if charitable:
        groups["healthcare"] = _replace_by_name(
            groups["healthcare"],
            "Charitable health",
            mortality_mult=_g(charitable, "state_mortality_mult", -0.03),
            pollution_health_reduction_mult=_g(charitable, "state_pollution_reduction_health_mult", -0.10),
        )
        groups["healthcare_pollution"] = _replace_by_name(
            groups["healthcare_pollution"],
            "Charitable health + pollution 50%",
            mortality_mult=_g(charitable, "state_mortality_mult", -0.03),
            pollution_health_reduction_mult=_g(charitable, "state_pollution_reduction_health_mult", -0.10),
        )
    if public:
        groups["healthcare"] = _replace_by_name(
            groups["healthcare"],
            "Public health",
            mortality_mult=_g(public, "state_mortality_mult", -0.05),
            pollution_health_reduction_mult=_g(public, "state_pollution_reduction_health_mult", -0.15),
        )
        groups["healthcare_pollution"] = _replace_by_name(
            groups["healthcare_pollution"],
            "Public health + pollution 50%",
            mortality_mult=_g(public, "state_mortality_mult", -0.05),
            pollution_health_reduction_mult=_g(public, "state_pollution_reduction_health_mult", -0.15),
        )
    if private:
        groups["healthcare"] = _replace_by_name(
            groups["healthcare"],
            "Private health (wealth from SoL)",
            mortality_wealth_mult=_g(private, "state_mortality_wealth_mult", -0.002),
            pollution_health_reduction_mult=_g(private, "state_pollution_reduction_health_mult", -0.10),
        )
        groups["healthcare_pollution"] = _replace_by_name(
            groups["healthcare_pollution"],
            "Private health + pollution 50%",
            mortality_wealth_mult=_g(private, "state_mortality_wealth_mult", -0.002),
            pollution_health_reduction_mult=_g(private, "state_pollution_reduction_health_mult", -0.10),
        )

    # Suppress the unused variable warning while keeping the symbol explicit.
    _ = base
    return groups
