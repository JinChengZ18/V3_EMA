# `v3_eat.demography` — package internals

End-user docs (CLI usage, output layout, examples) live in the project root
[README.md](../../README.md) → 「功能 3：人口与劳动力比例分析」 /
[README.en.md](../../README.en.md) → 「Feature 3: Pop-Growth & Workforce-Ratio Analysis」.

This file documents the package layout for contributors.

## Run

```powershell
python -m v3_eat demography report
```

The legacy direct entry point `demography_analysis/analyze_demography.py`
was retired when the subproject was integrated into `v3_eat`. The subcommand
above is the only supported invocation.

## Module layout

| File | Responsibility |
| --- | --- |
| `constants.py` | `PopGrowthConstants` parser for `defines/00_defines.txt`. |
| `model.py` | `Scenario`, `base_birth_rate`, `base_mortality`, `adjusted_rates`, `project_workforce_ratio` (with `WORKING_ADULT_RATIO_SKEW_MAXIMUM` correction and optional `sol_trajectory`), `pollution_impact_from_generation`, `simulate_pollution`, `sol_to_wealth`. |
| `scenarios.py` | Hardcoded default + sensitivity scenarios. Acts as a fallback when game files cannot be read. |
| `modifier_scan.py` | Flat audit scan over `game/common/*.txt` for `state_*_mult` / `state_*_add` keys (powers `modifier_sources.csv`). |
| `modifier_lookup.py` | Structured named-block extractor built on `v3_eat.parser.pdx_parser`; reads e.g. `law_public_health_insurance` and returns its numeric assignments. |
| `game_modifiers.py` | Glue that assembles scenarios from live game files via `modifier_lookup`. Used by the CLI when `--scenarios-from=game` (default). Falls back to `scenarios.py` per scenario when a block is missing. |
| `i18n.py` | Local `LABEL_TRANSLATIONS_ZH`, `NOTE_TRANSLATIONS_ZH`, `REPORT_TEXT`, `ANALYSIS_TEXT`, `SENSITIVITY_GROUPS`, `SENSITIVITY_NOTES`. Keyed by `"en"` / `"zh"` so callers can pass `v3_eat.i18n.ui_lang_for(args.lang)` directly. |
| `chart_svg.py` | `svg_line_chart`, `svg_bar_chart`, palettes. Series styling is decoupled from translated labels via the explicit `style_keys=` parameter (`STYLE_BASE` / `STYLE_BIRTH` / `STYLE_MORTALITY` / `STYLE_NATURAL_GROWTH`). |
| `rows.py` | CSV row builders (`make_rates_rows`, `make_projection_rows`, `make_workforce_sensitivity_rows`, …) + a dict-row `write_csv` with float rounding to 6 decimals (configurable via `float_digits=`). |
| `report.py` | HTML report template. `build_analysis_report(language=…)` is the single merged report (all charts + analysis prose inline). `workforce_chart_bounds(initial, target)` derives chart y-axis bounds from the projection inputs. |

## Tests

```powershell
python tests\test_demography.py        # no pytest required
# or
pytest tests\test_demography.py
```

Covers piecewise curve endpoints / continuity, pollution clamping & transient
convergence, projection invariants (population conservation at equilibrium,
ratio fixed-point when initial==target), skew vs no-skew, dynamic SoL,
wealth mapping, modifier-lookup extraction, and a drift-guard that asserts
the hardcoded scenarios in `scenarios.py` still match what `modifier_lookup`
parses from a representative fixture (`Public health`, `Charitable health`,
`starvation_penalty`, `severe_starvation_penalty`).

## Model notes

- Base birth and mortality curves come from `defines/00_defines.txt`.
- Pollution health effects use `state_region_pollution_health`:
  `state_mortality_mult = 0.5` and `state_standard_of_living_add = -3`,
  both scaled by `pollution_impact` and by
  `(1 + state_pollution_reduction_health_mult)`.
- Literacy uses the code static modifier `literacy_penalty`:
  `state_birth_rate_mult = -0.1`, scaled by pop literacy.
- Workforce-ratio projection includes an explicit
  `WORKING_ADULT_RATIO_SKEW_MAXIMUM` skew correction
  (`skew = clamp(target / current, 1/SKEW_MAX, SKEW_MAX)`). The exact engine
  algorithm is not exposed in script files — pass `--no-skew` to fall back
  to the legacy uniform model.
- `Scenario.wealth_from_sol=True` runs SoL through
  `sol_to_wealth(SoL) = 1.5 * SoL` (see `model.WEALTH_FROM_SOL_SLOPE`).
- Pollution transient dynamics use
  `impact += (target - impact) * change_speed / pollution_max` per month.
