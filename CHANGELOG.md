# 更新日志 / Changelog

V3_EAT 的版本变更记录，遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 格式。

版本号采用 [语义化版本](https://semver.org/lang/zh-CN/)：MAJOR.MINOR.PATCH。

---

## [0.5.0] — 2026-06-15

**功能 2 扩展：地区资源可视化**（[v3_eat/map/](v3_eat/map/)）。把地区资源统计表的数字画到游戏自带世界地图上——这是功能 2 的自然延伸，故归入同一小节。本条目合并了开发期的多次同日迭代。

### 新增 (Added)

- **资源等值图（choropleth）**：CLI `v3-eat regions map`。技法是 Paradox 社区通用的「省份索引色 → 查找表重着色」——每个省份在 `game/map_data/provinces.png` 里是唯一平涂色，用 numpy 2²⁴ 项 LUT 一次性向量化整图重着色（8192×3616 约 2 秒）。经像素级核验：省→州 1:1 零碰撞、99.76% 像素直接命中，余者为省界抗锯齿（自然成描边）。
- **可选依赖** `[map] = pillow, numpy`；`model.StateRegion.province_colors` + loader 保留省色（对既有 buildings/regions/demography 功能零影响）。
- **按资源种类自动配色** `--cmap auto`（默认）：每种资源一个助记色相（煤=炭黑、铁=钢蓝、硫=黄、金=琥珀、油=茄紫、伐木=森绿、渔=青、捕鲸=藏蓝、橡胶=橄榄、铅=石板紫），浅→深 = 少→多；另有 viridis/magma/plasma/inferno 与单色系。`--gamma`（默认 0.7）增强深浅区分。
- **地块数值标注**：每州在几何中心标注数量（面积加权质心，含 wrap_x 反子午线**环绕修正**——如俄罗斯楚科奇跨地图边界不再偏移到海里）。`--labels/--no-labels`。
- **维多利亚风格**：图例/标注用游戏自带字体（ParadoxVictorian / Playfair / EB Garamond + Noto Serif SC）；羊皮纸图例卡置于**中下方**，大标题 + 资源色块，缩略图也能分辨；图片输出统一英文。
- **州界 + 1836 国界**：`--borders`（默认）描州界与海岸线；`--countries` 叠国界，`--country-filter {civilized(默认),recognized,all}` 据 `country_type` 过滤（civilized 丢弃 decentralized 部落政权但保留中日波斯等大国），`--min-country-provinces`（默认 8）按规模再过滤。
- **矢量 SVG** `--svg`（可配 `--all`，每图一份）：高清栅格底图 + 矢量数值/图例，`@font-face` 内嵌游戏字体，缩放打印不糊。
- **高清导出** `--full-res`（原生 8192px）；另有 `--width`、`--clip`、`--log-scale`、`--reverse`、`--grid`。
- **交互式 HTML** `resource_map.html`：单文件，浏览器端 canvas 重着色，下拉切 14 图层 / 配色、按大洲缩放、搜地区名、开关标注、悬停看「州名 + 数值」。
- **跨版本资源变化图** `regions map-diff old.xlsx new.xlsx`：复用 `read_regions_report` 逐州求差，发散配色（红=削减、绿=增加），按各报表自身语言匹配资源列。变化量**仅在两个版本都存在的州之间**比较（以州的存在性为准，而非指标值）：跨大版本（如 1.0.6→1.13.8）被改名/拆分/合并的州——例如孟加拉 NORTH/SOUTH→WEST/EAST——不再因 `old=0` 而被画成满值的假性突变（曾有 93 个"新州"伪绿色尖峰）；同时仍保留持续存在的州 0↔N 的真实资源增减。
- **多版本时间线** `regions map-timeline a.xlsx b.xlsx …`：版本滑块 + 绝对值 / Δ较上版 / Δ较首版。
- **跨版本资源匹配（按稳定 id，而非本地化列名）**：资源列以建筑的本地化名称作表头，但建筑跨版本会被改名/改翻译，旧版报表按当前版本的名称匹配会**整列落空**。现按建筑 id + 历史名兼容表匹配：
  - 改名建筑（`石油精炼厂`→`油井` / `捕鲸业`→`捕鲸站` / `渔业`→`渔业码头` / `林业`→`伐木营地`）在所有版本都能正确取值，不再在旧版显示为空；
  - 旧版未翻译的 `bg_gold_fields` 折叠进「金矿」（`RESOURCE_ALIASES` + 原始 id 候选），不再漏配；
  - 已从游戏移除的资源种类（`Monuments` / `bg_monuments` / 奇观）作为**历史图层**补回时间线，滑到新版自动归零（解决"资源种类缺失"）；标签按地图渲染语言本地化（地图输出统一英文）；
  - **「资源种类」聚合**改为从报表自身的资源列实时统计（报表没有该列，旧实现导致除当前版本外**所有基线版本全为空**）；
  - 报表写出端：表头本地化缺失时回退到规范资源名/可读名，**不再泄漏 `bg_`/`building_` 原始 id**（修复旧版基线里的 `bg_gold_fields` 列名；对既有基线为显示层面，匹配已不受影响）；
  - **交互 HTML 统一英文**：时间线/查看器的资源图层名、历史图层名（Monuments）、大洲分桶名均随地图输出走英文，不再中英混排。
- **地图嵌入 Excel** `regions report --maps`：渲染图集内嵌为「资源地图」工作表。
- **「金矿 / 金矿场」合并**：`building_gold_field`（可发现地表矿，`depleted_type = building_gold_mine`）与 `building_gold_mine` 是同一资源的不同阶段，按 canonical 求和为单一图层（资源图层 11 → 10）。
- **农作物分布图** `regions map --crops`（[metrics.build_crop_metrics](v3_eat/map/metrics.py)）：按各州 `arable_resources` 列出 16 种作物（小麦/水稻/棉花/烟草/葡萄/甘蔗/咖啡/茶/丝/染料/罂粟…），每图显示该作物的**可种植范围**并按可耕地深浅着色；每种作物一个助记色（[colormap.CROP_DARK](v3_eat/map/colormap.py)）。输出到 `out/regions/maps/crops/`；交互 HTML 也增列这 16 个作物图层（共 30 层）。
- **渲染进度条**（无新依赖，stderr）。

### 修复 / 调整 (Fixed / Refinements)

- **「·」乱码**：分隔符在 ParadoxVictorian 字体缺字形 → 版本行改用 EB Garamond（含 middot）渲染，标题仍用 ParadoxVictorian（无此符号）。
- **标题移到海洋空白区**（参考 V3 Wiki 范例）：不再用遮挡地图的 plaque——按 WATER 覆盖率自动在最空旷海域定位标题，白色描边增强辨识、字号略缩、保留资源色块；图例卡留在**左下角**并略放大。
- **楚科奇环绕修正**：跨 `wrap_x` 反子午线的州（楚科奇/阿拉斯加）改用圆周加权质心，标注不再落到海里（PNG + HTML）。
- **标注随分辨率缩放**：数值字号上下限按图宽缩放（PNG + SVG），`--full-res` / showcase 的数字不再偏小，与主图集一致。
- **交互地图无限左右滚动**：`resource_map.html` 改为相机模型——拖动平移、滚轮缩放、**横向首尾相连无缝环绕**（如 P 社游戏内地图），消除缩放接缝处的割裂感；大洲跳转**居中**（原先锁左）、包围盒**环绕感知**（修复东亚/大洋洲跨接缝不缩放）。
- **交互地图更清晰**：底图默认 4096px，新增 `--html-width`（可上探 8192）；真·矢量请用 `--svg`（浏览器内多边形矢量化需轮廓库，暂不可行）。

### 输出 / 文档 (Output / Docs)

- 输出整理到 `out/regions/maps/`：图集 PNG/SVG + 交互 HTML 在顶层；`diffs/` 变化图、`crops/` 农作物、`atlas/` Excel 素材、`showcase/` 高清·国界分目录。
- 根 `README.md` / `README.en.md`：地图并入「功能 2：地区资源统计与可视化」小节（2a 表格 + 2b 地图），并新增示例插图（`docs/images/`）。
- **依赖管理**：新增 [requirements.txt](requirements.txt)（openpyxl / pillow / numpy / scipy），`pip install -r requirements.txt` 一键装齐；`pyproject` 的 `[map]` extra 同步加入 scipy（用于加粗国界，缺失时自动降级）。
- **一键生成脚本** [scripts/gen_maps.sh](scripts/gen_maps.sh)：跑一遍功能 2b 全部命令/参数，分桶输出到 `out/regions/maps/`，README 已说明（Windows 用 Git Bash）。
- **内置多版本基线**：`baselines/baseline_{buildings,regions}_v{1.0.6,1.3.6,1.6.2,1.9.8,1.13.8}.xlsx`（均反映分桶修复后的结构），跨版本可直接 `diff` / `regions diff` / `regions map-diff` 对比（如 1.6.2→1.13.8 建筑 Δ933、地区 1.6.2→1.9.8 Δ189）。新增 [scripts/make_baseline.sh](scripts/make_baseline.sh)：切换 Steam 版本后一键生成、**按当前安装版本号自动命名**基线。`scripts/gen_maps.sh` 的 diff / timeline 案例已更新为跨整条 1.0.6→1.13.8 链（timeline 串联全部 5 个基线版本）。
- **地区分桶修复（跨版本通用）**：1.13.x 的近东 / 尼罗河流域 / 大波斯 → 中东，大西洋海岸 → 北美，大哥伦比亚 → 南美，喜马拉雅 → 东亚；并补全 1.9.x（Lady Grey）的 31 个细分战略大区（英格兰/法兰西/莱茵/南北德意志/伊比利亚/意大利/多瑙/波兰/芬兰/波罗的/白俄/第聂伯/乌拉尔/东西西伯利亚/迪克西/中西部/马德拉斯/孟买/孟加拉/旁遮普/阿拉伯/刚果/尼日尔/塞内加尔/埃塞俄比亚/僧祇/北海/俄罗斯极地 等）。分桶表是各版本战略大区的并集，不同版本都不再出现「其他」表单，交互 HTML 大洲分组同步修正。
- **签名水印**：地图右下角（与左下图例对称）标注「Econometrics Automation Tool / map by J.C.」，PNG/SVG/交互 HTML 均有。
- **改名 EMA → EAT**：包 `v3_ema` → `v3_eat`、命令 `v3-eat` / `python -m v3_eat`、`pyproject`、测试、脚本、全部文档；正文 EMA/V3_EMA → EAT/V3_EAT，中文「计量经济自动化模组」→「计量经济自动化工具」。

---

## [0.4.5] — 2026-06-01 — 人口与劳动力分析整合进 v3_eat

### 整合 (Integrated)

- **`demography_analysis/` 子项目并入 `v3_eat.demography` 包**：原本的 11 个模块从项目根的 `demography_analysis/` 目录迁到 `v3_eat/demography/`，与 `v3_eat/{analysis,output,parser,util}` 同级。
- **新增 CLI 子命令 `v3-eat demography report`**：与既有的 `v3-eat {report, regions report}` 平行，复用 `find_game_root`、`_resolve_game_root`、`_resolve_ui_lang`、`get_logger()`、`out/<feature>/` 目录约定。新的 `--ui-lang {zh,en,both,auto}` 默认 `both`（仍生成中英双语 4 份 HTML，与旧脚本一致）。
- **退役旧入口** `demography_analysis/analyze_demography.py`，移入回收站。所有功能迁到 CLI 子命令；旧的直接调用方式不再支持。
- **测试** `tests/test_demography.py` 的 36 个测试 import 全部改为 `v3_eat.demography.*`，全绿。
- **输出位置不变**：仍写到 `V3_EAT/out/demography/`（沿用 `DEFAULT_OUT_DIR / "demography"`，与 `out/buildings/`、`out/regions/` 同构）。8 份 CSV 的 md5 整合前后 byte-exact 一致。

### 报告 (Report)

- **数据报告与分析报告合并为单文件**：过去每种语言产出两份 HTML（`demography_report_{lang}.html` 数据报告 + `demography_analysis_report_{lang}.html` 分析正文），现合并为单份 `demography_report_{lang}.html`，分析正文、全部图表、场景表与数据字典内联同一文档。`build_analysis_report(language=…)` 为合并后的唯一报告入口；CLI 运行时自动清理旧的 `demography_analysis_report_{lang}.html` 与重名 `demography_report.html`。
- **i18n 文案随合并更新**：`REPORT_TEXT` / `ANALYSIS_TEXT` 移除「配套文件 / companion file」「见数据报告」等跨文件指向，统一改为「本报告」；`source_line`、`figures_pointer_body`、`limits` 等键同步改写，分析正文（医疗、通用食品、劳动力比例、工业污染、饥荒、识字率、方法局限）整体扩写。
- **术语统一**：医疗法律的标签与注释将「私人医保」统一为「私立医疗」。

### 文档 (Docs)

- 根 `README.md` 与 `README.en.md` 各加「功能 3 / Feature 3」一节，介绍 `v3-eat demography report` 用法、输出文件、`--scenarios-from`、`--sol-start/--sol-end`、`--no-skew` 等选项。
- `v3_eat/demography/README.md` 改为面向贡献者的包内开发文档（模块表 + 模型注记），用户文档统一指向项目根 README。
- 根 `README.md` / `README.en.md` 的「功能 3 / Feature 3」输出清单同步为单份合并报告，移除已不再生成的 `demography_analysis_report_{lang}.html` 条目。

---

## [0.4.4] — 2026-05-28 — `demography_analysis` 改进批 2

人口与劳动力分析模块的模型保真度、报告完整度、CLI 体验同步提升。

### 新增 (Added)

- **场景值从 `game/common` 解析**（M1）：新增 [game_modifiers.py](demography_analysis/game_modifiers.py)，CLI 默认 `--scenarios-from=game` 直接读取 `law_public_health_insurance`、`law_charitable_health_system`、`law_private_health_insurance`、`law_women_in_the_workplace`、`starvation_penalty`、`severe_starvation_penalty` 等命名块。`--scenarios-from=hardcoded` 退回 `scenarios.py` 的常量。游戏文件缺失 → 自动 fallback 并 stderr 警告。
- **`Starvation (partial)` 默认场景**：对应游戏 `starvation_penalty`（**满强度**出生 -70%、死亡 +60%；引擎按 Starvation 缩放后典型约 -35%/+30%）。过去只有 `Severe starvation`，现常态饥荒也能横向比较。
- **`WORKING_ADULT_RATIO_SKEW_MAXIMUM` 偏移模型**：`project_workforce_ratio` 不再均匀分摊死亡。当当前比例与目标比例偏离时，按 `skew = clamp(target/current, 1/SKEW_MAX, SKEW_MAX)` 把死亡向被低估的群体倾斜，推动比例收敛得更快。`--no-skew` 回到旧的均匀模型。
- **动态 SoL 投影**：`--sol-start FLOAT --sol-end FLOAT` 让 SoL 在投影窗口内按线性轨迹演化。`model.project_workforce_ratio` 接收 `sol_trajectory` 回调；带轨迹时不复用缓存 rates。SoL 敏感性组（已带 `projection_sol`）不受影响。
- **污染瞬态模拟**：`model.simulate_pollution(generated, arable, months)` 按 `pollution += (target - pollution) * change_speed / pollution_max` 月演化。CLI 输出新文件 `pollution_dynamics.csv`，`--pollution-dynamics-months` 控制长度（0 关闭）。
- **更多 CLI 开关**：`--language {en,zh,all}`、`--no-html`、`--no-csv`、`--skip-modifier-scan`、`--bar-chart-top-n N`。
- **`sol_to_wealth(sol)` 映射**（M8）：`Scenario.wealth_from_sol=True` 现按 `1.5 * sol` 估算代理 wealth，不再粗暴地 `wealth = sol`。`Private health` 场景从「(wealth=SoL)」改名「(wealth from SoL)」反映新口径。

### 变更 (Changed)

- **污染 SoL 惩罚被 `state_pollution_reduction_health_mult` 缩放**（M7）：原代码只对死亡率乘数应用 reduction，对同一静态修正块里的 SoL 惩罚遗漏了。`pollution_sol_penalty = -3 * impact * (1 + reduction_health_mult)`。
- **CSV 浮点格式化**（P4）：`write_csv` 默认 `float_digits=6`，消除 `0.05399999999999999` 这种浮点尾巴。`float_digits=None` 关闭。
- **`build_analysis_report_zh` → `build_analysis_report(language=...)`**：旧名作为薄 shim 仍可用。

### 修复 (Fixed)

- 重构前的单文件 1798 行 `analyze_demography.py` 拆分为 11 个模块（`util/constants/model/scenarios/modifier_scan/modifier_lookup/game_modifiers/i18n/chart_svg/rows/report`），主入口缩到约 280 行。
- `project_workforce_ratio` 内 `adjusted_rates` 由每月调用降为静态 SoL 路径每场景调用一次（P1，约 60× 减少）。
- HTML CSS 抽出 `REPORT_CSS`/`ANALYSIS_CSS` 常量，不再两份模板各贴一份（R1）。
- 图表样式与翻译解耦（S4）：`svg_line_chart` 接收 `style_keys` 参数，调用方显式标 `"base"/"birth"/"mortality"/"natural_growth"`；不再依赖匹配 "出生率"/"birth" 等翻译字串。
- `formula_block` 同步反映 M4 skew、M5 瞬态污染、M7 SoL 惩罚缩放、M8 wealth 映射（R4）。
- **bug fix**：`Starvation (partial)` 的硬编码 `birth_mult=-0.25` 与游戏实际 `state_birth_rate_mult=-0.7` 不符，已纠正为 `-0.70`（M1 的漂移哨兵首次发现）。
- 新增 `tests/test_demography.py`，36 个测试覆盖常量解析、分段曲线、污染钳位、投影守恒律、modifier_lookup 提取、skew 行为、动态 SoL、wealth 映射、污染瞬态、starvation_penalty 漂移哨兵等。

### 输出影响（baseline 已 bump）

- `rates_by_sol.csv`、`net_growth_sensitivity.csv`、`workforce_projection.csv`、`workforce_sensitivity.csv`、`modifier_source_summary.csv`：受 M3/M4/M7/M8/P4 影响，数值小幅变化（饥荒新行、skew 改变投影、污染惩罚加深、wealth proxy 变化、浮点格式化）。
- 新增 `pollution_dynamics.csv`。
- `modifier_sources.csv`、`pollution_impact_examples.csv`：内容不变。

---

## [0.4.0] — 2026-05-10

V3_EAT 的「成熟度」里程碑：项目可放置任何位置、文件名版本化、双语 + 双功能完备。

### 新增 (Added)

- **可放置任意位置**：[v3_eat/game_root.py](v3_eat/game_root.py) 新增。按优先级解析游戏路径：`--game-root` 参数 → `V3_GAME_ROOT` 环境变量 → 缓存文件 `.game_root` → Steam 库扫描（注册表 + `libraryfolders.vdf`）→ 项目祖先回溯。Steam 自动检测后写入缓存。
- **`config` 子命令**：`python -m v3_eat config --game-root <path>` 持久化保存；`--show` 查看；`--clear` 清缓存。
- **内置基线**：[baselines/](baselines/) 提供 1.8.7 与 1.13.4 的 buildings/regions xlsx，开箱即可 diff，无需先生成。
- **自动版本化文件名**：`--out` 留空时自动命名 —— `report_buildings_v<ver>.xlsx` / `diff_buildings_v<old>_to_v<new>.xlsx`，避免覆盖。
- **CHANGELOG.md** —— 本文件。

### 变更 (Changed)

- **diff 表列布局对齐主报表**：[output/diff_writer.py](v3_eat/output/diff_writer.py) 与 [output/regions_diff_writer.py](v3_eat/output/regions_diff_writer.py) 的「变更」sheet 现使用主报表的列顺序（重要数值在前、文本与 ID 在后），每格**在位**显示差分（数值 = `new - old`，文本 = 新值），不再 旧/新/Δ 三列并排。
- **diff 永远输出全部 6 个 sheet**（即使某段 0 改动也带「— (none) —」占位行），消除「diff 失败了？」的歧义。
- **buildings/regions 输出独立子目录**：`out/buildings/{reports,diffs}/`、`out/regions/{reports,diffs}/`。
- **README 改写**：按功能（功能 1 / 功能 2）分组命令清单；安装步骤强调「解压到任意位置」；中英双版互链。

### 修复 (Fixed)

- **i18n 闭包变量遮蔽**：`label_to_key()` 内层循环遮蔽外层参数，导致首次调用返回错误结果（[i18n.py](v3_eat/i18n.py)）。
- **regions sheet 行错位**：`_style_data_sheet` 加 `data_row_offset` 参数，让合计行不进入条件格式范围、最后一行得到样式。
- **regions diff 漏汇总动态资源列**：合计分支检查 `cap_/pot_` 前缀已废弃，改 `res_`。
- **首列填色色域偏移**：regions writer 关闭地区列的 `fill_anchor_col`，保留居中加粗但不再着 indigo 底色。
- **modifier 译文残留英文**：`_format_modifier` 增加 loc 回退，未在 curated map 时查游戏 `modifiers_l_*.yml`；yml_loc 增加 `[concept_X]` 与 `[Concept('foo','fb')]` 解析、`@key!` 图标剥离。

---

## [0.3.0] — 2026-05-10

跨版本对比能力 + 完整多语言支持。

### 新增

- **跨版本 diff**：`v3-eat diff old.xlsx new.xlsx` 输出新增/移除/变更三段（各含 combo + construction）。包含 ε 阈值避免浮点抖动误报。
- **报告内嵌游戏版本**：「信息」sheet 含游戏版本、tool 版本、生成时间；从 `launcher/launcher-settings.json` 读取。
- **多语言支持**：V3 全部 11 种内置本地化（simp_chinese / english / french / ...），UI 自动跟随（`--ui-lang` 强制覆盖）。
- **i18n 模块**：[v3_eat/i18n.py](v3_eat/i18n.py) 集中所有 UI 字符串（zh / en）。
- **跨语言 diff**：headers 通过 `label_to_key` 反向映射回 canonical 字段名，zh 报告 vs en 报告也能 diff。
- **测例**：[tests/test_diff.py](tests/test_diff.py) 6 个用例（minimal / eps / cross-lang / regions × 3）。
- **理论文档**：[docs/economics.md](docs/economics.md)、[docs/method.md](docs/method.md) 中英双版。
- **regions feature**：地区资源统计第二大功能完整落地（详见下文）。

### 变更

- 项目重命名 `vic3_econ` → `V3_EAT` / `v3_eat`。
- README 学术化 → 模组说明风格 → 按功能整理（功能 1 / 功能 2）。
- 字体统一为 `Microsoft YaHei`，调色板换 Tailwind 风格。

---

## [0.2.x] — 2026-05-10

模组核心稳态、地区分析与诸多 UX 修复。

### 新增

- **功能 2：地区资源统计**（[v3_eat/analysis/regions.py](v3_eat/analysis/regions.py)、[output/regions_writer.py](v3_eat/output/regions_writer.py)）。
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

- 自研 PDX 词法/语法解析器（[v3_eat/parser/](v3_eat/parser/)），无需游戏二进制依赖。
- 本地化 yml 解析含 `$ref$` 递归。
- 建筑 × 生产方式组合的笛卡尔积（约 1500 行）含投入/产出/利润/建造力/劳动力/工资倍率等 19 列。
- xlsx 输出（openpyxl）+ CSV 后备。

---

## 维护说明

- 每次发版前更新 `v3_eat/__init__.py.__version__` 与 `pyproject.toml` 的 `version` 同步。
- 在本文件添加新版本节，列「新增 / 变更 / 修复」三类（对应 Added / Changed / Fixed）。
- 若主版本号变更（破坏性改动），需同步更新 README 与 docs/。
- 重大改动后建议重生 `baselines/baseline_*_v<version>.xlsx`，方便用户开箱 diff。
