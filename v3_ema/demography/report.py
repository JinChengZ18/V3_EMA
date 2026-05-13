from __future__ import annotations

import html
import math
from pathlib import Path

from .chart_svg import (
    STYLE_BIRTH,
    STYLE_MORTALITY,
    STYLE_NATURAL_GROWTH,
    svg_bar_chart,
    svg_line_chart,
)
from .experiments import (
    food_company_comparison,
    healthcare_100y_population_index,
    healthcare_comparison_table,
    industrial_vs_agrarian_table,
    literacy_birth_rate_table,
    pop_growth_sweet_spot,
    private_vs_public_breakeven_sol,
    starvation_recovery_curve,
    starvation_summary,
    workforce_ratio_lever_table,
)
from .i18n import (
    DATA_DICTIONARY,
    HEALTH_SYSTEM_LABELS,
    WORKFORCE_LEVER_LABELS,
)


BASE_SERIES_STYLE_KEYS = [STYLE_BIRTH, STYLE_MORTALITY, STYLE_NATURAL_GROWTH]


def _extract_months(projection_rows: list[dict[str, object]]) -> float:
    """Return the maximum ``month`` value seen in any projection row, or 0."""
    months_seen = [float(row.get("month", 0.0)) for row in projection_rows]
    return max(months_seen) if months_seen else 0.0
from .constants import PopGrowthConstants
from .i18n import (
    ANALYSIS_TEXT,
    NOTE_TRANSLATIONS_ZH,
    REPORT_TEXT,
    SENSITIVITY_GROUPS,
    SENSITIVITY_NOTES,
    tr_label,
    tr_note,
)
from .model import Scenario, base_birth_rate, base_mortality, project_workforce_ratio
from .rows import (
    final_matching,
    first_matching,
    localized_series,
    net_growth_series_from_rows,
    population_index_series_from_rows,
    projection_series_from_rows,
)
from .util import pct


REPORT_CSS = """\
body { margin: 0; font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; color: #172033; background: #f7f8fb; }
main { max-width: 1240px; margin: 0 auto; padding: 32px 28px 48px; }
h1 { margin: 0 0 8px; font-size: 30px; }
h2 { margin: 30px 0 12px; font-size: 21px; }
h3 { margin: 24px 0 8px; font-size: 16px; }
p { line-height: 1.55; }
.card { background: white; border: 1px solid #d9deea; border-radius: 8px; padding: 18px; margin: 16px 0; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04); }
.small { color: #5b6475; font-size: 13px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { border-bottom: 1px solid #e5e9f2; padding: 8px 9px; text-align: left; vertical-align: top; }
th { background: #f1f4f9; }
pre { overflow-x: auto; background: #111827; color: #e5e7eb; border-radius: 6px; padding: 14px; }
svg { width: 100%; height: auto; background: white; border: 1px solid #d9deea; border-radius: 8px; margin: 14px 0; }
.axis { stroke: #334155; stroke-width: 1.2; }
.grid { stroke: #e5e7eb; stroke-width: 1; }
.baseline { stroke: #111827; stroke-width: 1.6; stroke-dasharray: 5 4; }
.tick, .legend { fill: #475569; font-size: 12px; }
.chart-title { fill: #0f172a; font-size: 17px; font-weight: 700; }
.axis-label { fill: #475569; font-size: 12px; }"""

ANALYSIS_CSS = """\
body { margin: 0; font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif; color: #172033; background: #f7f8fb; }
main { max-width: 1120px; margin: 0 auto; padding: 34px 30px 56px; }
h1 { margin: 0 0 10px; font-size: 30px; }
h2 { margin: 32px 0 12px; font-size: 21px; }
h3 { margin: 22px 0 8px; font-size: 16px; }
p { line-height: 1.65; }
.abstract { background: white; border: 1px solid #d9deea; border-radius: 8px; padding: 18px; margin: 18px 0; }
.small { color: #5b6475; font-size: 13px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; background: white; border: 1px solid #d9deea; margin: 12px 0 18px; }
th, td { border-bottom: 1px solid #e5e9f2; padding: 8px 9px; text-align: left; vertical-align: top; }
th { background: #f1f4f9; }
pre { overflow-x: auto; background: #111827; color: #e5e7eb; border-radius: 6px; padding: 14px; }
svg { width: 100%; height: auto; background: white; border: 1px solid #d9deea; border-radius: 8px; margin: 14px 0 20px; }
.axis { stroke: #334155; stroke-width: 1.2; }
.grid { stroke: #e5e7eb; stroke-width: 1; }
.baseline { stroke: #111827; stroke-width: 1.6; stroke-dasharray: 5 4; }
.tick, .legend { fill: #475569; font-size: 12px; }
.chart-title { fill: #0f172a; font-size: 17px; font-weight: 700; }
.axis-label { fill: #475569; font-size: 12px; }"""


NET_OVERVIEW_EXCLUDE = {
    "Women's workplace",
    "Women's suffrage + food",
    "Women's suffrage + trade unions",
}

NET_SENSITIVITY_GROUP_KEYS = (
    "birth_multiplier",
    "mortality_multiplier",
    "literacy",
    "pollution",
    "healthcare",
    "healthcare_pollution",
)


def workforce_chart_bounds(initial_ratio: float, target_ratio: float) -> tuple[float, float, list[float]]:
    """Compute (y_min, y_max, y_ticks) for workforce charts so that the user-
    supplied initial/target ratios always fit with breathing room.

    Defaults (0.25, 0.50) reproduce the legacy 25%-50% chart bounds exactly.
    """
    lo = min(initial_ratio, target_ratio)
    hi = max(initial_ratio, target_ratio)
    # Round outward to nearest 5%, then add 0% padding on the side that already
    # has the user-supplied edge; clamp to [0, 1].
    pct_lo = max(0, math.floor(lo * 20) * 5)
    pct_hi = min(100, math.ceil(hi * 20) * 5)
    if pct_lo == pct_hi:
        pct_hi = min(100, pct_lo + 5)
    step = 5 if (pct_hi - pct_lo) <= 30 else 10
    pct_lo = (pct_lo // step) * step
    pct_hi = ((pct_hi + step - 1) // step) * step
    ticks = [v / 100.0 for v in range(int(pct_lo), int(pct_hi) + step, step)]
    return ticks[0], ticks[-1], ticks


def svg_workforce_chart(
    title: str,
    series: list[tuple[str, list[tuple[float, float]]]],
    *,
    x_label: str,
    y_label: str,
    palette: str = "categorical",
    bounds: tuple[float, float, list[float]] | None = None,
) -> str:
    if bounds is None:
        bounds = workforce_chart_bounds(0.25, 0.50)
    y_min, y_max, y_ticks = bounds
    return svg_line_chart(
        title,
        series,
        x_label=x_label,
        y_label=y_label,
        palette=palette,
        y_min=y_min,
        y_max=y_max,
        y_ticks=y_ticks,
        integer_percent_y_ticks=True,
    )


def formula_block(constants: PopGrowthConstants, language: str) -> str:
    if language == "zh":
        intro = "birth_base(s), mortality_base(s)：来自 game/common/defines/00_defines.txt 的分段线性月率"
    else:
        intro = "birth_base(s), mortality_base(s): piecewise linear monthly rates from game/common/defines/00_defines.txt"
    # Local import to avoid a top-level cycle; the constant lives in model.py.
    from .model import WEALTH_FROM_SOL_SLOPE
    wealth_slope = WEALTH_FROM_SOL_SLOPE
    skew_max = constants.working_adult_ratio_skew_maximum
    return f"""
    <pre>{intro}
pollution_health_factor = max(0, 1 + state_pollution_reduction_health_mult)
effective_sol = max(0, SoL - 3 * pollution_impact * pollution_health_factor)
wealth      = state.wealth if !wealth_from_sol else sol_to_wealth(SoL)  # = {wealth_slope:g} * SoL
birth     = birth_base(effective_sol)     * max(0, 1 + birth_mult - 0.10 * literacy)
mortality = mortality_base(effective_sol) * max(0,
    1 + mortality_mult
      + wealth  * state_mortality_wealth_mult
      + turmoil * state_mortality_turmoil_mult
      + 0.5 * pollution_impact * pollution_health_factor)
pollution_impact = clamp(generated_pollution / ({constants.pollution_target_divisor_base:g} + {constants.pollution_target_divisor_arable_land_mult:g} * sqrt(arable_land)) / {constants.pollution_max:g}, 0, 1)
target_workforce_ratio = pop_type_base + sum(state_working_adult_ratio_add)

# Workforce-ratio projection (per month, with skew correction):
skew              = clamp(target_workforce_ratio / current_workforce_ratio,
                          1/{skew_max:g}, {skew_max:g})
deaths_workforce  = total_deaths * ratio       / (ratio + (1 - ratio) * skew)
deaths_dependents = total_deaths * (1 - ratio) * skew / (ratio + (1 - ratio) * skew)
births_workforce  = total_births * target_workforce_ratio
births_dependents = total_births * (1 - target_workforce_ratio)
# --no-skew falls back to uniform: skew = 1.

# Transient pollution (M5):
impact[t+1] = clamp(impact[t] + (target - impact[t]) * {constants.pollution_change_speed:g} / {constants.pollution_max:g}, 0, 1)</pre>
    """


def _render_scenario_inputs_table(
    scenarios: list[Scenario], language: str, report_text: dict
) -> str:
    """Compact scenario-definition table. Column headers come from
    REPORT_TEXT so the wording matches the chart appendix."""
    rows_html = "\n".join(
        "<tr>"
        f"<td>{html.escape(tr_label(s.name, language))}</td>"
        f"<td>{pct(s.birth_mult, 1)}</td>"
        f"<td>{pct(s.mortality_mult, 1)}</td>"
        f"<td>{pct(s.literacy, 0)}</td>"
        f"<td>{pct(s.pollution_impact, 0)}</td>"
        f"<td>{pct(s.target_workforce_ratio, 1)}</td>"
        f"<td>{html.escape(tr_note(s, language))}</td>"
        "</tr>"
        for s in scenarios
    )
    return (
        "<table><thead><tr>"
        f"<th>{html.escape(report_text['scenario'])}</th>"
        f"<th>{html.escape(report_text['birth_mult'])}</th>"
        f"<th>{html.escape(report_text['mortality_mult'])}</th>"
        f"<th>{html.escape(report_text['literacy'])}</th>"
        f"<th>{html.escape(report_text['pollution'])}</th>"
        f"<th>{html.escape(report_text['target_workforce'])}</th>"
        f"<th>{html.escape(report_text['notes'])}</th>"
        f"</tr></thead><tbody>{rows_html}</tbody></table>"
    )


def _render_modifier_summary_table(
    source_summary: list[dict[str, str | float | int]],
    report_text: dict,
    *,
    top_n: int = 30,
) -> str:
    """Top-N modifier scan summary (counts + min/max). Headers from REPORT_TEXT."""
    rows_html = "\n".join(
        "<tr>"
        f"<td><code>{html.escape(str(r['key']))}</code></td>"
        f"<td>{r['count']}</td>"
        f"<td>{r['file_count']}</td>"
        f"<td>{r['min']}</td>"
        f"<td>{r['max']}</td>"
        "</tr>"
        for r in source_summary[:top_n]
    )
    return (
        "<table><thead><tr>"
        f"<th>{html.escape(report_text['key'])}</th>"
        f"<th>{html.escape(report_text['hits'])}</th>"
        f"<th>{html.escape(report_text['files'])}</th>"
        f"<th>{html.escape(report_text['min'])}</th>"
        f"<th>{html.escape(report_text['max'])}</th>"
        f"</tr></thead><tbody>{rows_html}</tbody></table>"
    )


_BASE_TABLE_HEADERS = {
    "en": ("SoL", "Birth (annual)", "Mortality (annual)", "Net (annual)"),
    "zh": ("SoL", "出生率（年）", "死亡率（年）", "净增长（年）"),
}


def _render_base_curve_table(
    rates_rows: list[dict[str, object]], language: str
) -> str:
    """Birth / mortality / net annual at a small set of reference SoL points."""
    base_rows = [
        first_matching(rates_rows, scenario="Base SoL curve", sol=float(sol))
        for sol in (5, 10, 12, 15, 18, 20, 25)
    ]
    body = "\n".join(
        f"<tr><td>{int(float(r['sol']))}</td>"
        f"<td>{pct(float(r['birth_annual']), 2)}</td>"
        f"<td>{pct(float(r['mortality_annual']), 2)}</td>"
        f"<td>{pct(float(r['net_annual']), 2)}</td></tr>"
        for r in base_rows
        if r is not None
    )
    headers = _BASE_TABLE_HEADERS.get(language, _BASE_TABLE_HEADERS["en"])
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _render_pollution_steady_table(
    rows: list[dict[str, object]], text: dict
) -> str:
    headers = (
        f"<tr><th>{html.escape(text['pollution_steady_col_gen'])}</th>"
        f"<th>{html.escape(text['pollution_steady_col_arable'])}</th>"
        f"<th>{html.escape(text['pollution_steady_col_impact'])}</th></tr>"
    )
    body = "\n".join(
        "<tr>"
        f"<td>{float(r['generated_pollution']):g}</td>"
        f"<td>{float(r['arable_land']):g}</td>"
        f"<td>{float(r['pollution_impact']) * 100:.2f}%</td>"
        "</tr>"
        for r in rows
    )
    return f"<table><thead>{headers}</thead><tbody>{body}</tbody></table>"


def _render_pollution_dynamics_chart(
    rows: list[dict[str, object]], text: dict
) -> str:
    """One series per distinct label, x = year, y = impact (0–1 scaled)."""
    series_dict: dict[str, list[tuple[float, float]]] = {}
    order: list[str] = []
    for r in rows:
        label = str(r["label"])
        if label not in series_dict:
            series_dict[label] = []
            order.append(label)
        series_dict[label].append((float(r["year"]), float(r["pollution_impact"])))
    return svg_line_chart(
        text["pollution_dynamics_chart"],
        [(name, series_dict[name]) for name in order],
        x_label=text["years_axis"],
        y_label=text["pollution"],
        y_as_percent=True,
        zero_baseline=False,
        palette="viridis",
    )


def _render_data_dictionary(text: dict, language: str) -> str:
    """Render DATA_DICTIONARY as one table per CSV (file → columns → meaning)."""
    lang_index = 1 if language == "en" else 2
    sections: list[str] = []
    for file_name, entries in DATA_DICTIONARY:
        rows_html = "\n".join(
            f"<tr><td><code>{html.escape(entry[0])}</code></td>"
            f"<td>{html.escape(entry[lang_index])}</td></tr>"
            for entry in entries
        )
        sections.append(
            f"<h3><code>{html.escape(file_name)}</code></h3>"
            f"<table><thead><tr>"
            f"<th>{html.escape(text['dict_col_column'])}</th>"
            f"<th>{html.escape(text['dict_col_meaning'])}</th>"
            f"</tr></thead><tbody>{rows_html}</tbody></table>"
        )
    return "\n".join(sections)


def build_html_report(
    *,
    game_root: Path,
    constants: PopGrowthConstants,
    scenarios: list[Scenario],
    rates_rows: list[dict[str, object]],
    projection_rows: list[dict[str, object]],
    growth_sensitivity_rows: list[dict[str, object]],
    sensitivity_rows: list[dict[str, object]],
    source_summary: list[dict[str, str | float | int]],
    pollution_examples: list[dict[str, object]] | None,
    pollution_dynamics_rows: list[dict[str, object]] | None,
    projection_initial_ratio: float,
    projection_target_ratio: float,
    projection_sol: float,
    language: str,
    compact: bool = False,
) -> str:
    text = REPORT_TEXT[language]
    sol_values = sorted({float(r["sol"]) for r in rates_rows})
    base_birth = [(s, base_birth_rate(s, constants) * 12.0) for s in sol_values]
    base_mortality_points = [(s, base_mortality(s, constants) * 12.0) for s in sol_values]
    base_natural_growth = [(s, birth - mortality) for (s, birth), (_, mortality) in zip(base_birth, base_mortality_points)]
    base_series = [
        ("birth", base_birth),
        ("mortality", base_mortality_points),
        ("natural growth", base_natural_growth),
    ]

    net_series = []
    for scenario in scenarios:
        if scenario.name in NET_OVERVIEW_EXCLUDE:
            continue
        points = [
            (float(r["sol"]), float(r["net_annual"]))
            for r in rates_rows
            if r["scenario"] == scenario.name
        ]
        if points:
            net_series.append((scenario.name, points))

    projection_series = projection_series_from_rows(projection_rows, language)
    if not projection_series:
        projection_series = [(tr_label(scenarios[0].name, language), [])]

    workforce_bounds = workforce_chart_bounds(projection_initial_ratio, projection_target_ratio)

    sensitivity_palette_map = {
        "birth_multiplier": "coolwarm",
        "mortality_multiplier": "coolwarm",
        "literacy": "viridis",
        "pollution": "viridis",
        "target_ratio": "viridis",
        "sol": "viridis",
        "healthcare": "categorical",
        "healthcare_pollution": "categorical",
    }

    def palette_for(group_key: str) -> str:
        return sensitivity_palette_map.get(group_key, "categorical")

    net_sensitivity_sections = []
    for group_key in NET_SENSITIVITY_GROUP_KEYS:
        group_rows = [row for row in growth_sensitivity_rows if row["factor_group"] == group_key]
        if not group_rows:
            continue
        title = SENSITIVITY_GROUPS[group_key][language]
        note = SENSITIVITY_NOTES[group_key][language]
        note_html = "" if compact else f'<p class="small">{html.escape(note)}</p>'
        net_sensitivity_sections.append(
            f"""
<h3>{html.escape(title)}</h3>
{note_html}
{svg_line_chart(title, net_growth_series_from_rows(group_rows, language), x_label=text["sol_axis"], y_label=text["net_axis"], y_scale="symlog", integer_percent_y_ticks=True, zero_baseline=True, palette=palette_for(group_key))}
"""
        )
    net_sensitivity_html = "\n".join(net_sensitivity_sections)

    sensitivity_sections = []
    for group_key, group_labels in SENSITIVITY_GROUPS.items():
        group_rows = [row for row in sensitivity_rows if row["factor_group"] == group_key]
        if not group_rows:
            continue
        title = group_labels[language]
        note = SENSITIVITY_NOTES[group_key][language]
        note_html = "" if compact else f'<p class="small">{html.escape(note)}</p>'
        population_chart = ""
        if group_key == "mortality_multiplier":
            population_chart = svg_line_chart(
                text["mortality_population_chart"],
                population_index_series_from_rows(group_rows, language),
                x_label=text["years_axis"],
                y_label=text["population_index_axis"],
                y_as_percent=False,
                palette=palette_for(group_key),
            )
        sensitivity_sections.append(
            f"""
<h3>{html.escape(title)}</h3>
{note_html}
{svg_workforce_chart(title, projection_series_from_rows(group_rows, language), x_label=text["years_axis"], y_label=text["workforce_axis"], palette=palette_for(group_key), bounds=workforce_bounds)}
{population_chart}
"""
        )
    sensitivity_html = "\n".join(sensitivity_sections)

    scenario_inputs_table = _render_scenario_inputs_table(scenarios, language, text)
    modifier_summary_table = _render_modifier_summary_table(source_summary, text, top_n=30)
    data_dict_html = _render_data_dictionary(text, language)
    pollution_steady_table_html = (
        _render_pollution_steady_table(pollution_examples, text)
        if pollution_examples else ""
    )

    return f"""<!doctype html>
<html lang="{text['html_lang']}">
<head>
<meta charset="utf-8">
<title>{html.escape(text['chart_appendix_title'])}</title>
<style>
{REPORT_CSS}
</style>
</head>
<body>
<main>
<h1>{html.escape(text['chart_appendix_title'])}</h1>
<p class="small">{text['chart_appendix_intro']}</p>

<h2>{html.escape(text['formula_title'])}</h2>
<div class="card">{formula_block(constants, language)}</div>

<h2>{html.escape(text['section_base_charts'])}</h2>
{svg_line_chart(text["base_chart"], localized_series(base_series, language), x_label=text["sol_axis"], y_label=text["rate_axis"], zero_baseline=True, style_keys=BASE_SERIES_STYLE_KEYS)}

<h2>{html.escape(text['section_scenarios_table'])}</h2>
{scenario_inputs_table}

<h2>{html.escape(text['section_net_charts'])}</h2>
{svg_line_chart(text["net_chart"], localized_series(net_series, language), x_label=text["sol_axis"], y_label=text["net_axis"], y_scale="symlog", integer_percent_y_ticks=True, zero_baseline=True)}
{net_sensitivity_html}

<h2>{html.escape(text['section_workforce_charts'])}</h2>
{svg_workforce_chart(text["workforce_chart"], projection_series, x_label=text["years_axis"], y_label=text["workforce_axis"], bounds=workforce_bounds)}
{sensitivity_html}

<h2>{html.escape(text['section_pollution_charts'])}</h2>
{pollution_steady_table_html}
{_render_pollution_dynamics_chart(pollution_dynamics_rows or [], text)}

<h2>{html.escape(text['section_modifier_section'])}</h2>
{svg_bar_chart(text["source_chart"], source_summary, key_field="key", value_field="count")}
{modifier_summary_table}

<h2>{html.escape(text['section_dict'])}</h2>
{data_dict_html}
</main>
</body>
</html>
"""


def _fmt_years(years: float | None, fallback: str = "—") -> str:
    if years is None:
        return fallback
    return f"{years:.0f}"


def _fmt_pct(value: float, digits: int = 2) -> str:
    return pct(value, digits)


def _fmt_signed_pp(value: float, digits: int = 2) -> str:
    """Format a value (already in percentage points, not a fraction) with sign."""
    return f"{value:+.{digits}f} pp"


def _system_label(key: str, language: str) -> str:
    return HEALTH_SYSTEM_LABELS[language].get(key, key)


def _render_tldr_table(text: dict, answers: dict[str, str]) -> str:
    rows = [
        ("tldr_q_health", "tldr_a_health"),
        ("tldr_q_food", "tldr_a_food"),
        ("tldr_q_workforce", "tldr_a_workforce"),
        ("tldr_q_polluted", "tldr_a_polluted"),
        ("tldr_q_starvation", "tldr_a_starvation"),
    ]
    body = "\n".join(
        f"<tr><td><strong>{html.escape(text[q])}</strong></td><td>{answers[a]}</td></tr>"
        for q, a in rows
    )
    return (
        f"<table><thead><tr>"
        f"<th style='width:35%'>{html.escape(text['tldr_col_question'])}</th>"
        f"<th>{html.escape(text['tldr_col_answer'])}</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


def _render_healthcare_mortality_table(
    rows: list[dict[str, object]], text: dict, language: str
) -> str:
    """One column per (system × pollution-level). Rows = SoL."""
    sols = sorted({float(r["sol"]) for r in rows})
    systems = [
        ("no_health", 0.0), ("charitable", 0.0), ("public", 0.0), ("private", 0.0),
        ("no_health", 0.5), ("charitable", 0.5), ("public", 0.5), ("private", 0.5),
    ]
    headers = "<tr><th>SoL</th>"
    for key, pollution in systems:
        suffix = " · 0%" if pollution == 0.0 else " · 50%"
        headers += f"<th>{html.escape(_system_label(key, language) + suffix)}</th>"
    headers += "</tr>"
    body_rows: list[str] = []
    for sol in sols:
        cells = [f"<td>{int(sol)}</td>"]
        for key, pollution in systems:
            match = next(
                (r for r in rows if float(r["sol"]) == sol and r["system_key"] == key and float(r["pollution_impact"]) == pollution),
                None,
            )
            cells.append(f"<td>{pct(float(match['mortality_annual']), 2)}</td>" if match else "<td>—</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead>{headers}</thead><tbody>{''.join(body_rows)}</tbody></table>"


def _render_healthcare_pop_table(
    rows: list[dict[str, object]], text: dict, language: str
) -> str:
    """For each (SoL, pollution) → final-population index column."""
    cells_by_key: dict[tuple[float, float], dict[str, float]] = {}
    for r in rows:
        key = (float(r["sol"]), float(r["pollution_impact"]))
        cells_by_key.setdefault(key, {})[str(r["system_key"])] = float(r["population_index_vs_no_health"])
    sols = sorted({k[0] for k in cells_by_key})
    pollutions = sorted({k[1] for k in cells_by_key})
    systems = ["no_health", "charitable", "public", "private"]
    headers = "<tr><th>SoL</th><th>" + html.escape(text["col_pollution"]) + "</th>"
    for s in systems:
        headers += f"<th>{html.escape(_system_label(s, language))}</th>"
    headers += "</tr>"
    body_rows: list[str] = []
    for sol in sols:
        for pollution in pollutions:
            cells = [f"<td>{int(sol)}</td>", f"<td>{int(pollution * 100)}%</td>"]
            row = cells_by_key.get((sol, pollution), {})
            for s in systems:
                v = row.get(s)
                cells.append(f"<td>{v:.2f}×</td>" if v is not None else "<td>—</td>")
            body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table><thead>{headers}</thead><tbody>{''.join(body_rows)}</tbody></table>"


def _render_food_table(rows: list[dict[str, object]], text: dict) -> str:
    headers = (
        f"<tr><th>{html.escape(text['col_sol'])}</th>"
        f"<th>{html.escape(text['col_food_net_base'])}</th>"
        f"<th>{html.escape(text['col_food_net_with'])}</th>"
        f"<th>{html.escape(text['col_food_delta'])}</th>"
        f"<th>{html.escape(text['col_food_multiplier'])}</th></tr>"
    )
    body = "\n".join(
        "<tr>"
        f"<td>{int(float(r['sol']))}</td>"
        f"<td>{pct(float(r['base_net_annual']), 2)}</td>"
        f"<td>{pct(float(r['food_net_annual']), 2)}</td>"
        f"<td>{pct(float(r['net_growth_delta']), 2)}</td>"
        f"<td>{float(r['population_multiplier_after_years']):.2f}×</td>"
        "</tr>"
        for r in rows
    )
    return f"<table><thead>{headers}</thead><tbody>{body}</tbody></table>"


def _render_lever_table(
    rows: list[dict[str, object]], text: dict, language: str
) -> str:
    lever_labels = WORKFORCE_LEVER_LABELS[language]
    headers = (
        f"<tr><th>{html.escape(text['col_lever'])}</th>"
        f"<th>{html.escape(text['col_target'])}</th>"
        f"<th>{html.escape(text['col_birth_mod'])}</th>"
        f"<th>SoL</th>"
        f"<th>{html.escape(text['col_years_to_40'])}</th>"
        f"<th>{html.escape(text['col_years_to_45'])}</th>"
        f"<th>{html.escape(text['col_ratio_at_50y'])}</th>"
        f"<th>{html.escape(text['col_ratio_at_100y'])}</th></tr>"
    )
    body = "\n".join(
        "<tr>"
        f"<td>{html.escape(lever_labels.get(str(r['label_key']), str(r['label_key'])))}</td>"
        f"<td>{pct(float(r['target_ratio']), 0)}</td>"
        f"<td>{pct(float(r['birth_mult']), 0)}</td>"
        f"<td>{float(r['sol']):.0f}</td>"
        f"<td>{_fmt_years(r['years_to_40pct'])}</td>"
        f"<td>{_fmt_years(r['years_to_45pct'])}</td>"
        f"<td>{pct(float(r['ratio_after_50y']), 1)}</td>"
        f"<td>{pct(float(r['ratio_after_100y']), 1)}</td>"
        "</tr>"
        for r in rows
    )
    return f"<table><thead>{headers}</thead><tbody>{body}</tbody></table>"


def _render_industrial_table(rows: list[dict[str, object]], text: dict) -> str:
    headers = (
        f"<tr><th>{html.escape(text['industry_col_pollution'])}</th>"
        f"<th>{html.escape(text['industry_col_no_health'])}</th>"
        f"<th>{html.escape(text['industry_col_public'])}</th>"
        f"<th>{html.escape(text['industry_col_uplift'])}</th></tr>"
    )
    body = "\n".join(
        "<tr>"
        f"<td>{int(float(r['pollution_impact']) * 100)}%</td>"
        f"<td>{float(r['no_health_pop_index']):.2f}×</td>"
        f"<td>{float(r['public_health_pop_index']):.2f}×</td>"
        f"<td>{float(r['public_health_uplift_pct']):+.1f}%</td>"
        "</tr>"
        for r in rows
    )
    return f"<table><thead>{headers}</thead><tbody>{body}</tbody></table>"


def _render_literacy_table(rows: list[dict[str, object]], text: dict) -> str:
    """Pivot to a grid: rows = SoL, columns = literacy levels."""
    sols = sorted({float(r["sol"]) for r in rows})
    literacy_levels = sorted({float(r["literacy"]) for r in rows})
    headers = "<tr><th>SoL</th>"
    for lit in literacy_levels:
        headers += f"<th>{int(lit * 100)}%</th>"
    headers += "</tr>"
    body_rows: list[str] = []
    for sol in sols:
        cells = [f"<td>{int(sol)}</td>"]
        for lit in literacy_levels:
            row = next(
                (r for r in rows if float(r["sol"]) == sol and float(r["literacy"]) == lit),
                None,
            )
            if row is None:
                cells.append("<td>—</td>")
            else:
                cells.append(f"<td>{pct(float(row['birth_annual']), 2)}<br><span style='color:#94a3b8;font-size:11px'>{pct(float(row['birth_delta_vs_zero']), 2)}</span></td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        f"<table><thead>{headers}</thead><tbody>{''.join(body_rows)}</tbody></table>"
        f"<p class='small'>{html.escape(text['literacy_grid_note'])}</p>"
    )


def _starvation_chart(
    partial_curve: list[dict[str, object]],
    severe_curve: list[dict[str, object]],
    text: dict,
    title: str,
) -> str:
    series = [
        (text["label_partial_starv"], [(float(r["year"]), float(r["population_index"])) for r in partial_curve]),
        (text["label_severe_starv"], [(float(r["year"]), float(r["population_index"])) for r in severe_curve]),
    ]
    return svg_line_chart(
        title,
        series,
        x_label=text["axis_years"],
        y_label=text["axis_pop_index"],
        y_as_percent=False,
        zero_baseline=False,
        palette="categorical",
    )


# One fixed color per health system, shared across both pollution levels.
# The 50% pollution variant is drawn dashed so the eye pairs solid/dashed as
# "same system, different pollution".
_HEALTH_SYSTEM_COLORS = {
    "no_health": "#475569",   # slate
    "charitable": "#0f766e",  # teal
    "public": "#2563eb",      # blue
    "private": "#b45309",     # amber-brown
}


def _healthcare_compare_chart(
    sols_dense: tuple[float, ...],
    constants: PopGrowthConstants,
    text: dict,
    language: str,
) -> str:
    """Plot net growth vs SoL for the four health systems at 0% and 50% pollution.

    Same color per system; solid line for 0% pollution, dashed for 50%.
    """
    from .experiments import _healthcare_scenarios
    from .model import adjusted_rates
    series: list[tuple[str, list[tuple[float, float]]]] = []
    colors: list[str | None] = []
    dashes: list[str | None] = []
    for pollution in (0.0, 0.5):
        scenarios = _healthcare_scenarios(constants, pollution=pollution)
        for key, scenario in scenarios.items():
            points = []
            for sol in sols_dense:
                rates = adjusted_rates(sol, scenario, constants)
                points.append((sol, rates["net_annual"]))
            suffix = " · 0%" if pollution == 0.0 else " · 50%"
            series.append((_system_label(key, language) + suffix, points))
            colors.append(_HEALTH_SYSTEM_COLORS.get(key))
            dashes.append("" if pollution == 0.0 else "6 4")
    return svg_line_chart(
        text["chart_health_compare"],
        series,
        x_label=text["axis_sol"],
        y_label=text["axis_net"],
        y_scale="symlog",
        integer_percent_y_ticks=True,
        zero_baseline=True,
        palette="categorical",
        series_colors=colors,
        series_dashes=dashes,
    )


def _food_chart(
    sols_dense: tuple[float, ...],
    constants: PopGrowthConstants,
    text: dict,
) -> str:
    from .model import adjusted_rates
    baseline_points = []
    food_points = []
    for sol in sols_dense:
        base = adjusted_rates(sol, Scenario("baseline"), constants)
        food = adjusted_rates(sol, Scenario("food", birth_mult=0.05), constants)
        baseline_points.append((sol, base["net_annual"]))
        food_points.append((sol, food["net_annual"]))
    return svg_line_chart(
        text["chart_food"],
        [
            (text["label_baseline"], baseline_points),
            (text["label_food_company"], food_points),
        ],
        x_label=text["axis_sol"],
        y_label=text["axis_net"],
        y_as_percent=True,
        zero_baseline=True,
        palette="categorical",
    )


def build_analysis_report(
    *,
    game_root: Path,
    constants: PopGrowthConstants,
    rates_rows: list[dict[str, object]],
    projection_rows: list[dict[str, object]],
    growth_sensitivity_rows: list[dict[str, object]],
    sensitivity_rows: list[dict[str, object]],
    source_summary: list[dict[str, str | float | int]],
    projection_initial_ratio: float,
    projection_target_ratio: float,
    projection_sol: float,
    language: str,
    scenarios: list[Scenario] | None = None,
    pollution_examples: list[dict[str, object]] | None = None,
) -> str:
    """Build the analysis-article HTML.

    Prose + a small set of argument-critical charts and tables. The full set
    of raw data tables (scenario definitions, modifier scan, pollution
    steady-state, data dictionary) and the systematic figure set live in the
    companion file produced by ``build_html_report``.
    """
    text = ANALYSIS_TEXT[language]

    # ---- Healthcare metrics ----
    hc_rows = healthcare_comparison_table(
        constants, sols=(10.0, 12.0, 15.0, 18.0, 20.0, 22.0),
        pollution_levels=(0.0, 0.5),
    )
    breakeven_sol = private_vs_public_breakeven_sol(constants)
    public_50_sol20 = next(
        r for r in hc_rows
        if r["system_key"] == "public" and r["sol"] == 20.0 and r["pollution_impact"] == 0.5
    )
    private_50_sol20 = next(
        r for r in hc_rows
        if r["system_key"] == "private" and r["sol"] == 20.0 and r["pollution_impact"] == 0.5
    )
    health_chart = _healthcare_compare_chart(tuple(range(5, 26)), constants, text, language)

    # ---- Food company metrics ----
    food_rows = food_company_comparison(
        constants, sols=(5.0, 10.0, 12.0, 15.0, 18.0, 22.0), years=100,
    )
    food_chart = _food_chart(tuple(range(5, 26)), constants, text)
    food_row_15 = next(r for r in food_rows if r["sol"] == 15.0)
    food_row_10 = next(r for r in food_rows if r["sol"] == 10.0)
    food_row_5 = next(r for r in food_rows if r["sol"] == 5.0)

    # ---- Workforce ratio levers ----
    lever_rows = workforce_ratio_lever_table(constants, initial_ratio=0.25, sol_baseline=12.0)
    lever_table_html = _render_lever_table(lever_rows, text, language)
    # The "suffrage + unions" row at SoL 12 and the "high_sol" row at SoL 15
    # carry the same target / birth mod, so they isolate the SoL-12 vs SoL-15
    # speed difference cleanly.
    sol12_row = next(r for r in lever_rows if r["label_key"] == "suffrage_unions")
    sol15_row = next(r for r in lever_rows if r["label_key"] == "high_sol")
    years_sol12 = _fmt_years(sol12_row["years_to_40pct"])
    years_sol15 = _fmt_years(sol15_row["years_to_40pct"])
    birth_sol12_annual = base_birth_rate(12.0, constants) * 12.0
    birth_sol15_annual = base_birth_rate(15.0, constants) * 12.0

    # ---- Industrial cost ----
    industrial_rows = industrial_vs_agrarian_table(
        constants, sol=14.0, years=80,
        pollution_levels=(0.0, 0.25, 0.5, 0.75, 1.0),
    )
    industrial_table_html = _render_industrial_table(industrial_rows, text)
    poll_0 = next(r for r in industrial_rows if r["pollution_impact"] == 0.0)
    poll_50 = next(r for r in industrial_rows if r["pollution_impact"] == 0.5)
    loss_50_pct = (1.0 - float(poll_50["no_health_pop_index"]) / float(poll_0["no_health_pop_index"])) * 100

    # ---- Starvation ----
    starv_sol = 8.0
    starv_partial = starvation_summary(constants, sol=starv_sol, starvation_years=5, severity="partial")
    starv_severe = starvation_summary(constants, sol=starv_sol, starvation_years=5, severity="severe")
    starv_partial_curve = starvation_recovery_curve(
        constants, sol=starv_sol, starvation_years=5, recovery_years=30, severity="partial",
    )
    starv_severe_curve = starvation_recovery_curve(
        constants, sol=starv_sol, starvation_years=5, recovery_years=30, severity="severe",
    )
    starvation_chart = _starvation_chart(
        starv_partial_curve, starv_severe_curve, text, text["chart_starvation"],
    )

    # ---- Literacy ----
    lit_rows = literacy_birth_rate_table(
        constants, sols=(12.0, 15.0), literacy_levels=(0.0, 1.0),
    )
    lit_12_0 = next(r for r in lit_rows if r["sol"] == 12.0 and r["literacy"] == 0.0)
    lit_12_1 = next(r for r in lit_rows if r["sol"] == 12.0 and r["literacy"] == 1.0)
    lit_15_0 = next(r for r in lit_rows if r["sol"] == 15.0 and r["literacy"] == 0.0)
    lit_15_1 = next(r for r in lit_rows if r["sol"] == 15.0 and r["literacy"] == 1.0)

    # ---- Prose interpolation ----
    health_body_p1 = text["health_body_p1"].format(breakeven_sol=f"{breakeven_sol:.1f}")
    health_body_p2 = text["health_body_p2"].format(
        public_mort_50_sol20=pct(float(public_50_sol20["mortality_annual"]), 2),
        private_mort_50_sol20=pct(float(private_50_sol20["mortality_annual"]), 2),
    )
    food_body_p1 = text["food_body_p1"].format(
        delta_15=pct(float(food_row_15["net_growth_delta"]), 2),
        mult_15=f"{float(food_row_15['population_multiplier_after_years']):.2f}×",
        mult_10=f"{float(food_row_10['population_multiplier_after_years']):.2f}×",
        mult_5=f"{float(food_row_5['population_multiplier_after_years']):.2f}×",
    )
    ratio_body_p3 = text["ratio_body_p3"].format(
        years_sol12=years_sol12,
        years_sol15=years_sol15,
        birth_sol12=pct(birth_sol12_annual, 2),
        birth_sol15=pct(birth_sol15_annual, 2),
    )
    industry_body_p2 = text["industry_body_p2"].format(
        loss_50=f"{loss_50_pct:.1f}",
        uplift_50=f"{float(poll_50['public_health_uplift_pct']):.1f}%",
    )
    famine_body_p1 = text["famine_body_p1"].format(
        partial_loss=f"{float(starv_partial['pop_loss_pct']):.1f}",
        partial_recover=_fmt_years(starv_partial["years_to_recover"], fallback=">30"),
        severe_loss=f"{float(starv_severe['pop_loss_pct']):.1f}",
        severe_recover=_fmt_years(starv_severe["years_to_recover"], fallback=">30"),
    )
    literacy_body_p1 = text["literacy_body_p1"].format(
        birth_12_lit0=pct(float(lit_12_0["birth_annual"]), 2),
        birth_12_lit1=pct(float(lit_12_1["birth_annual"]), 2),
        drop_12=f"{(float(lit_12_0['birth_annual']) - float(lit_12_1['birth_annual'])) * 100:.2f}",
        birth_15_lit0=pct(float(lit_15_0["birth_annual"]), 2),
        birth_15_lit1=pct(float(lit_15_1["birth_annual"]), 2),
        drop_15=f"{(float(lit_15_0['birth_annual']) - float(lit_15_1['birth_annual'])) * 100:.2f}",
    )

    source_line = text["source_line"].format(game_root=html.escape(str(game_root)))

    return f"""<!doctype html>
<html lang="{text['html_lang']}">
<head>
<meta charset="utf-8">
<title>{html.escape(text['title'])}</title>
<style>
{ANALYSIS_CSS}
</style>
</head>
<body>
<main>
<h1>{html.escape(text['title'])}</h1>
<p class="small">{source_line}</p>

<h2>{html.escape(text['intro_title'])}</h2>
<p>{text['intro_body']}</p>

<h2>{html.escape(text['health_title'])}</h2>
<p>{health_body_p1}</p>
<p>{health_body_p2}</p>
<p>{text['health_body_p3']}</p>
{health_chart}

<h2>{html.escape(text['food_title'])}</h2>
<p>{food_body_p1}</p>
{food_chart}

<h2>{html.escape(text['ratio_title'])}</h2>
<p>{text['ratio_body_p1']}</p>
<p>{text['ratio_body_p2']}</p>
<p>{ratio_body_p3}</p>
{lever_table_html}
<p>{text['ratio_body_p4']}</p>

<h2>{html.escape(text['industry_title'])}</h2>
<p>{text['industry_body_p1']}</p>
{industrial_table_html}
<p>{industry_body_p2}</p>

<h2>{html.escape(text['famine_title'])}</h2>
<p>{famine_body_p1}</p>
{starvation_chart}
<p>{text['famine_body_p2']}</p>

<h2>{html.escape(text['literacy_title'])}</h2>
<p>{literacy_body_p1}</p>
<p>{text['literacy_body_p2']}</p>

<h2>{html.escape(text['figures_pointer_title'])}</h2>
<p>{text['figures_pointer_body']}</p>

<h2>{html.escape(text['limits_title'])}</h2>
{text['limits_body']}
</main>
</body>
</html>
"""


def build_analysis_report_zh(**kwargs) -> str:
    """Backward-compatible wrapper. Prefer ``build_analysis_report(language='zh')``."""
    return build_analysis_report(language="zh", **kwargs)
