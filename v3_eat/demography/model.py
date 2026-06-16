from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import PopGrowthConstants
from .util import clamp


@dataclass(frozen=True)
class Scenario:
    name: str
    birth_mult: float = 0.0
    mortality_mult: float = 0.0
    mortality_wealth_mult: float = 0.0
    mortality_turmoil_mult: float = 0.0
    pollution_health_reduction_mult: float = 0.0
    literacy: float = 0.0
    wealth: float = 15.0
    wealth_from_sol: bool = False
    turmoil: float = 0.0
    pollution_impact: float = 0.0
    target_workforce_ratio: float = 0.25
    initial_workforce_ratio: float = 0.25
    projection_sol: float | None = None
    # Flat SoL bonus from the scenario itself (e.g. Public Health applies
    # state_standard_of_living_add = +0.5). Added BEFORE the pollution-driven
    # SoL penalty so it raises the effective SoL plugged into birth/mortality.
    sol_add: float = 0.0
    notes: str = ""


def base_birth_rate(sol: float, constants: PopGrowthConstants) -> float:
    sol = max(0.0, sol)
    if sol < constants.transition_sol:
        return sol * constants.birthrate_pretransition_slope + constants.max_birthrate
    if sol < constants.stable_sol:
        return sol * constants.birthrate_transition_slope + constants.birthrate_transition_intercept
    return constants.min_birthrate


def base_mortality(sol: float, constants: PopGrowthConstants) -> float:
    sol = max(0.0, sol)
    if sol < constants.equilibrium_sol:
        return sol * constants.mortality_starving_slope + constants.max_mortality
    if sol < constants.growth_max_sol:
        return (
            sol * constants.mortality_equilibrium_to_growth_max_slope
            + constants.mortality_equilibrium_to_growth_max_intercept
        )
    if sol < constants.stable_sol:
        return (
            sol * constants.mortality_growth_max_to_stable_slope
            + constants.mortality_growth_max_to_stable_intercept
        )
    return constants.min_mortality


WEALTH_FROM_SOL_SLOPE = 1.5
WEALTH_FROM_SOL_INTERCEPT = 0.0


def sol_to_wealth(sol: float) -> float:
    """Linear SoL→average-wealth proxy used when ``Scenario.wealth_from_sol`` is set.

    This is a deliberate simplification — engine wealth is determined per-pop
    by income bracket, but for ``state_mortality_wealth_mult`` (the private-
    healthcare channel) a single representative wealth per state is needed.
    Documented slope: at SoL 15 the average wealth comes out to ~22.5, matching
    the rough middle of the typical Pop Wealth bracket distribution.
    """
    return max(0.0, WEALTH_FROM_SOL_SLOPE * sol + WEALTH_FROM_SOL_INTERCEPT)


def pollution_impact_from_generation(
    generated_pollution: float, arable_land: float, constants: PopGrowthConstants
) -> float:
    divisor = constants.pollution_target_divisor_base + constants.pollution_target_divisor_arable_land_mult * math.sqrt(
        max(0.0, arable_land)
    )
    if divisor <= 0 or constants.pollution_max <= 0:
        return 0.0
    return clamp(generated_pollution / divisor / constants.pollution_max, 0.0, 1.0)


def simulate_pollution(
    generated_pollution: float,
    arable_land: float,
    constants: PopGrowthConstants,
    *,
    months: int,
    initial_impact: float = 0.0,
) -> list[dict[str, float]]:
    """Simulate transient pollution build-up toward its steady-state impact.

    The engine moves pollution toward its target at ``POLLUTION_CHANGE_SPEED``
    units per month and clamps to ``[0, POLLUTION_MAX]``. Working in
    ``pollution_impact`` (already normalized to [0, 1]) the equivalent per-step
    is ``impact += (target - impact) * change_speed / pollution_max``.
    """
    target_impact = pollution_impact_from_generation(generated_pollution, arable_land, constants)
    step = constants.pollution_change_speed / constants.pollution_max if constants.pollution_max > 0 else 0.0
    impact = clamp(initial_impact, 0.0, 1.0)
    rows: list[dict[str, float]] = [
        {
            "month": 0,
            "year": 0.0,
            "generated_pollution": generated_pollution,
            "arable_land": arable_land,
            "target_impact": target_impact,
            "pollution_impact": impact,
        }
    ]
    for month in range(1, months + 1):
        impact = clamp(impact + (target_impact - impact) * step, 0.0, 1.0)
        rows.append(
            {
                "month": month,
                "year": month / 12.0,
                "generated_pollution": generated_pollution,
                "arable_land": arable_land,
                "target_impact": target_impact,
                "pollution_impact": impact,
            }
        )
    return rows


def adjusted_rates(sol: float, scenario: Scenario, constants: PopGrowthConstants) -> dict[str, float]:
    pollution_impact = clamp(scenario.pollution_impact, 0.0, 1.0)
    # state_region_pollution_health is a single static-modifier block. The whole
    # block is reduced by state_pollution_reduction_health_mult, so both the
    # state_mortality_mult line *and* the state_standard_of_living_add line get
    # the same scaling. (See README "Model notes" for the assumption.)
    pollution_health_factor = max(0.0, 1.0 + scenario.pollution_health_reduction_mult)
    pollution_sol_penalty = -3.0 * pollution_impact * pollution_health_factor
    # Scenario-level flat SoL adds (e.g. Public Health's
    # state_standard_of_living_add = +0.5) raise the effective SoL plugged
    # into birth/mortality before the pollution penalty is applied.
    effective_sol = max(0.0, sol + scenario.sol_add + pollution_sol_penalty)

    birth_base = base_birth_rate(effective_sol, constants)
    mortality_base = base_mortality(effective_sol, constants)

    # literacy_penalty in 00_code_static_modifiers.txt is state_birth_rate_mult = -0.1
    # scaled by pop literacy.
    literacy_birth_mult = -0.10 * clamp(scenario.literacy, 0.0, 1.0)

    pollution_mortality_mult = 0.5 * pollution_impact * pollution_health_factor
    wealth_used = sol_to_wealth(sol) if scenario.wealth_from_sol else scenario.wealth
    wealth_mortality_mult = scenario.mortality_wealth_mult * wealth_used
    turmoil_mortality_mult = scenario.mortality_turmoil_mult * scenario.turmoil

    birth_mult_total = scenario.birth_mult + literacy_birth_mult
    mortality_mult_total = (
        scenario.mortality_mult
        + wealth_mortality_mult
        + turmoil_mortality_mult
        + pollution_mortality_mult
    )

    birth = max(0.0, birth_base * (1.0 + birth_mult_total))
    mortality = max(0.0, mortality_base * (1.0 + mortality_mult_total))

    return {
        "sol": sol,
        "effective_sol": effective_sol,
        "birth_base_monthly": birth_base,
        "mortality_base_monthly": mortality_base,
        "birth_mult_total": birth_mult_total,
        "mortality_mult_total": mortality_mult_total,
        "literacy_birth_mult": literacy_birth_mult,
        "pollution_sol_penalty": pollution_sol_penalty,
        "pollution_mortality_mult": pollution_mortality_mult,
        "wealth_mortality_mult": wealth_mortality_mult,
        "wealth_used": wealth_used,
        "turmoil_mortality_mult": turmoil_mortality_mult,
        "birth_monthly": birth,
        "mortality_monthly": mortality,
        "net_monthly": birth - mortality,
        "birth_annual": birth * 12.0,
        "mortality_annual": mortality * 12.0,
        "net_annual": (birth - mortality) * 12.0,
    }


def _skew_factor(current_ratio: float, target_ratio: float, skew_max: float) -> float:
    """Skew factor controlling how mortality is distributed between dependents
    and workforce. ``1.0`` means uniform (no skew).

    Engine has ``WORKING_ADULT_RATIO_SKEW_MAXIMUM`` (default 2.0) that caps the
    correction. The exact C++ formula is not exposed in script files, so this is
    an approximation: ``skew = clamp(target / current, 1/SKEW_MAX, SKEW_MAX)``.
    ``skew > 1`` shifts deaths toward dependents (pushes ratio up); ``skew < 1``
    shifts deaths toward workforce (pushes ratio down).
    """
    if current_ratio <= 0.0 or target_ratio <= 0.0:
        return 1.0
    raw = target_ratio / current_ratio
    return clamp(raw, 1.0 / skew_max, skew_max)


def project_workforce_ratio(
    scenario: Scenario,
    constants: PopGrowthConstants,
    *,
    sol: float,
    months: int,
    population: float,
    sol_trajectory=None,
    use_skew: bool = True,
) -> list[dict[str, float]]:
    """Project workforce ratio month-by-month for ``months`` steps.

    - ``sol_trajectory`` (optional): callable ``year -> sol``. When provided,
      ``adjusted_rates`` is recomputed each month and ``sol`` is the starting
      value (also used when the callable returns ``None``). When ``None``
      (default), SoL stays at ``sol`` and ``adjusted_rates`` is computed once.
    - ``use_skew`` (default True): apply the ``WORKING_ADULT_RATIO_SKEW_MAXIMUM``
      mortality-distribution correction. Set False for the legacy uniform model.
    """
    workforce = population * clamp(scenario.initial_workforce_ratio, 0.0, 1.0)
    dependents = population - workforce
    target_ratio = clamp(scenario.target_workforce_ratio, 0.0, 1.0)
    skew_max = constants.working_adult_ratio_skew_maximum if use_skew else 1.0

    # Static path: SoL is constant during the projection, so adjusted_rates is
    # invariant — compute once instead of once per month. (P1 in the plan.)
    if sol_trajectory is None:
        static_rates = adjusted_rates(sol, scenario, constants)
    else:
        static_rates = None

    rows: list[dict[str, float]] = []

    for month in range(months + 1):
        year = month / 12.0
        if sol_trajectory is None:
            current_sol = sol
            rates = static_rates
        else:
            traj_sol = sol_trajectory(year)
            current_sol = sol if traj_sol is None else float(traj_sol)
            rates = adjusted_rates(current_sol, scenario, constants)
        birth_monthly = rates["birth_monthly"]
        mortality_monthly = rates["mortality_monthly"]

        total = workforce + dependents
        ratio = workforce / total if total else 0.0
        rows.append(
            {
                "scenario": scenario.name,
                "sol": current_sol,
                "month": month,
                "year": year,
                "population": total,
                "workforce": workforce,
                "dependents": dependents,
                "workforce_ratio": ratio,
                "target_workforce_ratio": target_ratio,
                "effective_sol": rates["effective_sol"],
                "wealth_used": rates["wealth_used"],
                "birth_mult_total": rates["birth_mult_total"],
                "mortality_mult_total": rates["mortality_mult_total"],
                "birth_monthly": birth_monthly,
                "mortality_monthly": mortality_monthly,
            }
        )

        births = total * birth_monthly
        deaths = total * mortality_monthly
        skew = _skew_factor(ratio, target_ratio, skew_max)
        # Weighted death allocation: workforce keeps weight `ratio`, dependents
        # get weight `(1-ratio) * skew`. When skew = 1.0 this reduces to the
        # legacy uniform distribution.
        denom = ratio + (1.0 - ratio) * skew
        if denom > 0:
            deaths_workforce = min(workforce, deaths * ratio / denom)
            deaths_dependents = min(dependents, deaths * (1.0 - ratio) * skew / denom)
        else:
            deaths_workforce = 0.0
            deaths_dependents = 0.0
        births_workforce = births * target_ratio
        births_dependents = births * (1.0 - target_ratio)
        workforce = max(0.0, workforce + births_workforce - deaths_workforce)
        dependents = max(0.0, dependents + births_dependents - deaths_dependents)

    return rows
