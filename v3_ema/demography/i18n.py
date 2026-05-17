from __future__ import annotations


LABEL_TRANSLATIONS_ZH = {
    "birth": "出生率",
    "mortality": "死亡率",
    "natural growth": "自然增长率",
    "Base SoL curve": "基础 SoL 曲线",
    "Literacy 100%": "识字率 100%",
    "Food company prosperity": "食品公司繁荣",
    "Women's workplace": "女性工作",
    "Women's suffrage + food": "妇女选举 + 食品公司",
    "Women's suffrage + trade unions": "妇女选举 + 工会特质",
    "Pollution impact 50%": "污染影响 50%",
    "Pollution 100% + public health": "污染 100% + 公共医保",
    "Private health, wealth 20": "私人医保，财富 20",
    "No health system": "无医疗制度",
    "Charitable health": "慈善医院",
    "Public health": "公共医保",
    "Private health (wealth from SoL)": "私立医疗（财富按 SoL 映射）",
    "No health + pollution 50%": "无医疗 + 污染 50%",
    "Charitable health + pollution 50%": "慈善医院 + 污染 50%",
    "Public health + pollution 50%": "公共医保 + 污染 50%",
    "Private health + pollution 50%": "私人医保 + 污染 50%",
    "Starvation (partial)": "饥荒（部分）",
    "Severe starvation": "严重饥荒",
    "Base": "基准",
    "Birth mult -10%": "出生率乘数 -10%",
    "Birth mult -5%": "出生率乘数 -5%",
    "Birth mult +5%": "出生率乘数 +5%",
    "Birth mult +10%": "出生率乘数 +10%",
    "Mortality mult -10%": "死亡率乘数 -10%",
    "Mortality mult -5%": "死亡率乘数 -5%",
    "Mortality mult +5%": "死亡率乘数 +5%",
    "Mortality mult +10%": "死亡率乘数 +10%",
    "Mortality mult +50%": "死亡率乘数 +50%",
    "Literacy 0%": "识字率 0%",
    "Literacy 25%": "识字率 25%",
    "Literacy 50%": "识字率 50%",
    "Literacy 75%": "识字率 75%",
    "Pollution 0%": "污染 0%",
    "Pollution 25%": "污染 25%",
    "Pollution 50%": "污染 50%",
    "Pollution 75%": "污染 75%",
    "Pollution 100%": "污染 100%",
    "Target 25%": "目标 25%",
    "Target 35%": "目标 35%",
    "Target 40%": "目标 40%",
    "Target 45%": "目标 45%",
    "Target 50%": "目标 50%",
    "SoL 7": "SoL 7",
    "SoL 8": "SoL 8",
    "SoL 9": "SoL 9",
    "SoL 10": "SoL 10",
    "SoL 11": "SoL 11",
    "SoL 12": "SoL 12",
    "SoL 13": "SoL 13",
    "SoL 15": "SoL 15",
}


NOTE_TRANSLATIONS_ZH = {
    "Base SoL curve": "不施加州修正。",
    "Literacy 100%": "识字率惩罚：100% 识字率时出生率乘数 -10%。",
    "Food company prosperity": "食品公司繁荣修正：state_birth_rate_mult = 0.05。",
    "Women's workplace": "女性工作：目标劳动力比例 +10%，出生率 -5%；示例识字率设为 80%。",
    "Women's suffrage + food": "妇女选举 -5% 与食品公司 +5% 在识字率惩罚前抵消。",
    "Women's suffrage + trade unions": "妇女选举 +15%，叠加两个工会特质各 +5%；出生率 -5%。",
    "Pollution impact 50%": "state_region_pollution_health 按 50% 污染影响缩放：SoL -1.5，死亡率乘数 +25%。",
    "Pollution 100% + public health": "公共医保：死亡率 -5%，污染健康影响减少 15%。",
    "Private health, wealth 20": "私人医保：state_mortality_wealth_mult = -0.002，按财富点数缩放。",
    "No health system": "医疗制度控制组。",
    "Charitable health": "慈善医院：死亡率 -3%，污染健康影响减少 10%。",
    "Public health": "公共医保：死亡率 -5%，污染健康影响减少 15%。",
    "Private health (wealth from SoL)": "私立医疗：state_mortality_wealth_mult = -0.002，按由 SoL 线性映射的代理财富缩放。",
    "No health + pollution 50%": "固定污染影响 50% 的医疗制度控制组。",
    "Charitable health + pollution 50%": "固定污染影响 50%，慈善医院减少污染健康影响。",
    "Public health + pollution 50%": "固定污染影响 50%，公共医保减少污染健康影响。",
    "Private health + pollution 50%": "固定污染影响 50%，私立医疗按 SoL 代理财富并减少污染健康影响。",
    "Starvation (partial)": "starvation_penalty：满强度时出生率 -70%、死亡率 +60%（引擎按 Starvation 缩放，约 50% 强度封顶，典型效果 ≈ -35%/+30%）。",
    "Severe starvation": "severe_starvation_penalty：出生率 -90%，死亡率 +100%。",
}


REPORT_TEXT = {
    "en": {
        "html_lang": "en",
        "title": "Victoria 3 Demography Analysis",
        "game_root": "Game root",
        "intro": "This report separates the exposed base population-growth curves from additive modifier channels: literacy, pollution health effects, law/company modifiers, turmoil and wealth-scaled mortality. Annual percentages are monthly game rates multiplied by 12.",
        "formula_title": "Effective Formula",
        "base_title": "Base Birth, Mortality And Natural Growth",
        "base_chart": "Base annual birth, mortality and natural growth by SoL",
        "net_title": "Net Growth Scenarios",
        "net_note": "The overview chart omits workforce-law lines whose only population-growth effect is a birth-rate multiplier; those effects are broken out below. The y-axis is symmetric logarithmic because severe starvation is a visible negative outlier, with the 0% baseline marked explicitly.",
        "net_chart": "Annual net population growth by SoL",
        "net_sensitivity_title": "Net Growth Sensitivity Analysis",
        "net_sensitivity_intro": "These charts isolate one population-growth modifier channel at a time across SoL, using the same base formulas.",
        "workforce_title": "Workforce Ratio Projection",
        "workforce_chart": "Approximate workforce ratio convergence",
        "workforce_note": "Projection uses the visible monthly birth/death rates at SoL {sol:g} and compares all scenarios on the same {initial} to {target} workforce-ratio path. The engine also has an internal skew-correction path controlled by WORKING_ADULT_RATIO_SKEW_MAXIMUM; that exact C++ step is not exposed in script files.",
        "sensitivity_title": "Workforce Sensitivity Analysis",
        "sensitivity_intro": "The charts below isolate one factor at a time on the same initial population, SoL and projection window, so the direction and relative size of each effect is easier to read.",
        "style_note": "Continuous sensitivity charts use single-style solid lines with scientific colormap-style palettes; the base curve remains a heavier black reference.",
        "scenario_title": "Scenario Inputs",
        "source_title": "Modifier Source Scan",
        "source_chart": "Most common tracked modifier keys",
        "sol_axis": "Standard of Living",
        "rate_axis": "Annual rate",
        "net_axis": "Annual net growth",
        "years_axis": "Years",
        "workforce_axis": "Workforce ratio",
        "population_index_axis": "Population index",
        "mortality_population_chart": "Mortality multiplier effect on total population",
        "scenario": "Scenario",
        "birth_mult": "Birth mult",
        "mortality_mult": "Mortality mult",
        "literacy": "Literacy",
        "pollution": "Pollution",
        "target_workforce": "Target workforce",
        "notes": "Notes",
        "key": "Key",
        "hits": "Hits",
        "files": "Files",
        "min": "Min",
        "max": "Max",
        "pollution_steady_title": "Pollution · Steady-State Reference",
        "pollution_steady_note": "Engine formula: impact = clamp(generated_pollution / (50 + 1.5·√arable) / 255, 0, 1). Reads as the long-run impact a state settles at for a given combination of arable land and continuous pollution generation.",
        "pollution_steady_col_gen": "Generated pollution",
        "pollution_steady_col_arable": "Arable land",
        "pollution_steady_col_impact": "Steady impact",
        "pollution_dynamics_title": "Pollution · Transient Build-up",
        "pollution_dynamics_note": "Per-month: impact[t+1] = impact[t] + (target − impact[t]) · 0.255 / 255. With default constants the step is ~0.001/month, giving an exponential-approach time constant near 1000 months.",
        "pollution_dynamics_chart": "Transient pollution impact under continuous generation",
        "dict_title": "Data Dictionary",
        "dict_note": "Every chart and table is regenerated from the CSVs alongside this HTML. Below: the column meanings for each file.",
        "dict_col_file": "File",
        "dict_col_column": "Column",
        "dict_col_meaning": "Meaning",
        "chart_appendix_title": "Victoria 3 — Demography Data Report",
        "chart_appendix_intro": "Raw data report. Every CSV in this directory is mirrored here as a table or figure. Numbers regenerate with each game version. The narrative analysis is in the companion file <code>demography_analysis_report_en.html</code>.",
        "section_base_charts": "Base population curves",
        "section_scenarios_table": "Scenario definitions",
        "section_net_charts": "Net growth — scenarios and sensitivity",
        "section_workforce_charts": "Workforce ratio — projection and sensitivity",
        "section_pollution_charts": "Pollution — steady state and dynamics",
        "section_modifier_section": "Modifier source scan",
        "section_dict": "Data dictionary",
    },
    "zh": {
        "html_lang": "zh-CN",
        "title": "维多利亚3人口与劳动力分析",
        "game_root": "游戏目录",
        "intro": "本报告把游戏暴露出的基础人口增长曲线与各类修正通道分开处理：识字率、污染健康影响、法律与公司修正、动乱、按财富缩放的死亡率等。年度百分比按游戏月率乘以 12 计算。",
        "formula_title": "有效公式",
        "base_title": "基础出生率、死亡率与自然增长率",
        "base_chart": "按 SoL 绘制的基础年度出生率、死亡率与自然增长率",
        "net_title": "自然增长场景",
        "net_note": "概览图不再绘制那些人口增长效果只体现为出生率乘数的劳动力法律线；这些效果在下方单独展开。由于严重饥荒是明显负向离群值，y 轴使用对称对数坐标，并标出 0% 基线。",
        "net_chart": "按 SoL 绘制的年度自然增长率",
        "net_sensitivity_title": "自然增长敏感性分析",
        "net_sensitivity_intro": "这些图按 SoL 展开，一次只隔离一个人口增长修正通道，方便横向比较。",
        "workforce_title": "劳动力比例投影",
        "workforce_chart": "近似劳动力比例收敛",
        "workforce_note": "投影使用 SoL {sol:g} 下可见的月出生率和死亡率，并把所有场景放在同一条 {initial} 到 {target} 的劳动力比例路径上比较。引擎内部还存在由 WORKING_ADULT_RATIO_SKEW_MAXIMUM 控制的偏移修正；这一步没有暴露在脚本文件中。",
        "sensitivity_title": "劳动力比例敏感性分析",
        "sensitivity_intro": "下面的图一次只隔离一个因素，在相同初始人口、SoL 与投影窗口下比较，便于看清每种因素的方向与相对强度。",
        "style_note": "连续数值敏感性图使用统一实线和科研 colormap 风格配色；基准线保留为更粗的黑色参考线。",
        "scenario_title": "场景输入",
        "source_title": "修正来源扫描",
        "source_chart": "被跟踪修正键的出现次数",
        "sol_axis": "生活水平",
        "rate_axis": "年度比例",
        "net_axis": "年度自然增长率",
        "years_axis": "年",
        "workforce_axis": "劳动力比例",
        "population_index_axis": "人口指数",
        "mortality_population_chart": "死亡率乘数对总人口的影响",
        "scenario": "场景",
        "birth_mult": "出生率乘数",
        "mortality_mult": "死亡率乘数",
        "literacy": "识字率",
        "pollution": "污染",
        "target_workforce": "目标劳动力比例",
        "notes": "说明",
        "key": "键",
        "hits": "命中数",
        "files": "文件数",
        "min": "最小值",
        "max": "最大值",
        "pollution_steady_title": "污染 · 稳态参考",
        "pollution_steady_note": "引擎公式：impact = clamp(generated_pollution / (50 + 1.5·√arable) / 255, 0, 1)。表示长期稳定生产某污染量、可耕地某规模时的稳态 impact。",
        "pollution_steady_col_gen": "污染生成",
        "pollution_steady_col_arable": "可耕地",
        "pollution_steady_col_impact": "稳态 impact",
        "pollution_dynamics_title": "污染 · 瞬态演化",
        "pollution_dynamics_note": "月度递推：impact[t+1] = impact[t] + (target − impact[t]) · 0.255 / 255。按默认常数每月约 0.001 的步进，指数逼近的时间常数接近 1000 月。",
        "pollution_dynamics_chart": "持续生成下的污染 impact 瞬态演化",
        "dict_title": "数据字典",
        "dict_note": "所有图表都从同目录下的 CSV 重生成。下面列出每个文件每一列的含义。",
        "dict_col_file": "文件",
        "dict_col_column": "列",
        "dict_col_meaning": "含义",
        "chart_appendix_title": "维多利亚 3 — 人口数据报告",
        "chart_appendix_intro": "原始数据报告。同目录下的每个 CSV 都对应到本文档中的表格或图表，所有数值随每个游戏版本重新生成。分析正文位于配套文件 <code>demography_analysis_report_zh.html</code>。",
        "section_base_charts": "基础人口曲线",
        "section_scenarios_table": "场景定义",
        "section_net_charts": "净增长 · 场景与敏感性",
        "section_workforce_charts": "劳动力比例 · 投影与敏感性",
        "section_pollution_charts": "污染 · 稳态与瞬态",
        "section_modifier_section": "修正源扫描",
        "section_dict": "数据字典",
    },
}


SENSITIVITY_GROUPS = {
    "birth_multiplier": {
        "en": "Birth Multiplier Sensitivity",
        "zh": "出生率乘数敏感性",
    },
    "mortality_multiplier": {
        "en": "Mortality Multiplier Sensitivity",
        "zh": "死亡率乘数敏感性",
    },
    "literacy": {
        "en": "Literacy Sensitivity",
        "zh": "识字率敏感性",
    },
    "pollution": {
        "en": "Pollution Health Sensitivity",
        "zh": "污染健康影响敏感性",
    },
    "target_ratio": {
        "en": "Workforce Target Sensitivity",
        "zh": "劳动力目标比例敏感性",
    },
    "sol": {
        "en": "SoL Sensitivity",
        "zh": "SoL 敏感性",
    },
    "healthcare": {
        "en": "Healthcare System Sensitivity",
        "zh": "医疗制度敏感性",
    },
    "healthcare_pollution": {
        "en": "Healthcare Sensitivity With 50% Pollution",
        "zh": "50% 污染下的医疗制度敏感性",
    },
}


SENSITIVITY_NOTES = {
    "birth_multiplier": {
        "en": "Applies only state_birth_rate_mult around the base curve.",
        "zh": "只改变 state_birth_rate_mult，其他条件保持基准。",
    },
    "mortality_multiplier": {
        "en": "Applies only state_mortality_mult around the base curve.",
        "zh": "只改变 state_mortality_mult，其他条件保持基准。",
    },
    "literacy": {
        "en": "Uses literacy_penalty, which reduces births by up to 10% at full literacy.",
        "zh": "使用 literacy_penalty；满识字率时出生率最多降低 10%。",
    },
    "pollution": {
        "en": "Uses the pollution health static modifier: SoL penalty and mortality multiplier scaled by pollution impact.",
        "zh": "使用污染健康静态修正：SoL 惩罚与死亡率乘数按污染影响缩放。",
    },
    "target_ratio": {
        "en": "Varies only the target workforce ratio, including the 25% to 50% suffrage plus trade-union comparison.",
        "zh": "只改变目标劳动力比例，包含 25% 到 50% 的妇女选举加工会特质对比。",
    },
    "sol": {
        "en": "Varies only the fixed SoL used in the projection, concentrated around the transition region near SoL 10.",
        "zh": "只改变投影使用的固定 SoL，在 SoL 10 附近加密取点。",
    },
    "healthcare": {
        "en": "Controls pollution at 0% and compares health systems. Private health uses the plotted SoL as the wealth proxy instead of a fixed wealth value.",
        "zh": "把污染控制为 0%，只比较医疗制度。私立医疗使用图中 SoL 作为财富代理，不再固定财富 20。",
    },
    "healthcare_pollution": {
        "en": "Controls pollution at 50% to compare the same health systems under equal pollution exposure, including pollution-health reduction effects.",
        "zh": "把污染控制为 50%，在相同污染暴露下比较医疗制度，并包含污染健康影响减免。",
    },
}


# Data dictionary for the main HTML report. Each top-level entry is one CSV
# file in the output directory. Inner list = (column name, en meaning, zh meaning).
DATA_DICTIONARY = [
    (
        "rates_by_sol.csv",
        [
            ("scenario", "Scenario name (matches the inputs table).", "场景名（对应场景输入表）。"),
            ("sol", "Standard of Living, 0–35 (the report scans this range).", "生活水平，0–35（本报告扫描的范围）。"),
            ("effective_sol", "SoL after pollution penalty: max(0, SoL − 3·impact·(1+reduction)).", "扣除污染惩罚后的有效 SoL：max(0, SoL − 3·impact·(1+reduction))。"),
            ("birth_base_monthly", "Base monthly birth rate at effective_sol, before modifiers.", "effective_sol 下、未叠加修正前的基础月出生率。"),
            ("mortality_base_monthly", "Base monthly mortality at effective_sol, before modifiers.", "effective_sol 下、未叠加修正前的基础月死亡率。"),
            ("birth_mult_total", "Sum of all birth-rate multipliers active in the scenario.", "场景中所有出生率乘数之和。"),
            ("mortality_mult_total", "Sum of all mortality multipliers (incl. wealth, turmoil, pollution health).", "所有死亡率乘数之和（含财富、动乱、污染健康通道）。"),
            ("literacy_birth_mult", "−0.10 × literacy contribution to birth_mult_total.", "literacy_penalty 对 birth_mult_total 的贡献：−0.10 × 识字率。"),
            ("pollution_sol_penalty", "−3 × impact × (1+reduction): the SoL drop driving effective_sol.", "−3 × impact × (1+reduction)：导致 effective_sol 下降的 SoL 惩罚。"),
            ("pollution_mortality_mult", "0.5 × impact × (1+reduction): pollution's mortality contribution.", "0.5 × impact × (1+reduction)：污染对死亡率乘数的贡献。"),
            ("wealth_mortality_mult", "state_mortality_wealth_mult × wealth_used. Private-health channel.", "state_mortality_wealth_mult × wealth_used。私立医疗通道。"),
            ("wealth_used", "Wealth value plugged into wealth_mortality_mult (sol_to_wealth(SoL) when wealth_from_sol).", "代入 wealth_mortality_mult 的财富值（wealth_from_sol 时为 sol_to_wealth(SoL)）。"),
            ("turmoil_mortality_mult", "state_mortality_turmoil_mult × turmoil. Always 0 in default scenarios.", "state_mortality_turmoil_mult × 动乱值。默认场景中恒为 0。"),
            ("birth_monthly", "Final monthly birth rate after all multipliers, clamped to ≥0.", "经全部乘数后的最终月出生率，下限 0。"),
            ("mortality_monthly", "Final monthly mortality after all multipliers, clamped to ≥0.", "经全部乘数后的最终月死亡率，下限 0。"),
            ("net_monthly", "birth_monthly − mortality_monthly.", "birth_monthly − mortality_monthly。"),
            ("birth_annual", "birth_monthly × 12.", "birth_monthly × 12。"),
            ("mortality_annual", "mortality_monthly × 12.", "mortality_monthly × 12。"),
            ("net_annual", "net_monthly × 12.", "net_monthly × 12。"),
        ],
    ),
    (
        "net_growth_sensitivity.csv",
        [
            ("factor_group", "Sensitivity group: birth_multiplier / mortality_multiplier / literacy / pollution / healthcare / healthcare_pollution.", "敏感性分组：出生率 / 死亡率 / 识字 / 污染 / 医疗 / 医疗+污染。"),
            ("scenario", "Scenario name within the group (e.g. \"Public health\").", "组内场景名（如「公共医保」）。"),
            ("…", "Remaining columns identical to rates_by_sol.csv.", "其余列与 rates_by_sol.csv 一致。"),
        ],
    ),
    (
        "workforce_projection.csv",
        [
            ("scenario", "Scenario name.", "场景名。"),
            ("sol", "Fixed SoL used for the projection.", "投影使用的固定 SoL。"),
            ("month", "Month index, 0 to --months.", "月份索引，0 到 --months。"),
            ("year", "month / 12.", "month / 12。"),
            ("population", "Total state population at this step.", "本步州总人口。"),
            ("workforce", "Working-adult count.", "工作年龄人口数。"),
            ("dependents", "Dependent count (children + elderly).", "依赖人口数（儿童 + 老人）。"),
            ("workforce_ratio", "workforce / population.", "workforce / population。"),
            ("target_workforce_ratio", "WORKING_ADULT_RATIO_BASE + sum of state_working_adult_ratio_add.", "WORKING_ADULT_RATIO_BASE + state_working_adult_ratio_add 之和。"),
            ("effective_sol / wealth_used / birth_mult_total / mortality_mult_total", "Cached from adjusted_rates() at the projection SoL.", "在投影 SoL 下从 adjusted_rates() 缓存得到。"),
            ("birth_monthly / mortality_monthly", "Per-month rates used for the projection step.", "每月投影步使用的月率。"),
        ],
    ),
    (
        "workforce_sensitivity.csv",
        [
            ("factor_group", "One of birth_multiplier, mortality_multiplier, literacy, pollution, healthcare, healthcare_pollution, target_ratio, sol.", "出生 / 死亡 / 识字 / 污染 / 医疗 / 医疗+污染 / 目标比例 / SoL 之一。"),
            ("…", "Remaining columns identical to workforce_projection.csv.", "其余列与 workforce_projection.csv 一致。"),
        ],
    ),
    (
        "modifier_sources.csv",
        [
            ("key", "Modifier name (state_birth_rate_mult, state_mortality_mult, building_*_mortality_mult, …).", "修正键名。"),
            ("value", "Numeric value assigned at this location.", "该处赋值的数值。"),
            ("file", "Path under game/ where the assignment lives.", "赋值所在的 game/ 路径。"),
            ("line_number", "1-indexed line number inside the file.", "文件内的 1-indexed 行号。"),
            ("scope", "Up to 5 nested block names leading to the assignment, joined by \"> \".", "最多 5 层嵌套块名，用 「> 」连接。"),
            ("line", "Raw source line (stripped).", "原始源代码行（去除首尾空白）。"),
        ],
    ),
    (
        "modifier_source_summary.csv",
        [
            ("key", "Same as modifier_sources.key.", "同 modifier_sources.key。"),
            ("count", "Number of hits for this key across game/common.", "该键在 game/common 中出现的次数。"),
            ("file_count", "Number of distinct files containing the key.", "包含该键的文件数。"),
            ("min / max / sum", "Numeric min, max and sum across hits.", "数值最小 / 最大 / 求和。"),
        ],
    ),
    (
        "pollution_impact_examples.csv",
        [
            ("generated_pollution", "Continuous pollution generation in the state.", "州的持续污染生成量。"),
            ("arable_land", "Arable land of the state.", "州的可耕地。"),
            ("pollution_impact", "Steady-state impact: clamp(gen / (50 + 1.5·√arable) / 255, 0, 1).", "稳态 impact：clamp(gen / (50 + 1.5·√arable) / 255, 0, 1)。"),
        ],
    ),
    (
        "pollution_dynamics.csv",
        [
            ("label", "Friendly name of the (generation, arable) pair.", "(generation, arable) 组合的友好名。"),
            ("month / year", "Time step.", "时间步。"),
            ("generated_pollution / arable_land", "Inputs (constant per series).", "输入（每条序列内为常量）。"),
            ("target_impact", "Steady-state impact the trajectory approaches.", "轨迹趋近的稳态 impact。"),
            ("pollution_impact", "Current impact at this month.", "当月的 impact。"),
        ],
    ),
]


HEALTH_SYSTEM_LABELS = {
    "en": {
        "no_health": "No health system",
        "charitable": "Charitable health",
        "public": "Public health",
        "private": "Private health",
    },
    "zh": {
        "no_health": "无医疗制度",
        "charitable": "慈善医院",
        "public": "公共医保",
        "private": "私立医疗",
    },
}


WORKFORCE_LEVER_LABELS = {
    "en": {
        "baseline_target_50": "Baseline 50% target (no laws stacked, food off)",
        "workplace_only": "Women in the Workplace (−5% birth, +10% target)",
        "suffrage": "Women's Suffrage (−5% birth, +15% target)",
        "suffrage_unions": "Suffrage + 2× Trade-Union trait (+5% each)",
        "food_only": "Food company prosperity (+5% birth, 50% target)",
        "high_sol": "Counter-example: same 50% target but SoL 15 (slower!)",
        "all_combined": "Recommended: suffrage + unions + food, SoL 12 (birth nets to 0, target 50%)",
    },
    "zh": {
        "baseline_target_50": "基准：仅目标 50%（不叠加任何法律 / 食品公司）",
        "workplace_only": "女性工作（出生 −5%，目标 +10%）",
        "suffrage": "妇女选举（出生 −5%，目标 +15%）",
        "suffrage_unions": "选举 + 两层工会特质（每层 +5% 目标）",
        "food_only": "通用食品公司繁荣（出生 +5%，目标 50%）",
        "high_sol": "反例：同样目标 50% 但 SoL 15",
        "all_combined": "推荐：选举 + 工会 + 食品，SoL 12（出生抵消归零，目标 50%）",
    },
}


ANALYSIS_TEXT = {
    "en": {
        "html_lang": "en",
        "title": "Victoria 3 — Population and Workforce Mechanics: An Analysis",
        "source_line": (
            "Data source: {game_root}. This document is the narrative; "
            "the companion file <code>demography_report_en.html</code> in the "
            "same directory holds all raw data tables and figures, which "
            "regenerate with each game version."
        ),
        "intro_title": "Overview",
        "intro_body": (
            "This report examines several gameplay decisions in Victoria 3 "
            "that touch on population and the workforce ratio: choice of "
            "health-system law, the timing of the food company, paths to "
            "raise the workforce ratio, and the population cost of "
            "industrialisation. All numerical findings derive from the CSV "
            "outputs in the same directory; the companion data report holds "
            "the full set of tables and figures."
        ),

        "health_title": "Health-System Law",
        "health_body_p1": (
            "Public Health applies a flat −5% mortality multiplier and "
            "reduces pollution-health damage by an additional 15%. Charitable "
            "Health's corresponding values are −3% and −10%, weaker on both "
            "channels. Private Health uses a wealth-scaled mortality channel "
            "(coefficient −0.002); under the linear approximation "
            "<em>wealth = 1.5 × SoL</em>, its mortality reduction matches "
            "Public's −5% only at SoL ≥ {breakeven_sol}."
        ),
        "health_body_p2": (
            "Polluted contexts shift the picture. At 50% pollution impact, "
            "Public Health restores effective SoL by 0.75 versus Private's "
            "0.45; the 5% pollution-reduction gap manifests as "
            "{public_mort_50_sol20} annual mortality under Public at SoL 20 "
            "compared to {private_mort_50_sol20} under Private. Private "
            "outperforms Public only when state pollution remains below 25% "
            "and SoL stays above 20; in other contexts Public is the better "
            "default."
        ),
        "health_body_p3": (
            "Charitable Health functions as a transitional option before "
            "pharmaceuticals research completes. Its −10% pollution reduction "
            "is 5% behind Public's, and even Private outperforms it on raw "
            "mortality. Once Public Health is researched, Charitable Health "
            "should be replaced."
        ),
        "health_data_ref": (
            "The data report's <a href=\"demography_report_en.html#net-healthcare\">"
            "net-growth healthcare sensitivity chart (0% pollution)</a> and "
            "<a href=\"demography_report_en.html#net-healthcare_pollution\">"
            "50%-pollution variant</a> plot the four systems on a common axis. "
            "Without pollution, Public, Charitable, and Private nearly overlap "
            "above SoL 16; under 50% pollution the curves separate across the "
            "full SoL range, with Public above Private. The "
            "<a href=\"demography_report_en.html#wf-healthcare\">workforce-ratio "
            "sensitivity chart</a> shows the choice has little impact on the "
            "ratio itself; the difference accumulates in total population."
        ),

        "food_title": "Food Company",
        "food_body_p1": (
            "The food company's prosperity modifier is a +5% birth-rate "
            "multiplier, applied monthly once the company is prosperous. "
            "Hundred-year compounded effects: at SoL 15 the +{delta_15} "
            "annual-growth increment yields a state population of {mult_15} "
            "relative to the no-company baseline. SoL 10, where base birth "
            "rate is still at its maximum, sees a larger absolute gain and "
            "reaches {mult_10}. SoL 5 is near the natural-growth equilibrium, "
            "where lifting 0% to 0.27% net growth is the largest relative "
            "change; the multiplier is also {mult_5}."
        ),
        "food_data_ref": (
            "The data report's <a href=\"demography_report_en.html#net-birth_multiplier\">"
            "net-growth birth-rate-multiplier sensitivity chart</a> sweeps "
            "±10%. The +5% curve reads 2.69%/yr at SoL 15 versus the 2.50%/yr "
            "baseline, a +{delta_15} difference. Past SoL 25 all curves "
            "converge as base birth hits its floor. The "
            "<a href=\"demography_report_en.html#wf-birth_multiplier\">workforce "
            "sensitivity counterpart</a> shows the same +5% accelerates "
            "convergence by about 4 years from a 25% start."
        ),

        "ratio_title": "Raising the Workforce Ratio",
        "ratio_body_p1": (
            "The long-run upper bound is the sum of the working-adult ratio "
            "additive modifiers from laws and traits: Women in the Workplace "
            "+10%, Women's Suffrage +15%, and two ranks of the Trade Unions "
            "trait at +5% each, totalling +35% on the 25% base — an asymptote "
            "of 50% that the model cannot exceed."
        ),
        "ratio_body_p2": (
            "Convergence speed is driven by the birth rate. New pops are "
            "allocated to the workforce at the target ratio, so a higher "
            "birth rate pulls the current ratio toward target faster. The "
            "engine additionally applies a working-adult-ratio skew "
            "correction (maximum factor 2.0): when the current ratio lags "
            "target, mortality falls disproportionately on dependents, "
            "roughly doubling effective convergence."
        ),
        "ratio_body_p3": (
            "Under the same law stack, raising the ratio from 25% to 40% takes "
            "{years_sol12} years at SoL 12 but {years_sol15} years at SoL 15. "
            "SoL 12's base birth rate ({birth_sol12}/yr) exceeds SoL 15's "
            "({birth_sol15}/yr) by about 25%, and birth dominates convergence. "
            "Where workforce ratio is the priority, SoL is best held in the "
            "10–12 range."
        ),
        "ratio_body_p4": (
            "The food company pairs with the suffrage path: its +5% birth "
            "multiplier cancels the suffrage law's −5% birth penalty, "
            "leaving the birth channel at zero while the target keeps rising. "
            "Mortality multipliers have little effect on the ratio itself "
            "(numerator and denominator move together); trading births for "
            "lower mortality is not advisable."
        ),
        "ratio_data_ref_p1": (
            "Three workforce-sensitivity charts in the data report support these "
            "claims. The <a href=\"demography_report_en.html#wf-target_ratio\">"
            "target-ratio sensitivity chart</a> shows five curves converging to "
            "25 / 35 / 40 / 45 / 50%; each asymptote equals the law-stack sum, "
            "and no birth-rate or SoL change pushes a curve past its target."
        ),
        "ratio_data_ref_p2": (
            "The <a href=\"demography_report_en.html#wf-sol\">SoL sensitivity "
            "chart</a> covers SoL 5–25 with nine curves. SoL 10 and SoL 12 "
            "converge fastest, both reaching 40% within 16 years. SoL 5 lags "
            "(base mortality equals birth), and SoL 25 lags (base birth is at "
            "its floor). The relation between SoL and convergence speed is "
            "non-monotonic: the optimum is in the 10–12 band."
        ),
        "ratio_data_ref_p3": (
            "The <a href=\"demography_report_en.html#wf-birth_multiplier\">"
            "birth-rate sensitivity chart</a> and "
            "<a href=\"demography_report_en.html#wf-mortality_multiplier\">"
            "mortality-rate sensitivity chart</a> compare the two modifier "
            "channels side by side. Birth-rate curves spread across a 5-year "
            "time-to-target band; mortality-rate curves visually overlap. The "
            "population-index sub-chart on the same page shows +50% mortality "
            "leaves the ratio close to target while pulling the population "
            "index from ~1.5 to ~0.6 over 100 years. Births shift the ratio; "
            "mortality shifts population size."
        ),

        "industry_title": "Population Cost of Industrialisation",
        "industry_body_p1": (
            "Pollution reduces population through two channels: lowering "
            "effective SoL (up to −3) and inflating the mortality multiplier "
            "(up to +50%). Both channels are scaled by the pollution-health "
            "reduction multiplier from the active health system. The "
            "following 80-year projection from a SoL-14 baseline isolates "
            "the effect:"
        ),
        "industry_col_pollution": "Pollution",
        "industry_col_no_health": "No health (pop ×)",
        "industry_col_public": "Public health (pop ×)",
        "industry_col_uplift": "Public uplift",
        "industry_body_p2": (
            "At 50% pollution impact the final population is {loss_50}% "
            "below the 0%-pollution baseline. Public Health recovers "
            "approximately {uplift_50} of that gap, but does not close it. "
            "In industrial cores, switching to forestry or electric production "
            "methods and adding pollution-reduction infrastructure yields a "
            "larger population gain than Public Health alone; the latter "
            "should be treated as damage control rather than a primary remedy."
        ),
        "industry_data_ref": (
            "The data report's <a href=\"demography_report_en.html#section-pollution\">"
            "pollution section</a> contains the steady-state table and the "
            "transient curve. At the engine's default change speed, the time "
            "constant from zero to steady state is ~1000 months: a state "
            "generating 2000 pollution needs about 50 years to reach half of "
            "its steady-state impact, so early industrialisation pays less than "
            "the steady-state table suggests. The "
            "<a href=\"demography_report_en.html#net-pollution\">net-growth "
            "pollution sensitivity chart</a> isolates pollution's effect: 100% "
            "pollution flattens net growth across the entire SoL range, and "
            "0% versus 50% pollution costs about 0.8% at SoL 15."
        ),

        "famine_title": "Famine and Recovery",
        "famine_body_p1": (
            "The starvation penalty after engine scaling applies "
            "approximately −35% birth and +30% mortality. Five years of "
            "sustained partial starvation at SoL 8 reduces state population "
            "by {partial_loss}%, with recovery to pre-famine levels in about "
            "{partial_recover} years. The severe starvation penalty "
            "(−90% birth, +100% mortality) under identical conditions causes "
            "a {severe_loss}% loss requiring approximately {severe_recover} "
            "years to recover, a persistent demographic loss within this "
            "report's 30-year observation window."
        ),
        "famine_body_p2": (
            "Severe starvation warrants intervention before the event chain "
            "completes (decrees, grain redirection, tariff adjustment). "
            "Partial starvation is recoverable; resource expenditure on its "
            "mitigation may be reduced accordingly."
        ),

        "literacy_title": "Birth-Rate Cost of Literacy",
        "literacy_body_p1": (
            "The literacy penalty applies a birth-rate multiplier of −0.1 "
            "scaled linearly by pop literacy; full literacy reduces birth "
            "rate by 10%. In absolute terms: SoL 12 birth rate moves from "
            "{birth_12_lit0}/yr to {birth_12_lit1}/yr, a {drop_12}% drop; "
            "SoL 15 moves from {birth_15_lit0} to {birth_15_lit1}, a "
            "{drop_15}% drop."
        ),
        "literacy_body_p2": (
            "Relative to the productivity gains literacy enables — "
            "production-method unlocks, Intelligentsia political weight, "
            "upper-strata standard-of-living improvements — the birth-rate "
            "cost is small. Suppressing literacy to raise births is not "
            "advisable."
        ),
        "literacy_data_ref": (
            "The data report's <a href=\"demography_report_en.html#net-literacy\">"
            "net-growth literacy sensitivity chart</a> shows 0%–100% literacy "
            "as five parallel curves offset by the birth-rate penalty. The "
            "<a href=\"demography_report_en.html#wf-literacy\">workforce-ratio "
            "counterpart</a> shows all five curves still converging to the same "
            "50% target — literacy affects convergence speed, not the asymptote."
        ),

        "figures_pointer_title": "Raw Data",
        "figures_pointer_body": (
            "The complete set of raw data tables (scenario inputs, modifier "
            "scan, pollution steady state, data dictionary) and the full "
            "figure set is in the companion file "
            "<code>demography_report_en.html</code> in this directory. Both "
            "files regenerate from the same CSVs and therefore change with "
            "each game version."
        ),

        "limits_title": "Method Limits",
        "limits_body": (
            "<ol>"
            "<li>The engine's working-adult-ratio skew correction "
            "(maximum factor 2.0) lacks a documented script-side algorithm. "
            "This report approximates it with "
            "<code>skew = clamp(target / current, 1/2, 2)</code>; the "
            "divergence from the no-correction baseline is small and is "
            "quantified in the data report.</li>"
            "<li>SoL is held constant within each projection. In live game "
            "play SoL drifts with industrialisation, literacy and commodity "
            "prices. The CLI flags <code>--sol-start / --sol-end</code> "
            "enable a linear-trajectory mode.</li>"
            "<li>Pollution is modelled at steady state. The ramp from zero "
            "to steady state has a time constant near 1000 months (see the "
            "pollution-dynamics chart in the data report); early "
            "industrialisation pays less than the steady-state numbers "
            "imply.</li>"
            "<li>Private Health's wealth uses a 1.5 × SoL proxy. In game, "
            "pop wealth derives from income distributions; high-SoL states "
            "with concentrated wealth may exceed this estimate "
            "(strengthening Private), while majority-commoner states may "
            "fall below it.</li>"
            "<li>Not modelled: migration and immigration; occupational "
            "mortality multipliers (slaves, engineers, machinists); state "
            "traits such as epidemics and storms; per-strata effects.</li>"
            "</ol>"
        ),

        "label_birth": "birth",
        "label_mortality": "mortality",
        "label_natural_growth": "natural growth",
        "label_baseline": "without food company",
        "label_food_company": "with food company",
        "label_partial_starv": "partial starvation",
        "label_severe_starv": "severe starvation",
        "axis_sol": "Standard of Living",
        "axis_rate": "Annual rate",
        "axis_years": "Years",
        "axis_workforce": "Workforce ratio",
        "axis_net": "Annual net growth",
        "axis_pop_index": "Population index (initial = 1.0)",
        "chart_health_compare": "Annual net growth by SoL under each health system (0% pollution solid, 50% dashed)",
        "chart_food": "Annual net growth by SoL — with and without the food company",
        "chart_starvation": "Population trajectories: 5 years of famine followed by 30 years of recovery (SoL 8)",
        "chart_base_curves": "Base annual birth, mortality and natural growth by SoL",
        "col_pollution": "Pollution",
        "col_lever": "Policy combination",
        "col_target": "Target ratio",
        "col_birth_mod": "Birth rate modifier",
        "col_years_to_40": "Years to 40%",
        "col_years_to_45": "Years to 45%",
        "col_ratio_at_50y": "Ratio after 50 yr",
        "col_ratio_at_100y": "Ratio after 100 yr",
        "col_initial_ratio": "Initial ratio",
        "ratio_skew_para": (
            "The skew correction is the largest convergence accelerator in the "
            "model. At SoL 12, 25% → 50% path, no birth-rate modifier: with the "
            "correction the ratio reaches 40% in {skew_on_40} years; without it, "
            "{skew_off_40} years. At the 50-year mark the two trajectories "
            "differ by {skew_diff_40}%."
        ),
        "ratio_initial_para": (
            "Sweeping the initial ratio at constant law stack:"
        ),
        "ratio_initial_after": (
            "Starting 10% earlier saves 7–10 years on the way to 40%. The law "
            "stack still dominates: a state starting at 35% but capped at 35% "
            "target (no suffrage) stays at 35%."
        ),
        "ratio_birth_para": (
            "Birth-rate modifiers at fixed target shift convergence speed "
            "within a ±5-year band:"
        ),
        "ratio_birth_after": (
            "Each ±5% birth modifier moves time-to-40% by about 4 years. The "
            "food company's +5% by itself matches the convergence gain from "
            "passing one additional women's-rights law tier, because the "
            "modifier compounds across the full convergence window."
        ),
    },
    "zh": {
        "html_lang": "zh-CN",
        "title": "维多利亚 3 — 人口与劳动力机制分析",
        "source_line": (
            "数据来源：{game_root}。本文为分析正文；"
            "完整原始数据表与图表位于同目录下的配套文件 "
            "<code>demography_report_zh.html</code>，"
            "其内容随游戏版本变化而重新生成。"
        ),
        "intro_title": "概述",
        "intro_body": (
            "本报告分析 Victoria 3 中与人口及劳动力比例相关的若干玩法决策："
            "医疗法案的选择、通用食品公司的设立时机、劳动力比例的提升路径，"
            "以及工业化的人口代价。"
            "所有数值结论均来自同目录下的 CSV 输出；"
            "配套数据报告中列出完整的表格与图表。"
        ),

        "health_title": "医疗法案的选择",
        "health_body_p1": (
            "公共医保对死亡率施加 −5% 的固定乘数，并对污染健康损害额外减少 15%。"
            "慈善医院的对应数值为 −3% 与 −10%，两条通道均弱于公共医保。"
            "私立医疗使用按财富缩放的死亡率通道（系数 −0.002）；"
            "在「财富 = 1.5 × SoL」的线性近似下，"
            "其死亡率减免需 SoL 不低于 {breakeven_sol} 才能与公共医保相当。"
        ),
        "health_body_p2": (
            "公共医保还会带来 +0.5 SoL 的全州加成。50% 污染冲击下，"
            "+0.5 SoL 与 −15% 污染减免叠加使有效 SoL 仅净损 0.78；"
            "私立医疗只有 −10% 污染减免，有效 SoL 净损 1.35。"
            "SoL 20 时公共医保年死亡率为 {public_mort_50_sol20}，私立为 {private_mort_50_sol20}。"
            "公共医保在 SoL 25 以下区间优于私立；只有州内 wealth 增速持续高于 SoL，"
            "私立的 wealth-scaled 通道才可能追平。"
        ),
        "health_body_p3": (
            "慈善医院在药学研究完成前作为过渡选项。"
            "其 −10% 的污染减免低于公共医保 5%，原始死亡率减免亦不及私立医疗，"
            "公共医保研究完成后应替换。"
        ),
        "health_data_ref": (
            "数据报告的<a href=\"demography_report_zh.html#net-healthcare\">"
            "净增长 · 医疗制度敏感性图（0% 污染）</a>与"
            "<a href=\"demography_report_zh.html#net-healthcare_pollution\">"
            "50% 污染下的同图</a>把四套制度画在同一坐标系。"
            "无污染时公共医保、私立、慈善在 SoL 16 以上几乎重合，"
            "净增长差距不到 0.1%；50% 污染下四条曲线在整段 SoL 区间拉开，"
            "公共医保始终在私立之上。"
            "<a href=\"demography_report_zh.html#wf-healthcare\">"
            "劳动力比例 · 医疗制度敏感性图</a>下，"
            "医疗制度对比例本身影响有限，差异主要体现在总人口规模。"
        ),

        "food_title": "通用食品公司",
        "food_body_p1": (
            "通用食品公司的繁荣加成为 +5% 出生率乘数，"
            "在公司繁荣后按月生效。百年累计效应："
            "SoL 15 下年净增长率提升 {delta_15}，"
            "100 年后州人口达到无公司情形的 {mult_15}；"
            "SoL 10 因基础出生率仍处最大值，绝对收益更大，倍数 {mult_10}；"
            "SoL 5 接近自然增长平衡点，0% 净增长被拉至 0.27%，"
            "相对变化最大，倍数同样为 {mult_5}。"
        ),
        "food_data_ref": (
            "数据报告的<a href=\"demography_report_zh.html#net-birth_multiplier\">"
            "净增长 · 出生率乘数敏感性图</a>给出 ±10% 完整扫描。"
            "+5% 曲线在 SoL 15 处读数 2.69%/年，基准 2.50%/年，差 +{delta_15}。"
            "SoL 25 以后所有曲线收敛于同一速率，因为基础出生率已触底。"
            "<a href=\"demography_report_zh.html#wf-birth_multiplier\">"
            "劳动力比例 · 出生率乘数敏感性图</a>下，同样 +5% 把从 25% 起步的收敛时间缩短约 4 年。"
        ),

        "ratio_title": "劳动力比例的提升路径",
        "ratio_body_p1": (
            "长期上限为法律与特性贡献的工作年龄比例加成之和："
            "女性工作 +10%、妇女选举 +15%、"
            "工会两层特性各 +5%，在 25% 基础上累计 50%，"
            "即模型的渐近线。"
        ),
        "ratio_body_p2": (
            "劳动力比例的收敛速度由出生率主导。"
            "新生人口按目标比例分配至工作年龄，"
            "出生率越高，当前比例向目标的拉动越快。"
            "引擎附带工作年龄比例偏移修正（上限因子 2.0）："
            "当前比例低于目标时，死亡率向依赖人口倾斜，"
            "等效将收敛速度再加倍。"
        ),
        "ratio_body_p3": (
            "相同法律组合下，"
            "SoL 12 时从 25% 提升至 40% 需 {years_sol12} 年，"
            "SoL 15 需 {years_sol15} 年。"
            "SoL 12 的基础出生率（{birth_sol12}/年）"
            "较 SoL 15（{birth_sol15}/年）高约 25%，"
            "比例收敛由出生率驱动。"
            "劳动力比例优先时，SoL 应稳定在 10–12 区间。"
        ),
        "ratio_body_p4": (
            "通用食品公司的 +5% 出生率乘数可抵消选举法律的 −5% 出生率乘数，"
            "出生率通道净零的同时目标比例继续上升。"
            "死亡率乘数对劳动力比例本身影响有限（分子分母同向变化），"
            "不宜以降低死亡率为代价牺牲出生率。"
        ),
        "ratio_data_ref_p1": (
            "数据报告三张劳动力敏感性图直接支持上述结论。"
            "<a href=\"demography_report_zh.html#wf-target_ratio\">劳动力比例 · 目标比例敏感性图</a>"
            "的五条曲线分别收敛到 25 / 35 / 40 / 45 / 50%，每条渐近线即对应法律堆叠之和。"
            "出生率或 SoL 的变动不能跨过曲线自身的目标上限。"
        ),
        "ratio_data_ref_p2": (
            "<a href=\"demography_report_zh.html#wf-sol\">劳动力比例 · SoL 敏感性图</a>"
            "覆盖 SoL 5–25 共九条曲线。"
            "SoL 10、12 收敛最快，16 年内到 40%；"
            "SoL 5 滞后（基础死亡率与出生率持平），"
            "SoL 25 滞后（基础出生率触底）。"
            "收敛速度与 SoL 之间为非单调关系，最快区间在 SoL 10–12。"
        ),
        "ratio_data_ref_p3": (
            "<a href=\"demography_report_zh.html#wf-birth_multiplier\">劳动力比例 · 出生率乘数敏感性图</a>"
            "与<a href=\"demography_report_zh.html#wf-mortality_multiplier\">死亡率乘数敏感性图</a>"
            "并列对比两条修正通道。出生率曲线在 5 年时间带内分散，死亡率曲线几乎重叠。"
            "同页下方的<em>人口指数副图</em>显示，"
            "+50% 死亡率几乎不动比例，但 100 年内把人口指数从约 1.5 拉到 0.6。"
            "出生率改变比例，死亡率改变人口规模。"
        ),

        "industry_title": "工业化的人口代价",
        "industry_body_p1": (
            "污染通过两条通道削减人口：拉低有效 SoL（最多 −3）"
            "与提升死亡率乘数（最多 +50%）。"
            "两条通道均按当前医疗制度的污染健康减免乘数缩放。"
            "下表为 SoL 14 起始州 80 年人口投影的对照："
        ),
        "industry_col_pollution": "污染",
        "industry_col_no_health": "无医疗（人口倍数）",
        "industry_col_public": "公共医保（人口倍数）",
        "industry_col_uplift": "公立提升",
        "industry_body_p2": (
            "50% 污染冲击下，州人口较 0% 污染情形减少 {loss_50}%，"
            "公共医保可挽回其中约 {uplift_50}，但缺口无法完全弥补。"
            "工业核心州中，切换至林业 / 电气化生产方式及部署减污染建筑"
            "较单纯依赖公共医保更为有效；"
            "公共医保的角色为损害控制而非根本解决。"
        ),
        "industry_data_ref": (
            "数据报告的<a href=\"demography_report_zh.html#section-pollution\">污染节</a>"
            "包含稳态参考表（污染生成、可耕地 → 长期 impact）与瞬态曲线。"
            "按引擎默认变化速率，从 0 涨到稳态的时间常数约 1000 月："
            "污染生成 2000 的州约需 50 年达到稳态 impact 的一半，"
            "因此开荒前 50 年的人口代价低于稳态值。"
            "<a href=\"demography_report_zh.html#net-pollution\">净增长 · 污染敏感性图</a>"
            "孤立出污染的影响：100% 污染下整段 SoL 区间的净增长曲线几乎被压平；"
            "0% 与 50% 污染在 SoL 15 处相差约 0.8%。"
        ),

        "famine_title": "饥荒与恢复",
        "famine_body_p1": (
            "饥荒惩罚经引擎缩放后约为出生 −35% / 死亡 +30%。"
            "SoL 8 下持续 5 年导致州人口下降 {partial_loss}%，"
            "结束后约 {partial_recover} 年恢复至饥荒前规模。"
            "严重饥荒惩罚（−90% / +100%）"
            "在相同条件下 5 年损失 {severe_loss}%，"
            "需约 {severe_recover} 年方能恢复，"
            "在 30 年观察窗口内构成持久性人口损失。"
        ),
        "famine_body_p2": (
            "严重饥荒应在事件链完成前优先处理；"
            "普通饥荒具备自愈能力，资源投入可适度降低。"
        ),

        "literacy_title": "识字率的隐性成本",
        "literacy_body_p1": (
            "识字率惩罚施加 −0.1 的出生率乘数，"
            "按人口识字率线性缩放，满识字率对应出生率下降 10%。"
            "绝对百分值：SoL 12 由 {birth_12_lit0}/年降至 {birth_12_lit1}/年，"
            "下降 {drop_12}%；"
            "SoL 15 由 {birth_15_lit0} 降至 {birth_15_lit1}，下降 {drop_15}%。"
        ),
        "literacy_body_p2": (
            "与识字率带来的收益相比，该出生率损失影响有限，"
            "因此不宜以压低识字率换取出生率提升。"
        ),
        "literacy_data_ref": (
            "数据报告的<a href=\"demography_report_zh.html#net-literacy\">"
            "净增长 · 识字率敏感性图</a>把 0%–100% 识字率画成五条几乎平行的曲线，"
            "纵向间距对应出生率惩罚。"
            "<a href=\"demography_report_zh.html#wf-literacy\">"
            "劳动力比例 · 识字率敏感性图</a>下，五条曲线最终都收敛到 50% 目标，"
            "识字率影响收敛速度但不改变终点。"
        ),

        "figures_pointer_title": "原始数据",
        "figures_pointer_body": (
            "完整原始数据表（场景定义、修正源扫描、污染稳态、数据字典）"
            "及全部图表位于同目录下的配套文件 "
            "<code>demography_report_zh.html</code>。"
            "两份文件均自相同的 CSV 重生成，因此随每个游戏版本而变化。"
        ),

        "limits_title": "方法局限",
        "limits_body": (
            "<ol>"
            "<li>引擎中的工作年龄比例偏移修正（上限因子 2.0）"
            "缺少完整的脚本侧公开算法。"
            "本文采用 <code>skew = clamp(target / current, 1/2, 2)</code> 近似；"
            "其与无修正模型的差异较小，量化结果见配套数据报告。</li>"
            "<li>SoL 在每次投影内为固定值；"
            "真实游戏中 SoL 随工业化、识字率与商品价格变化。"
            "CLI 选项 <code>--sol-start / --sol-end</code> 可启用线性轨迹模式。</li>"
            "<li>污染按稳态建模。真实污染从零到稳态的时间常数约为 1000 月"
            "（参见配套数据报告中的污染瞬态曲线）；"
            "开荒期的人口代价低于稳态数值。</li>"
            "<li>私立医疗的财富估算采用 1.5 × SoL 线性映射。"
            "真实游戏中人口财富来自收入分布，"
            "高 SoL 富裕州可能高于该估计（私立效果更强），"
            "平民为主的州可能低于该估计。</li>"
            "<li>未建模：迁徙与移民、奴隶 / 工程师 / 机械工的职业死亡率乘数、"
            "地区特性（疫情、风暴）、阶层差异。</li>"
            "</ol>"
        ),

        "label_birth": "出生率",
        "label_mortality": "死亡率",
        "label_natural_growth": "自然增长率",
        "label_baseline": "无食品公司",
        "label_food_company": "有食品公司",
        "label_partial_starv": "部分饥荒",
        "label_severe_starv": "严重饥荒",
        "axis_sol": "生活水平",
        "axis_rate": "年度比例",
        "axis_years": "年",
        "axis_workforce": "劳动力比例",
        "axis_net": "年度自然增长率",
        "axis_pop_index": "人口指数（起始 = 1.0）",
        "chart_health_compare": "各医疗制度下的年度净增长率随 SoL 变化（0% 污染实线，50% 虚线）",
        "chart_food": "年度净增长率随 SoL 变化 —— 有 / 无通用食品公司对照",
        "chart_starvation": "5 年饥荒后 30 年恢复的人口轨迹（SoL 8）",
        "chart_base_curves": "按 SoL 绘制的基础年度出生率、死亡率与自然增长率",
        "col_pollution": "污染",
        "col_lever": "组合方案",
        "col_target": "目标比例",
        "col_birth_mod": "出生率乘数",
        "col_years_to_40": "到 40% 年数",
        "col_years_to_45": "到 45% 年数",
        "col_ratio_at_50y": "50 年后比例",
        "col_ratio_at_100y": "100 年后比例",
        "col_initial_ratio": "初始比例",
        "ratio_skew_para": (
            "skew 修正是模型中最大的收敛加速通道。"
            "SoL 12、25% → 50% 路径、无出生率乘数的基准下，"
            "启用修正 {skew_on_40} 年达到 40%，"
            "关闭修正 {skew_off_40} 年；"
            "50 年时刻两条轨迹相差 {skew_diff_40}%。"
        ),
        "ratio_initial_para": (
            "在固定法律组合下扫描初始劳动力比例："
        ),
        "ratio_initial_after": (
            "初始比例每提前 10%，到 40% 的时间缩短 7–10 年。"
            "法律堆叠仍是主导因素：起始 35% 但目标上限 35%（未通过妇女选举）"
            "的州停在 35%。"
        ),
        "ratio_birth_para": (
            "目标比例固定下，出生率乘数扫描显示 ±5 年的收敛带宽："
        ),
        "ratio_birth_after": (
            "每 ±5% 的出生率乘数将到 40% 的时间挪动约 4 年。"
            "单独开通用食品（+5%）带来的收敛收益约等于"
            "再通过一档女权法律层级，因为该乘数在整个收敛窗口内复利。"
        ),
    },
}


def tr_label(label: str, language: str) -> str:
    if language == "zh":
        return LABEL_TRANSLATIONS_ZH.get(label, label)
    return label


def tr_note(scenario, language: str) -> str:
    if language == "zh":
        return NOTE_TRANSLATIONS_ZH.get(scenario.name, scenario.notes)
    return scenario.notes
