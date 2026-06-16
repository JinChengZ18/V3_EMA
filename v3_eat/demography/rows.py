from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from .constants import PopGrowthConstants
from .i18n import tr_label
from .model import Scenario, adjusted_rates, project_workforce_ratio


def write_csv(
    path: Path,
    rows: list[dict[str, object]],
    fieldnames: list[str] | None = None,
    *,
    float_digits: int | None = 6,
) -> None:
    """Write ``rows`` as CSV. Floats are rounded to ``float_digits`` decimal places
    so the output is free of binary-float artefacts like ``0.05399999999999999``.
    Pass ``float_digits=None`` to disable rounding.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []

    def _format(value: object) -> object:
        if float_digits is not None and isinstance(value, float):
            return round(value, float_digits)
        return value

    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _format(v) for k, v in row.items()})


def first_matching(rows: list[dict[str, object]], **criteria: object) -> dict[str, object] | None:
    for row in rows:
        ok = True
        for key, expected in criteria.items():
            value = row.get(key)
            if isinstance(expected, float):
                ok = abs(float(value) - expected) <= 1e-9
            else:
                ok = value == expected
            if not ok:
                break
        if ok:
            return row
    return None


def final_matching(rows: list[dict[str, object]], **criteria: object) -> dict[str, object] | None:
    matches = [row for row in rows if all(row.get(k) == v for k, v in criteria.items())]
    if not matches:
        return None
    return max(matches, key=lambda row: float(row.get("month", 0.0)))


def make_rates_rows(
    scenarios: list[Scenario],
    constants: PopGrowthConstants,
    sol_min: int,
    sol_max: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for scenario in scenarios:
        for sol in range(sol_min, sol_max + 1):
            rates = adjusted_rates(float(sol), scenario, constants)
            rows.append({"scenario": scenario.name, **rates})
    return rows


def make_grouped_rates_rows(
    groups: dict[str, list[Scenario]],
    constants: PopGrowthConstants,
    sol_min: int,
    sol_max: int,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group, scenarios in groups.items():
        for row in make_rates_rows(scenarios, constants, sol_min, sol_max):
            rows.append({"factor_group": group, **row})
    return rows


def make_projection_rows(
    scenarios: list[Scenario],
    constants: PopGrowthConstants,
    *,
    sol: float,
    months: int,
    population: float,
    initial_workforce_ratio: float,
    target_workforce_ratio: float | None,
    sol_trajectory=None,
    use_skew: bool = True,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for scenario in scenarios:
        # Per-scenario projection_sol (e.g. the SoL-sensitivity group) overrides
        # the global SoL trajectory.
        if scenario.projection_sol is not None:
            scenario_sol = scenario.projection_sol
            trajectory = None
        else:
            scenario_sol = sol
            trajectory = sol_trajectory
        projected_scenario = replace(
            scenario,
            initial_workforce_ratio=initial_workforce_ratio,
            target_workforce_ratio=(
                scenario.target_workforce_ratio
                if target_workforce_ratio is None
                else target_workforce_ratio
            ),
        )
        rows.extend(
            project_workforce_ratio(
                projected_scenario,
                constants,
                sol=scenario_sol,
                months=months,
                population=population,
                sol_trajectory=trajectory,
                use_skew=use_skew,
            )
        )
    return rows


def make_workforce_sensitivity_rows(
    groups: dict[str, list[Scenario]],
    constants: PopGrowthConstants,
    *,
    sol: float,
    months: int,
    population: float,
    initial_workforce_ratio: float,
    default_target_workforce_ratio: float,
    sol_trajectory=None,
    use_skew: bool = True,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group, scenarios in groups.items():
        use_scenario_targets = group == "target_ratio"
        group_rows = make_projection_rows(
            scenarios,
            constants,
            sol=sol,
            months=months,
            population=population,
            initial_workforce_ratio=initial_workforce_ratio,
            target_workforce_ratio=None if use_scenario_targets else default_target_workforce_ratio,
            sol_trajectory=sol_trajectory,
            use_skew=use_skew,
        )
        rows.extend({"factor_group": group, **row} for row in group_rows)
    return rows


def projection_series_from_rows(rows: list[dict[str, object]], language: str) -> list[tuple[str, list[tuple[float, float]]]]:
    grouped: dict[str, list[tuple[float, float]]] = {}
    order: list[str] = []
    for row in rows:
        name = str(row["scenario"])
        if name not in grouped:
            grouped[name] = []
            order.append(name)
        grouped[name].append((float(row["year"]), float(row["workforce_ratio"])))
    return [(tr_label(name, language), grouped[name]) for name in order]


def net_growth_series_from_rows(rows: list[dict[str, object]], language: str) -> list[tuple[str, list[tuple[float, float]]]]:
    grouped: dict[str, list[tuple[float, float]]] = {}
    order: list[str] = []
    for row in rows:
        name = str(row["scenario"])
        if name not in grouped:
            grouped[name] = []
            order.append(name)
        grouped[name].append((float(row["sol"]), float(row["net_annual"])))
    return [(tr_label(name, language), grouped[name]) for name in order]


def population_index_series_from_rows(rows: list[dict[str, object]], language: str) -> list[tuple[str, list[tuple[float, float]]]]:
    grouped: dict[str, list[tuple[float, float]]] = {}
    initial_population: dict[str, float] = {}
    order: list[str] = []
    for row in rows:
        name = str(row["scenario"])
        if name not in grouped:
            grouped[name] = []
            initial_population[name] = max(float(row["population"]), 1.0)
            order.append(name)
        grouped[name].append((float(row["year"]), float(row["population"]) / initial_population[name]))
    return [(tr_label(name, language), grouped[name]) for name in order]


def localized_series(series: list[tuple[str, list[tuple[float, float]]]], language: str) -> list[tuple[str, list[tuple[float, float]]]]:
    return [(tr_label(name, language), points) for name, points in series]
