# 更新日志 / Changelog

V3_EMA 的版本变更记录，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

版本号采用 [语义化版本](https://semver.org/lang/zh-CN/)：MAJOR.MINOR.PATCH。

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
