# V3_EMA — Implementation Details & Design Notes

[中文](method.md) | **English**

This document records V3_EMA's internal architecture, data flow, output schema, and cross-version diff implementation. Targets developers who plan to extend or integrate the tool; regular users only need [README](../README.en.md).

For metric definitions, simplifying axioms, and unbiasedness discussion, see [economics.en.md](economics.en.md).

---

## 1. Pipeline

```
launcher-settings.json ────┐
common/{goods,pop_types,                   ┌── Overview sheet
  production_methods,                       │
  production_method_groups,                 ├── Agriculture / Plantations / Extraction / ...
  buildings,                                │     (bucketed by building_group root)
  building_groups,                          │
  script_values}                            ├── Construction Sectors sheet
   ↓ PDX parser (parser/pdx_parser)         │     (cost / construction, inverted color scale)
   ↓ Localization yml (parser/yml_loc)      │
GameData (model.py)              ──────────►├── Info sheet (game_version, counts, ui_lang)
   ↓                                        │
build_rows / build_construction_rows        ↓
(analysis/rows.py, analysis/construction.py)   v3_ema_report.xlsx

Old report ┐
            ├── read_report → diff_snapshots ─► Info / Added / Removed / Changed sheets
New report ┘                                   v3_ema_diff.xlsx
```

## 2. Module Structure

```
v3_ema/
├── parser/
│   ├── pdx_tokenizer.py      # PDX lexer (handles ?= != hsv{} etc.)
│   ├── pdx_parser.py         # Recursive-descent parser + directory bulk loader
│   └── yml_loc.py            # Localization yml parser + recursive $ref$ resolution
├── i18n.py                   # zh / en UI string table; canonical-key reverse map for diff
├── model.py                  # dataclasses: Good / PopType / PM / PMG / Building / GameData
├── loader.py                 # parser → model, single entry point; reads game version
├── analysis/
│   ├── metrics.py            # Pure-function metrics (gross/net/roi/per_capita, ×52)
│   ├── rows.py               # Cartesian product of building × PMGs into combination rows
│   ├── construction.py       # Special analysis for construction sectors
│   └── diff.py               # Read previously-generated xlsx + compute diff
├── output/
│   ├── csv_writer.py         # UTF-8 BOM csv
│   ├── xlsx_writer.py        # Multi-sheet xlsx + modern styling + Info sheet
│   └── diff_writer.py        # Diff xlsx output
├── util/
│   ├── logging.py
│   └── strings.py            # BG_BUCKET (canonical bucket ids), PMG-category derivation, pm_notes formatting
├── cli.py                    # argparse command dispatch
└── __main__.py               # Supports `python -m v3_ema`
```

## 3. Output Schema

### v3_ema_report.xlsx

| Sheet | Contents |
|---|---|
| Info | Game version, raw version, tool version, generated timestamp, data lang, UI lang, object counts |
| Overview | All combination rows (building × Base × Secondary × Automation PMs) |
| Agriculture / Plantations / Extraction / Manufacturing / Service / Infrastructure / Government / Military / Monuments | Bucketed by building-group parent-chain root (`bg_extraction` / `bg_manufacturing` / …); sorted by profit descending |
| Construction Sectors | Construction sector PMs' "Construction/Level, Material Cost/Level, Wage Cost/Level, Cost/Construction-Unit" comparison |

Each row's fields (22 columns):

```
Building | Base PM | Secondary PM | Automation PM | Default Ownership
| Output Value | Input Value | Profit | Construction | Employment | Wage Multiplier | Construction ROI | Annual Per-Capita Profit
| Building Group | Inputs | Outputs | Notes
| Building ID | Base_ID | Secondary_ID | Automation_ID | Ownership_ID
```

### v3_ema_diff.xlsx

| Sheet | Contents |
|---|---|
| Info | Both game versions, both generation times, comparison time, six categories of counts |
| Added-Combo / Removed-Combo | (Building × combination) rows present only in new / old report |
| Changed-Combo | Rows present in both with values changed beyond ε; each changed field shown as `Old / New / Δ` triple, Δ column conditionally formatted (positive=green, negative=red) |
| Added-Construction / Removed-Construction / Changed-Construction | Same, but for the Construction Sectors sheet |

## 4. Reproducibility

Every generated xlsx records, in both the Info sheet and workbook properties:

- Game version (from `launcher-settings.json`'s `version` field, e.g. `1.13.4 (Matcha)`)
- Raw version (`rawVersion` field)
- Tool version (`v3_ema.__version__`)
- Generation timestamp (ISO-8601, local time)
- Data language (which `localization/<lang>` was used)
- UI language (`zh` or `en`)
- Object counts (goods/pops/PMs/PMGs/buildings/combo rows/construction rows)

Any V3_EMA xlsx output uniquely identifies a (game_version, tool_version, data_lang, ui_lang) tuple. The `diff` command reads both reports' Info sheets and surfaces this tuple comparison in the diff workbook.

## 5. Multi-Language Support

The tool supports all 11 V3 in-game localizations via `--lang`: `simp_chinese`, `english`, `french`, `german`, `japanese`, `korean`, `polish`, `russian`, `spanish`, `turkish`, `braz_por`. The tool's UI (sheet names, column headers, bucket labels, modifier-note labels) auto-switches:

- `simp_chinese` → zh UI
- everything else → en UI
- `--ui-lang zh|en` overrides the auto inference

### Cross-language diff

Diff is fully language-agnostic. When `read_report` parses a workbook, it maps each header label (in any supported language) back to the canonical column key via `i18n.label_to_key`. Internal data is keyed by these canonical names, so comparing a `simp_chinese`-UI report against an `english`-UI report still produces a clean diff.

The diff output workbook itself is rendered in the diff command's chosen `--ui-lang`.

## 6. Cross-Version Diff Implementation

```bash
python -m v3_ema diff <old.xlsx> <new.xlsx> [--out diff.xlsx] [--ui-lang zh|en|auto] [--eps-abs 0.01] [--eps-rel 0.005]
```

### 6.1 Key Definition

- Combo rows: `(building_id, base_ids, secondary_ids, automation_ids)` 4-tuple
- Construction rows: `(building_id, pm_id)` 2-tuple

### 6.2 Compared Fields

- Combo: `output_value, input_value, net_value, construction, employment, wage_mult, roi, per_capita`
- Construction: `construction_per_lvl, employment, wage_mult, material_cost_per_lvl, wage_cost_per_lvl, material_cost_per_unit, wage_cost_per_unit, total_cost_per_unit`

### 6.3 ε Threshold

```
Change triggered if  abs(old - new) > max(eps_abs, eps_rel × max(|old|, |new|))
```

Defaults: `eps_abs=0.01, eps_rel=0.005`. This avoids floating-point round-trip jitter (xlsx save/load can introduce ~1e-15 noise) being reported as real changes.

### 6.4 Three-Way Bucketing

Each sheet's diff is split into:
- **added** (only in new) → "Added-" sheet
- **removed** (only in old) → "Removed-" sheet
- **changed** (in both, value changed) → "Changed-" sheet, only displaying fields that **actually have changes**, avoiding column-width explosion

## 7. Limitations

The tool runs under simplifying axioms A1–A4 — see [economics.en.md §7](economics.en.md):

- A1: All goods valued at base `cost`, no dynamic market simulation
- A2: Building at level 1, 100% staffed
- A3: No law / tech / company modifiers; no throughput modifier chain modeling
- A4: Static cross-section, no week-by-week evolution

So this tool is suitable for **structural comparison and ranking** (which PM combination is better, which buildings were modified) — not for direct national finance forecasting.

## 8. Future Extensions

- **Dynamic prices**: Read live market prices from saves to override `cost`
- **Save-game integration**: `.v3` binary parser for analyzing a specific country's actual economic structure
- **Law / tech layering**: Model throughput / production_efficiency modifier chains
- **Mod compatibility**: Detect mod paths and merge overrides
- **Regression baseline suite**: Maintain a set of "gold standard" xlsx files; run diff in CI to auto-flag unexpected changes

## 9. Testing

`tests/test_diff.py` includes 4 cases (added / removed / value-changed + ε boundary + cross-language round-trip), runnable as either pytest or a plain script:

```powershell
python tests\test_diff.py
```

The tests build small xlsx fixtures programmatically (using `xlsx_writer` to emit minimal datasets, then mutating one), validating `diff_snapshots` produces the right three-way buckets.

## 10. Data Source Summary

| Content | File |
|---|---|
| Game version | `launcher/launcher-settings.json` |
| Goods prices / pop wages | `common/{goods,pop_types}/*.txt` |
| PMs / PMGs / buildings | `common/{production_methods,production_method_groups,buildings}/*.txt` |
| Building-group parent chain | `common/building_groups/00_building_groups.txt` |
| Construction tiers | `common/script_values/building_values.txt` |
| Localization | `localization/{lang}/*.yml` |
