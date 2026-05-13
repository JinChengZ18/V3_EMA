# 更新日志 / Changelog

V3_EMA 的版本变更记录，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

版本号采用 [语义化版本](https://semver.org/lang/zh-CN/)：MAJOR.MINOR.PATCH。

---

## [Unreleased] — 人口与劳动力分析整合进 v3_ema

### 整合 (Integrated)

- **`demography_analysis/` 子项目并入 `v3_ema.demography` 包**：原本的 11 个模块从项目根的 `demography_analysis/` 目录迁到 `v3_ema/demography/`，与 `v3_ema/{analysis,output,parser,util}` 同级。
- **新增 CLI 子命令 `v3-ema demography report`**：与既有的 `v3-ema {report, regions report}` 平行，复用 `find_game_root`、`_resolve_game_root`、`_resolve_ui_lang`、`get_logger()`、`out/<feature>/` 目录约定。新的 `--ui-lang {zh,en,both,auto}` 默认 `both`（仍生成中英双语 4 份 HTML，与旧脚本一致）。
- **退役旧入口** `demography_analysis/analyze_demography.py`，移入回收站。所有功能迁到 CLI 子命令；旧的直接调用方式不再支持。
- **测试** `tests/test_demography.py` 的 36 个测试 import 全部改为 `v3_ema.demography.*`，全绿。
- **输出位置不变**：仍写到 `V3_EMA/out/demography/`（沿用 `DEFAULT_OUT_DIR / "demography"`，与 `out/buildings/`、`out/regions/` 同构）。8 份 CSV 的 md5 整合前后 byte-exact 一致。

### 文档 (Docs)

- 根 `README.md` 与 `README.en.md` 各加「功能 3 / Feature 3」一节，介绍 `v3-ema demography report` 用法、输出文件、`--scenarios-from`、`--sol-start/--sol-end`、`--no-skew` 等选项。
- `v3_ema/demography/README.md` 改为面向贡献者的包内开发文档（模块表 + 模型注记），用户文档统一指向项目根 README。

---

## [Unreleased pre-integration] — `demography_analysis` 改进批 2

人口与劳动力分析模块的模型保真度、报告完整度、CLI 体验同步提升。

### 新增 (Added)

- **场景值从 `game/common` 解析**（M1）：新增 [game_modifiers.py](demography_analysis/game_modifiers.py)，CLI 默认 `--scenarios-from=game` 直接读取 `law_public_health_insurance`、`law_charitable_health_system`、`law_private_health_insurance`、`law_women_in_the_workplace`、`starvation_penalty`、`severe_starvation_penalty` 等命名块。`--scenarios-from=hardcoded` 退回 `scenarios.py` 的常量。游戏文件缺失 → 自动 fallback 并 stderr 警告。
- **`Starvation (partial)` 默认场景**：对应游戏 `starvation_penalty`（**满强度**出生 -70%、死亡 +60%；引擎按 Starvation 缩放后典型约 -35%/+30%）。过去只有 `Severe starvation`，现常态饥荒也能横向比较。
- **`WORKING_ADULT_RATIO_SKEW_MAXIMUM` 偏移模型**：`project_workforce_ratio` 不再均匀分摊死亡。当当前比例与目标比例偏离时，按 `skew = clamp(target/current, 1/SKEW_MAX, SKEW_MAX)` 把死亡向被低估的群体倾斜，推动比例收敛得更快。`--no-skew` 回到旧的均匀模型。
- **动态 SoL 投影**：`--sol-start FLOAT --sol-end FLOAT` 让 SoL 在投影窗口内按线性轨迹演化。`model.project_workforce_ratio` 接收 `sol_trajectory` 回调；带轨迹时不复用缓存 rates。SoL 敏感性组（已带 `projection_sol`）不受影响。
- **污染瞬态模拟**：`model.simulate_pollution(generated, arable, months)` 按 `pollution += (target - pollution) * change_speed / pollution_max` 月演化。CLI 输出新文件 `pollution_dynamics.csv`，`--pollution-dynamics-months` 控制长度（0 关闭）。
- **英文学术分析报告** `demography_analysis_report_en.html`：原本只有中文。所有章节文案进 `i18n.ANALYSIS_TEXT` 双语字典。
- **更多 CLI 开关**：`--language {en,zh,all}`、`--no-html`、`--no-csv`、`--skip-modifier-scan`、`--bar-chart-top-n N`。
- **`sol_to_wealth(sol)` 映射**（M8）：`Scenario.wealth_from_sol=True` 现按 `1.5 * sol` 估算代理 wealth，不再粗暴地 `wealth = sol`。`Private health` 场景从「(wealth=SoL)」改名「(wealth from SoL)」反映新口径。

### 变更 (Changed)

- **污染 SoL 惩罚被 `state_pollution_reduction_health_mult` 缩放**（M7）：原代码只对死亡率乘数应用 reduction，对同一静态修正块里的 SoL 惩罚遗漏了。`pollution_sol_penalty = -3 * impact * (1 + reduction_health_mult)`。
- **CSV 浮点格式化**（P4）：`write_csv` 默认 `float_digits=6`，消除 `0.05399999999999999` 这种浮点尾巴。`float_digits=None` 关闭。
- **`build_analysis_report_zh` → `build_analysis_report(language=...)`**：旧名作为薄 shim 仍可用。

### 修复 (Fixed)

- 重构前的单文件 1798 行 `analyze_demography.py` 拆分为 11 个模块（`util/constants/model/scenarios/modifier_scan/modifier_lookup/game_modifiers/i18n/chart_svg/rows/report`），主入口缩到约 280 行。
- `project_workforce_ratio` 内 `adjusted_rates` 由每月调用降为静态 SoL 路径每场景调用一次（P1，约 60× 减少）。
- 劳动力图 y 轴不再钉死 25%–50%，由 `workforce_chart_bounds(initial, target)` 按实参外扩，避免非默认参数被裁剪（P2）。
- HTML CSS 抽出 `REPORT_CSS`/`ANALYSIS_CSS` 常量，不再两份模板各贴一份（R1）。
- 图表样式与翻译解耦（S4）：`svg_line_chart` 接收 `style_keys` 参数，调用方显式标 `"base"/"birth"/"mortality"/"natural_growth"`；不再依赖匹配 "出生率"/"birth" 等翻译字串。
- `formula_block` 同步反映 M4 skew、M5 瞬态污染、M7 SoL 惩罚缩放、M8 wealth 映射（R4）。
- 学术分析报告「7. 局限性」节附量化差异行：skew on/off 与 SoL 轨迹/常量两组对比的最终比例 / 总人口偏差（R3）。
- **bug fix**：`Starvation (partial)` 的硬编码 `birth_mult=-0.25` 与游戏实际 `state_birth_rate_mult=-0.7` 不符，已纠正为 `-0.70`（M1 的漂移哨兵首次发现）。
- 新增 `tests/test_demography.py`，36 个测试覆盖常量解析、分段曲线、污染钳位、投影守恒律、modifier_lookup 提取、skew 行为、动态 SoL、wealth 映射、污染瞬态、starvation_penalty 漂移哨兵等。

### 输出影响（baseline 已 bump）

- `rates_by_sol.csv`、`net_growth_sensitivity.csv`、`workforce_projection.csv`、`workforce_sensitivity.csv`、`modifier_source_summary.csv`：受 M3/M4/M7/M8/P4 影响，数值小幅变化（饥荒新行、skew 改变投影、污染惩罚加深、wealth proxy 变化、浮点格式化）。
- 新增 `pollution_dynamics.csv`、`demography_analysis_report_en.html`。
- `modifier_sources.csv`、`pollution_impact_examples.csv`：内容不变。

---

## [0.4.0] — 2026-05-10

V3_EMA 的「成熟度」里程碑：项目可放置任何位置、文件名版本化、双语 + 双功能完备。

### 新增 (Added)

- **可放置任意位置**：[v3_ema/game_root.py](v3_ema/game_root.py) 新增。按优先级解析游戏路径：`--game-root` 参数 → `V3_GAME_ROOT` 环境变量 → 缓存文件 `.game_root` → Steam 库扫描（注册表 + `libraryfolders.vdf`）→ 项目祖先回溯。Steam 自动检测后写入缓存。
- **`config` 子命令**：`python -m v3_ema config --game-root <path>` 持久化保存；`--show` 查看；`--clear` 清缓存。
- **内置基线**：[baselines/](baselines/) 提供 1.8.7 与 1.13.4 的 buildings/regions xlsx，开箱即可 diff，无需先生成。
- **自动版本化文件名**：`--out` 留空时自动命名 —— `report_buildings_v<ver>.xlsx` / `diff_buildings_v<old>_to_v<new>.xlsx`，避免覆盖。
- **CHANGELOG.md** —— 本文件。

### 变更 (Changed)

- **diff 表列布局对齐主报表**：[output/diff_writer.py](v3_ema/output/diff_writer.py) 与 [output/regions_diff_writer.py](v3_ema/output/regions_diff_writer.py) 的「变更」sheet 现使用主报表的列顺序（重要数值在前、文本与 ID 在后），每格**在位**显示差分（数值 = `new - old`，文本 = 新值），不再 旧/新/Δ 三列并排。
- **diff 永远输出全部 6 个 sheet**（即使某段 0 改动也带「— (none) —」占位行），消除「diff 失败了？」的歧义。
- **buildings/regions 输出独立子目录**：`out/buildings/{reports,diffs}/`、`out/regions/{reports,diffs}/`。
- **README 改写**：按功能（功能 1 / 功能 2）分组命令清单；安装步骤强调「解压到任意位置」；中英双版互链。

### 修复 (Fixed)

- **i18n 闭包变量遮蔽**：`label_to_key()` 内层循环遮蔽外层参数，导致首次调用返回错误结果（[i18n.py](v3_ema/i18n.py)）。
- **regions sheet 行错位**：`_style_data_sheet` 加 `data_row_offset` 参数，让合计行不进入条件格式范围、最后一行得到样式。
- **regions diff 漏汇总动态资源列**：合计分支检查 `cap_/pot_` 前缀已废弃，改 `res_`。
- **首列填色色域偏移**：regions writer 关闭地区列的 `fill_anchor_col`，保留居中加粗但不再着 indigo 底色。
- **modifier 译文残留英文**：`_format_modifier` 增加 loc 回退，未在 curated map 时查游戏 `modifiers_l_*.yml`；yml_loc 增加 `[concept_X]` 与 `[Concept('foo','fb')]` 解析、`@key!` 图标剥离。

---

## [0.3.0] — 2026-05-10

跨版本对比能力 + 完整多语言支持。

### 新增

- **跨版本 diff**：`v3-ema diff old.xlsx new.xlsx` 输出新增/移除/变更三段（各含 combo + construction）。包含 ε 阈值避免浮点抖动误报。
- **报告内嵌游戏版本**：「信息」sheet 含游戏版本、tool 版本、生成时间；从 `launcher/launcher-settings.json` 读取。
- **多语言支持**：V3 全部 11 种内置本地化（simp_chinese / english / french / ...），UI 自动跟随（`--ui-lang` 强制覆盖）。
- **i18n 模块**：[v3_ema/i18n.py](v3_ema/i18n.py) 集中所有 UI 字符串（zh / en）。
- **跨语言 diff**：headers 通过 `label_to_key` 反向映射回 canonical 字段名，zh 报告 vs en 报告也能 diff。
- **测例**：[tests/test_diff.py](tests/test_diff.py) 6 个用例（minimal / eps / cross-lang / regions × 3）。
- **理论文档**：[docs/economics.md](docs/economics.md)、[docs/method.md](docs/method.md) 中英双版。
- **regions feature**：地区资源统计第二大功能完整落地（详见下文）。

### 变更

- 项目重命名 `vic3_econ` → `V3_EMA` / `v3_ema`。
- README 学术化 → 模组说明风格 → 按功能整理（功能 1 / 功能 2）。
- 字体统一为 `Microsoft YaHei`，调色板换 Tailwind 风格。

---

## [0.2.x] — 2026-05-10

模组核心稳态、地区分析与诸多 UX 修复。

### 新增

- **功能 2：地区资源统计**（[v3_ema/analysis/regions.py](v3_ema/analysis/regions.py)、[output/regions_writer.py](v3_ema/output/regions_writer.py)）。
  - 解析 `game/map_data/state_regions/`、`game/common/strategic_regions/`、`game/common/state_traits/`。
  - 14 个大洲分桶（西欧 / 南欧 / 北欧 / 东欧 / 北美 / 中美 / 南美 / 非洲 / 中东 / 中亚 / 印度 / 东亚 / 东南亚 / 大洋洲）。
  - 每张 sheet 首行**合计**（同桶资源汇总）。
  - **动态资源列**：扫游戏数据列出每种采掘建筑（铁矿 / 煤矿 / 油井 / ...），每行单独数值便于排序。
  - 「特性加成」对应 V3 modifier 全文翻译。
- **建造部门**：单独一张 sheet，显示物料/工资 单位建造力成本（颜色低=好，反向条件格式）。
- **现代化样式**：模板加深、斑马线、冻结窗格、隐藏网格。
- **类别条件格式**：利润 / 建造力回报率 / 人均年产值 三色色阶。

### 变更

- 列重排多次：建筑列移首位、投入产出移近末尾、ID 列只按表头宽。
- 「净产值」→「利润」；「人均产值」→「人均年产值」（×52 年化，与游戏 tooltip 对齐）。
- 「自动化」类生产方式：所有权 PMG 默认 PM 雇佣并入总计（修了艺术学院劳动力为 0 的 bug）。
- 信息量为 0 的行（无产能、无修饰）被过滤（如 `pm_monument_no_effects`）。

### 修复

- dummy 建筑（loc 名 > 30 字符）跳过。
- PDX `?=`、`!=` 比较运算符 + tagged-block 语法 (`color = hsv{...}`) 解析。

---

## [0.1.0] — 2026-05-10

首版：建筑生产方式产值表。

### 新增

- 自研 PDX 词法/语法解析器（[v3_ema/parser/](v3_ema/parser/)），无需游戏二进制依赖。
- 本地化 yml 解析含 `$ref$` 递归。
- 建筑 × 生产方式组合的笛卡尔积（约 1500 行）含投入/产出/利润/建造力/劳动力/工资倍率等 19 列。
- xlsx 输出（openpyxl）+ CSV 后备。

---

## 维护说明

- 每次发版前更新 `v3_ema/__init__.py.__version__` 与 `pyproject.toml` 的 `version` 同步。
- 在本文件添加新版本节，列「新增 / 变更 / 修复」三类（对应 Added / Changed / Fixed）。
- 若主版本号变更（破坏性改动），需同步更新 README 与 docs/。
- 重大改动后建议重生 `baselines/baseline_*_v<version>.xlsx`，方便用户开箱 diff。
