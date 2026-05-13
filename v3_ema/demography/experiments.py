"""Derived gameplay-decision metrics on top of the base model.

The analysis report uses these helpers to answer concrete in-game questions:
"which health system?", "is the food company worth a slot?", "how do I
fastest grow the workforce ratio?", etc.
"""
from __future__ import annotations

import math
from dataclasses import replace
from typing import Callable

from .constants import PopGrowthConstants
from .model import (
    Scenario,
    adjusted_rates,
    base_birth_rate,
    base_mortality,
    project_workforce_ratio,
    sol_to_wealth,
)
from .scenarios import workforce_sensitivity_scenarios
from .util import clamp


# ---------------------------------------------------------------------------
# Section 0 / 1 — base curve sweet spot & summary
# ---------------------------------------------------------------------------

def pop_growth_sweet_spot(constants: PopGrowthConstants, *, step: float = 0.1) -> tuple[float, float]:
    """Find the SoL where annual net growth peaks on the base curve.

    Returns ``(sol_at_peak, annual_net_growth_at_peak)``. We scan with a fine
    step because the piecewise curves have kinks at SoL 5 / 10 / 15 / 25.
    """
    best_sol = 0.0
    best_net = -math.inf
    sol = 0.0
    while sol <= 35.0:
        rate = (base_birth_rate(sol, constants) - base_mortality(sol, constants)) * 12.0
        if rate > best_net:
            best_net = rate
            best_sol = sol
        sol += step
    return best_sol, best_net


def base_rate_at(sol: float, constants: PopGrowthConstants) -> tuple[float, float, float]:
    """Annual (birth, mortality, net) at a given SoL with no modifiers."""
    b = base_birth_rate(sol, constants) * 12.0
    m = base_mortality(sol, constants) * 12.0
    return b, m, b - m


# ---------------------------------------------------------------------------
# Section 2 — healthcare law decision
# ---------------------------------------------------------------------------

def _healthcare_scenarios(constants: PopGrowthConstants, *, pollution: float) -> dict[str, Scenario]:
    """Return name → Scenario for the four health-system tiers at a given
    pollution level. Values come straight from the law file (see
    ``game_modifiers.load_game_modifiers``); pinned defaults here match
    game 1.9.x at release.
    """
    base = constants.working_adult_ratio_base
    return {
        "no_health": Scenario(
            "No health system",
            target_workforce_ratio=base,
            pollution_impact=pollution,
        ),
        "charitable": Scenario(
            "Charitable health",
            mortality_mult=-0.03,
            pollution_health_reduction_mult=-0.10,
            target_workforce_ratio=base,
            pollution_impact=pollution,
        ),
        "public": Scenario(
            "Public health",
            mortality_mult=-0.05,
            pollution_health_reduction_mult=-0.15,
            target_workforce_ratio=base,
            pollution_impact=pollution,
        ),
        "private": Scenario(
            "Private health",
            mortality_wealth_mult=-0.002,
            wealth_from_sol=True,
            pollution_health_reduction_mult=-0.10,
            target_workforce_ratio=base,
            pollution_impact=pollution,
        ),
    }


def healthcare_comparison_table(
    constants: PopGrowthConstants,
    *,
    sols: tuple[float, ...] = (10.0, 12.0, 15.0, 18.0, 22.0),
    pollution_levels: tuple[float, ...] = (0.0, 0.5),
) -> list[dict[str, object]]:
    """One row per (sol, pollution, system) with annual mortality and net growth."""
    rows: list[dict[str, object]] = []
    for pollution in pollution_levels:
        scenarios = _healthcare_scenarios(constants, pollution=pollution)
        for sol in sols:
            for key, scenario in scenarios.items():
                rates = adjusted_rates(sol, scenario, constants)
                rows.append({
                    "sol": sol,
                    "pollution_impact": pollution,
                    "system_key": key,
                    "system": scenario.name,
                    "mortality_annual": rates["mortality_annual"],
                    "birth_annual": rates["birth_annual"],
                    "net_annual": rates["net_annual"],
                })
    return rows


def private_vs_public_breakeven_sol(constants: PopGrowthConstants) -> float:
    """SoL at which private health's wealth-scaled mortality reduction
    equals public health's flat reduction.

    public: mortality_mult contribution = -0.05.
    private: mortality_mult contribution = -0.002 * sol_to_wealth(SoL).
    Solve -0.002 * 1.5 * SoL = -0.05 → SoL = 0.05 / 0.003 ≈ 16.67.
    """
    public_reduction = 0.05
    # Inverted from sol_to_wealth(SoL) = WEALTH_FROM_SOL_SLOPE * SoL.
    return public_reduction / 0.002 / (sol_to_wealth(1.0))


def population_after_years(
    scenario: Scenario,
    constants: PopGrowthConstants,
    *,
    sol: float,
    years: int = 100,
    population: float = 1_000_000.0,
) -> float:
    """Run the projection and return the final total population."""
    rows = project_workforce_ratio(
        scenario, constants, sol=sol, months=years * 12, population=population,
    )
    return rows[-1]["population"]


def healthcare_100y_population_index(
    constants: PopGrowthConstants,
    *,
    sols: tuple[float, ...] = (10.0, 15.0, 20.0),
    pollution_levels: tuple[float, ...] = (0.0, 0.5),
    years: int = 100,
) -> list[dict[str, object]]:
    """Final-population index (no-health = 1.00) per (sol, pollution, system)."""
    rows: list[dict[str, object]] = []
    for pollution in pollution_levels:
        scenarios = _healthcare_scenarios(constants, pollution=pollution)
        for sol in sols:
            baseline_pop = population_after_years(
                scenarios["no_health"], constants, sol=sol, years=years,
            )
            for key, scenario in scenarios.items():
                pop = population_after_years(scenario, constants, sol=sol, years=years)
                rows.append({
                    "sol": sol,
                    "pollution_impact": pollution,
                    "system_key": key,
                    "system": scenario.name,
                    "population_index_vs_no_health": pop / baseline_pop,
                    "final_population": pop,
                })
    return rows


# ---------------------------------------------------------------------------
# Section 3 — food company (company_basic_food prosperity_modifier)
# ---------------------------------------------------------------------------

def food_company_comparison(
    constants: PopGrowthConstants,
    *,
    sols: tuple[float, ...] = (5.0, 10.0, 12.0, 15.0, 18.0, 22.0),
    years: int = 100,
) -> list[dict[str, object]]:
    """Compare base vs +5% birth rate (food company prosperity) at each SoL.

    Reports the absolute net-growth delta and the 100-year population gain
    multiplier — which is much larger than the rate delta suggests because of
    compounding.
    """
    rows: list[dict[str, object]] = []
    base_target = constants.working_adult_ratio_base
    for sol in sols:
        baseline = Scenario("baseline", target_workforce_ratio=base_target)
        food = Scenario("food", birth_mult=0.05, target_workforce_ratio=base_target)
        b_rates = adjusted_rates(sol, baseline, constants)
        f_rates = adjusted_rates(sol, food, constants)
        b_pop = population_after_years(baseline, constants, sol=sol, years=years)
        f_pop = population_after_years(food, constants, sol=sol, years=years)
        rows.append({
            "sol": sol,
            "base_net_annual": b_rates["net_annual"],
            "food_net_annual": f_rates["net_annual"],
            "net_growth_delta": f_rates["net_annual"] - b_rates["net_annual"],
            "population_multiplier_after_years": f_pop / b_pop if b_pop > 0 else float("nan"),
            "years": years,
        })
    return rows


# ---------------------------------------------------------------------------
# Section 4 — workforce ratio levers
# ---------------------------------------------------------------------------

def time_to_target_ratio(
    scenario: Scenario,
    constants: PopGrowthConstants,
    *,
    sol: float,
    target_ratio_check: float,
    months: int = 1200,
    population: float = 1_000_000.0,
) -> float | None:
    """Years until the projection reaches ``target_ratio_check``. Returns
    ``None`` if not reached within ``months``.
    """
    rows = project_workforce_ratio(scenario, constants, sol=sol, months=months, population=population)
    for row in rows:
        if row["workforce_ratio"] >= target_ratio_check:
            return row["year"]
    return None


def workforce_ratio_lever_table(
    constants: PopGrowthConstants,
    *,
    initial_ratio: float = 0.25,
    sol_baseline: float = 12.0,
    months: int = 1200,
) -> list[dict[str, object]]:
    """Compare years-to-40%/45% under different policy combinations."""
    base = constants.working_adult_ratio_base
    rows: list[dict[str, object]] = []
    cases = [
        # (label_key, target_ratio, birth_mult, sol, notes_key)
        ("baseline_target_50", base + 0.25, 0.0, sol_baseline, "lever_note_baseline"),
        ("workplace_only", base + 0.10, -0.05, sol_baseline, "lever_note_workplace"),
        ("suffrage", base + 0.15, -0.05, sol_baseline, "lever_note_suffrage"),
        ("suffrage_unions", base + 0.25, -0.05, sol_baseline, "lever_note_suffrage_unions"),
        ("food_only", base + 0.25, 0.05, sol_baseline, "lever_note_food_only"),
        ("high_sol", base + 0.25, 0.0, 15.0, "lever_note_high_sol"),
        # All combined = suffrage's -0.05 + food's +0.05 → net 0; SoL 12 is
        # faster than SoL 15 because higher SoL drops the birth rate, which
        # is what drives convergence.
        ("all_combined", base + 0.25, 0.0, sol_baseline, "lever_note_all_combined"),
    ]
    for label_key, target, birth_mult, sol, notes_key in cases:
        s = Scenario(
            label_key,
            birth_mult=birth_mult,
            target_workforce_ratio=target,
            initial_workforce_ratio=initial_ratio,
        )
        t40 = time_to_target_ratio(s, constants, sol=sol, target_ratio_check=0.40, months=months)
        t45 = time_to_target_ratio(s, constants, sol=sol, target_ratio_check=0.45, months=months)
        final_rows = project_workforce_ratio(s, constants, sol=sol, months=months, population=1_000_000.0)
        rows.append({
            "label_key": label_key,
            "notes_key": notes_key,
            "target_ratio": target,
            "birth_mult": birth_mult,
            "sol": sol,
            "years_to_40pct": t40,
            "years_to_45pct": t45,
            "ratio_after_50y": final_rows[599]["workforce_ratio"] if len(final_rows) > 599 else final_rows[-1]["workforce_ratio"],
            "ratio_after_100y": final_rows[-1]["workforce_ratio"],
        })
    return rows


# ---------------------------------------------------------------------------
# Section 5 — industrialization population cost (pollution + health)
# ---------------------------------------------------------------------------

def industrial_vs_agrarian_table(
    constants: PopGrowthConstants,
    *,
    sol: float = 14.0,
    years: int = 80,
    pollution_levels: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> list[dict[str, object]]:
    """For a state with given pollution impact, compare 80-year pop growth
    under (a) no health system and (b) public health.
    """
    rows: list[dict[str, object]] = []
    base = constants.working_adult_ratio_base
    for pollution in pollution_levels:
        no_health = Scenario(
            "no_health",
            target_workforce_ratio=base,
            pollution_impact=pollution,
        )
        public = Scenario(
            "public",
            mortality_mult=-0.05,
            pollution_health_reduction_mult=-0.15,
            target_workforce_ratio=base,
            pollution_impact=pollution,
        )
        no_pop = population_after_years(no_health, constants, sol=sol, years=years)
        pub_pop = population_after_years(public, constants, sol=sol, years=years)
        rows.append({
            "pollution_impact": pollution,
            "no_health_pop_index": no_pop / 1_000_000.0,
            "public_health_pop_index": pub_pop / 1_000_000.0,
            "public_health_uplift_pct": (pub_pop / no_pop - 1.0) * 100 if no_pop > 0 else 0.0,
        })
    return rows


# ---------------------------------------------------------------------------
# Section 6 — starvation recovery
# ---------------------------------------------------------------------------

def starvation_recovery_curve(
    constants: PopGrowthConstants,
    *,
    sol: float = 12.0,
    starvation_years: int = 5,
    recovery_years: int = 30,
    population: float = 1_000_000.0,
    severity: str = "partial",
) -> list[dict[str, object]]:
    """Run a 2-phase projection: ``starvation_years`` of starvation, then
    ``recovery_years`` of normal growth. Returns yearly population samples.
    """
    if severity == "severe":
        starv_scenario = Scenario("severe", birth_mult=-0.90, mortality_mult=1.00)
    else:
        # Engine scales starvation_penalty by Starvation level up to ~50%
        # strength, so the typical effective values are halved.
        starv_scenario = Scenario("partial", birth_mult=-0.35, mortality_mult=0.30)
    recovery_scenario = Scenario("recovery")

    months_phase1 = starvation_years * 12
    phase1 = project_workforce_ratio(
        starv_scenario, constants, sol=sol, months=months_phase1, population=population,
    )
    # Pick up where phase 1 left off (use final population for phase 2 start).
    pop_after_starv = phase1[-1]["population"]
    months_phase2 = recovery_years * 12
    phase2 = project_workforce_ratio(
        recovery_scenario, constants, sol=sol, months=months_phase2, population=pop_after_starv,
    )

    out: list[dict[str, object]] = []
    for row in phase1:
        out.append({
            "year": row["year"],
            "phase": "starvation",
            "population": row["population"],
            "population_index": row["population"] / population,
        })
    last_phase1_year = phase1[-1]["year"]
    # Skip phase2's month-0 row to avoid the duplicate boundary sample.
    for row in phase2[1:]:
        out.append({
            "year": last_phase1_year + row["year"],
            "phase": "recovery",
            "population": row["population"],
            "population_index": row["population"] / population,
        })
    return out


def starvation_summary(
    constants: PopGrowthConstants,
    *,
    sol: float = 12.0,
    starvation_years: int = 5,
    severity: str = "partial",
) -> dict[str, object]:
    """One-line summary: how much pop you lose, and how many years to recover
    to pre-famine population.
    """
    curve = starvation_recovery_curve(
        constants, sol=sol, starvation_years=starvation_years,
        recovery_years=50, severity=severity,
    )
    initial = curve[0]["population_index"]
    trough = min(r["population_index"] for r in curve if r["phase"] == "starvation")
    years_to_recover: float | None = None
    starv_end_year = starvation_years
    for r in curve:
        if r["phase"] == "recovery" and r["population_index"] >= initial:
            years_to_recover = r["year"] - starv_end_year
            break
    return {
        "severity": severity,
        "sol": sol,
        "starvation_years": starvation_years,
        "pop_loss_pct": (1.0 - trough) * 100,
        "years_to_recover": years_to_recover,
    }


# ---------------------------------------------------------------------------
# Section 7 — literacy birth-rate cost
# ---------------------------------------------------------------------------

def literacy_birth_rate_table(
    constants: PopGrowthConstants,
    *,
    sols: tuple[float, ...] = (10.0, 12.0, 15.0, 18.0),
    literacy_levels: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0),
) -> list[dict[str, object]]:
    """Show the absolute birth-rate drop caused by literacy_penalty at each
    (sol, literacy) cell.
    """
    rows: list[dict[str, object]] = []
    for sol in sols:
        baseline = adjusted_rates(sol, Scenario("base"), constants)
        for lit in literacy_levels:
            r = adjusted_rates(sol, Scenario("lit", literacy=lit), constants)
            rows.append({
                "sol": sol,
                "literacy": lit,
                "birth_annual": r["birth_annual"],
                "birth_delta_vs_zero": r["birth_annual"] - baseline["birth_annual"],
                "net_annual": r["net_annual"],
            })
    return rows
