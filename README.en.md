# EMA — Victoria 3 Econometrics Automation

[中文](README.md) | **English**

Econometrics Automation, the EMA tool, is a fully automated pipeline for V3 econometric research. It does not modify game content in any way; on the contrary, it extracts data from local files and produces structured Excel reports.

### Why this tool?

Victoria 3's economic decision space spans ~440 production methods (PMs), ~200 production method groups (PMGs), and ~110 buildings, yielding 1500+ theoretical combinations. Any analysis based on hand-copied tables goes stale after every patch — you never know what Paradox quietly tweaked (or maybe they wrote it down somewhere, but you've been away from V3 for a while). This causes pain for maintainers and forces players to wrestle with outdated guides.

EMA solves this with end-to-end V3 economic analysis:

- One command: export an Excel sheet with all 1500+ combinations for the **current version**
- One command: diff **two reports** to see exactly which buildings and which fields changed
- The report auto-embeds the game version (e.g. `1.13.4 (Matcha)`) for easy archival



## Installation

### Step 1: Unzip anywhere

Put the `V3_EMA` folder wherever you like (**no longer required to be inside the game folder** — that risked Steam's "verify integrity" wiping it). Typical locations: `D:\tools\V3_EMA\` or `C:\Users\you\Documents\V3_EMA\`.

### Step 2: Install Python and dependencies

Requires Python ≥ 3.10. Open PowerShell in the V3_EMA folder:

```powershell
python -m pip install openpyxl
```

Just one dependency (`openpyxl`, for writing Excel).

### Step 3: First run — locating the game

The tool auto-resolves the V3 install in this order:

1. CLI flag `--game-root <path>` (one-shot override)
2. Environment variable `V3_GAME_ROOT`
3. Cache file `<V3_EMA>/.game_root`
4. **Steam library scan** (Windows registry + `libraryfolders.vdf`) — **handles most users**
5. If V3_EMA happens to live inside the game directory, walk up to find it

Most users need no configuration. If detection fails, pick any of:

```powershell
python -m v3_ema config --game-root "D:\Games\Victoria 3"   # persisted
python -m v3_ema report --game-root "D:\Games\Victoria 3"    # one-shot
$env:V3_GAME_ROOT = "D:\Games\Victoria 3"; python -m v3_ema report  # env var
```

Helpers:

```powershell
python -m v3_ema config --show     # show cached path + currently resolved path
python -m v3_ema config --clear    # clear cache; next run re-detects
```



## Usage

### Feature 1: Buildings Profit Report

```powershell
# Generate for the current version (Chinese UI by default)
python -m v3_ema report

# Cross-version comparison — a 1.13.4 baseline ships with the project, use it directly
python -m v3_ema report --out current.xlsx
python -m v3_ema diff baseline_buildings_v1.13.4.xlsx current.xlsx

# Switch language (all 11 V3 localizations)
python -m v3_ema report --lang english   --out v3_ema_report_en.xlsx
python -m v3_ema report --lang french    --out v3_ema_report_fr.xlsx
python -m v3_ema report --lang german    --out v3_ema_report_gm.xlsx
python -m v3_ema report --lang japanese  --out v3_ema_report_jp.xlsx
python -m v3_ema report --lang korean    --out v3_ema_report_kr.xlsx
python -m v3_ema report --lang polish    --out v3_ema_report_po.xlsx
python -m v3_ema report --lang russian   --out v3_ema_report_ru.xlsx
python -m v3_ema report --lang spanish   --out v3_ema_report_sp.xlsx
python -m v3_ema report --lang turkish   --out v3_ema_report_tu.xlsx
python -m v3_ema report --lang braz_por  --out v3_ema_report_bp.xlsx
```

Output location: `V3_EMA\out\buildings\{reports,diffs}\`.

The report has 12 sheets: Info / Overview / Agriculture / Plantations / Extraction / Manufacturing / Service / Infrastructure / Government / Military / Monuments / Construction Sectors. Each row's core fields: Building / Base-Secondary-Automation PM / Output Value / Input Value / Profit / Construction / Employment / Wage Multiplier / Construction ROI / Annual Per-Capita Profit. The diff workbook has 6 sheets (Added-Combo / Removed-Combo / Changed-Combo and the construction-sector counterparts); changed metric columns appear as `Old / New / Δ` triples with auto green/red coloring on Δ.

### Feature 2: State-Region Resource Statistics

```powershell
# Generate for the current version (Chinese UI by default)
python -m v3_ema regions report

# Cross-version comparison — a 1.13.4 baseline ships with the project, use it directly
python -m v3_ema regions report --out current.xlsx
python -m v3_ema regions diff baseline_regions_v1.13.4.xlsx current.xlsx

# Switch language
python -m v3_ema regions report --lang english   --out regions_en.xlsx
python -m v3_ema regions report --lang french    --out regions_fr.xlsx
python -m v3_ema regions report --lang german    --out regions_gm.xlsx
python -m v3_ema regions report --lang japanese  --out regions_jp.xlsx
python -m v3_ema regions report --lang korean    --out regions_kr.xlsx
python -m v3_ema regions report --lang polish    --out regions_po.xlsx
python -m v3_ema regions report --lang russian   --out regions_ru.xlsx
python -m v3_ema regions report --lang spanish   --out regions_sp.xlsx
python -m v3_ema regions report --lang turkish   --out regions_tu.xlsx
python -m v3_ema regions report --lang braz_por  --out regions_bp.xlsx
```

Output location: `V3_EMA\out\regions\{reports,diffs}\`.

The report buckets states into 14 continent groups (Western Europe / Southern Europe / Northern Europe / Eastern Europe / North America / Central America / South America / Africa / Middle East / Central Asia / India / East Asia / Southeast Asia / Oceania). **Row 2 is a totals row** (sum of all states' resources within the bucket). Each row's core fields: State / Strategic Region / Arable Land / Arable Buildings / Capped Total / **per-resource columns** (Iron Mine / Coal Mine / Logging Camp / Oil Rig / etc., easy to sort & compare) / Total Capacity / State Traits.

### Feature 3: Pop-Growth & Workforce-Ratio Analysis

```powershell
# Bilingual HTML reports + CSV raw data (default)
python -m v3_ema demography report

# English only
python -m v3_ema demography report --ui-lang en
# Chinese only
python -m v3_ema demography report --ui-lang zh

# Custom projection (default: 100 years, SoL 15, 25% → 50% workforce ratio)
python -m v3_ema demography report --months 600 --projection-sol 12 \
    --initial-workforce-ratio 0.20 --projection-target 0.45

# Linear SoL trajectory from 8 to 14 across the projection window
python -m v3_ema demography report --sol-start 8 --sol-end 14

# Skip the slow scan of game/common (faster, but the modifier-source CSV and
# the modifier-frequency bar chart in the HTML are then empty)
python -m v3_ema demography report --skip-modifier-scan

# Disable the WORKING_ADULT_RATIO_SKEW_MAXIMUM correction (legacy uniform model)
python -m v3_ema demography report --no-skew
```

Output location: `V3_EMA\out\demography\`.

Per run (default `--ui-lang both`):

- `demography_report_{en,zh}.html` — compact chart + data report
- `demography_analysis_report_{en,zh}.html` — academic-style analysis report (base curves, sensitivities, controlled healthcare comparison, quantitative limitations)
- `rates_by_sol.csv` — birth / mortality / net growth by SoL × scenario
- `net_growth_sensitivity.csv` — one-factor-at-a-time net-growth sensitivities
- `workforce_projection.csv` — 100-year workforce-ratio and population trajectories per scenario
- `workforce_sensitivity.csv` — same projection isolated per factor
- `modifier_sources.csv` / `modifier_source_summary.csv` — scan of every relevant modifier hit in `game/common`
- `pollution_impact_examples.csv` — steady-state pollution generation → impact reference
- `pollution_dynamics.csv` — monthly transient pollution build-up

The report is driven by the population curves in `defines/00_defines.txt`, the health-system laws in `laws/00_health_system.txt`, the women's-rights laws in `laws/00_rights_of_women.txt`, and the literacy / starvation static modifiers in `static_modifiers/00_code_static_modifiers.txt`. Law / health / starvation values are parsed live from `game/common` by default (`--scenarios-from game`), so any stale hardcoded value would be overridden; pass `--scenarios-from hardcoded` to use the constants frozen in `v3_ema/demography/scenarios.py`.

### Utility Commands

```powershell
python -m v3_ema verify                       # self-check (parses current game data correctly)
python -m v3_ema dump-pm pm_simple_farming    # debug a single PM's parsed result
python tests\test_diff.py                     # run tests (expect 6 PASS lines)
```

Common args: `--game-root <path>` overrides the game root; `--ui-lang zh|en` forces a UI language (default: inferred from `--lang` — `simp_chinese` → Chinese UI, everything else → English).

---

## Further Documentation

- **V3 economic mechanics + the tool's simplifying assumptions**: [docs/economics.en.md](docs/economics.en.md)
- **Architecture, modules, output schema, diff implementation details**: [docs/method.en.md](docs/method.en.md)



## Data Sources

| Content              | File                                                         |
| -------------------- | ------------------------------------------------------------ |
| Game version         | `launcher/launcher-settings.json`                            |
| Goods prices / pop wages | `common/{goods,pop_types}/*.txt`                         |
| PMs / PMGs / buildings | `common/{production_methods,production_method_groups,buildings}/*.txt` |
| Building-group parent chain | `common/building_groups/00_building_groups.txt`       |
| Construction tiers   | `common/script_values/building_values.txt`                   |
| Localizations        | `localization/{lang}/*.yml`                                  |
