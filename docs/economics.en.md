# V3 Economic Mechanics and Computational Assumptions

[中文](economics.md) | **English**

This document targets researchers using V3_EMA for economic analysis. It briefly describes Victoria 3's economic mechanics and clarifies the simplifying assumptions V3_EMA makes in its calculations. All metric definitions in this doc are authoritative; the concrete implementation lives in `v3_ema/analysis/`.

## 1. Time Scale (Tick Model)

The V3 engine settles economics at the granularity of one **week** per tick; one year = 52 ticks. All economic flows (inputs, outputs, wages, profits) are denominated in **per-week** units by default.

In V3_EMA reports:
- "Output Value" / "Input Value" / "Profit" are **weekly** values (matching the in-game tooltip).
- "Annual Per-Capita Profit" is **annualized**: `profit × 52 / employment`, aligning with the in-game tooltip's "per capita output" wording.
- "Construction ROI" = `profit / construction_cost`, with units of "weekly profit per construction unit", an invariant suitable for cross-building cost-efficiency comparisons.

## 2. Building Hierarchy and Production-Method Slots

```
buildings (114)
  └── production_method_groups (197)
        └── production_methods (436)
```

Each building binds multiple PMGs (production method groups). At any moment each PMG **selects exactly one PM**. So a building's actual economic configuration is the joint state across all its PMGs — one specific point in the Cartesian product `∏_{pmg} |PMs(pmg)|`.

V3_EMA explicitly enumerates this space (~1528 combination rows after dropping "ownership" PMGs and informationless rows), answering: "How does this building perform under this specific configuration?"

PMG role is inferred from the name prefix:
- `pmg_base_*` → Base (one per building)
- `pmg_secondary_*`, `pmg_canning`, `pmg_distillery`, etc. → Secondary (may be multiple)
- `pmg_automation_*`, `pmg_harvesting_process_*`, `pmg_train_automation_*` → Automation (may be multiple)
- `pmg_ownership_*`, `pmg_serfdom` → Ownership (**not part of the combination axis**; the first PM's contribution is added as default to every combination row, since these primarily set who is employed)

## 3. Modifier Scaling

PM files declare effects under `building_modifiers` using three scaling kinds:

| Scaling | Meaning | Example |
|---|---|---|
| `workforce_scaled` | Linear in active workforce | `goods_output_grain_add = 20`: a fully-staffed level-1 building outputs 20 grain/week |
| `level_scaled` | Linear in building level | `building_employment_laborers_add = 4000`: 4000 laborers per level |
| `unscaled` | Independent of level | `building_laborers_mortality_mult = 0.3` |

V3_EMA assumes a building at **level 1, fully staffed** — under this assumption the workforce_scaled values represent the actual per-level contribution.

## 4. Goods Pricing

Each good has a base `cost` defined in `common/goods/00_goods.txt`. The in-game runtime price = `cost × supply-demand multiplier`, with the multiplier floating in [0.25, 1.75] based on regional/national supply-demand imbalance.

**A1 (simplifying axiom)**: V3_EMA always uses `cost`; it does not simulate dynamic markets. Consequence:
- For "**comparing two buildings' relative merit**" the report is unbiased (rank ordering preserved), assuming both face similar market conditions
- For "**absolute profit numbers**" there is bias — in-game, an oversupplied good's price drops, shrinking actual output value

## 5. Wage Formation

V3 wage logic: a building's cash flow (output value − input cost) is distributed across its pop types proportionally to their `wage_weight`. Each pop type has a static `wage_weight` defined in `common/pop_types/*.txt`:

| Pop | weight | Pop | weight |
|---|---|---|---|
| slaves | 0 | shopkeepers / clergymen / engineers | 3 |
| peasants | 0.2 | bureaucrats / academics | 4 |
| laborers / soldiers | 1 | aristocrats / capitalists / officers | 5 |
| machinists / clerks | 1.5 | farmers | 2 |

V3_EMA's "Wage Multiplier" column is defined as the employment-weighted average:

```
wage_mult = Σ(employment_i × wage_weight_i) / Σ employment_i
```

This is a linear proxy for "**wage sensitivity per unit of labor**" — higher values mean the PM choice carries a higher wage-cost share.

## 6. Construction Sector

`building_construction_sector` is special: its output isn't a good but a country-level **construction capacity** (`country_construction_add`). Construction goes into a national pool consumed by all projects (including new buildings) per their `required_construction`.

V3_EMA dedicates a separate "Construction Sectors" sheet with these columns:

```
Material Cost / Construction = Σ(input qty × goods.cost) / construction_per_lvl
Wage Cost / Construction      = Σ(employment × wage_weight) / construction_per_lvl
Total Cost / Construction     = sum of the two above
```

"Lower is better", so this sheet uses an inverted color scale (green for low, red for high).

## 7. Simplifying Axioms

| ID | Axiom | Impact |
|---|---|---|
| **A1** | All goods valued at base `cost` | Absolute profit biased; relative ordering unbiased |
| **A2** | Building at level 1, 100% staffed | Ignores hiring ramp, proportionality discount |
| **A3** | No law / tech / company modifiers | Ignores throughput / production_efficiency modifier chains |
| **A4** | Static cross-section, no week-by-week evolution | Ignores price feedback, population flow, corporate cash accumulation |

## 8. Metric Validity (Discussion)

| Metric | Under A1–A4 |
|---|---|
| **Output / input quantities** | Exact (read directly from PM fields) |
| **Employment count** | Exact (level_scaled fields) |
| **Construction (required_construction)** | Exact (lookup against script_value) |
| **Wage Multiplier** | Exact (pop_type static fields) |
| **Absolute Profit** | **Biased**: A1's effect; use for "directional" analysis, not financial forecasting |
| **Construction ROI** | **Rank-ordering unbiased**: A1's error acts uniformly across buildings |
| **Annual Per-Capita Profit** | Rank-ordering unbiased; absolute value underestimates positive returns |

## 9. Cross-Version Regression

Under A1–A4, V3_EMA's `diff` command performs a strict **structural diff**: it identifies (building × combination) units that newly appeared / were removed, and within units that exist in both reports, fields whose values changed beyond ε. This is **not** an economic simulation in the price-change sense, but a **mod/patch-level script-change detector** suitable for:

- Locating buildings/PMs modified after a game update
- Mod development regression testing
- Comparing economic parameters across mods

## References

- `common/production_methods/*` — PM definitions
- `common/production_method_groups/*` — PMG lists
- `common/buildings/*` — buildings, PMG references, required_construction
- `common/script_values/building_values.txt` — construction tier constants
- `common/pop_types/*.txt` — wage_weight, etc.
- `common/goods/00_goods.txt` — cost, etc.
- `common/building_groups/00_building_groups.txt` — parent_group chain
- `launcher/launcher-settings.json` — game version
