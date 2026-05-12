"""Centralized UI string translations.

The tool's UI (sheet names, column headers, bucket labels, notes labels)
auto-switches between Chinese (zh) and English (en) based on the game-data
language passed to `--lang`:

    simp_chinese  → zh UI
    everything else (english/french/german/...) → en UI

Game data names (buildings, PMs, goods) always come from the corresponding
game localization files. Only the tool's own chrome is in this module.
"""
from __future__ import annotations
from dataclasses import dataclass


def ui_lang_for(game_lang: str) -> str:
    return "zh" if game_lang == "simp_chinese" else "en"


# All translatable strings. Add new keys here, then add both translations.
_TRANSLATIONS: dict[str, dict[str, str]] = {
    # --- Sheet names ---
    "sheet_info":          {"zh": "信息",     "en": "Info"},
    "sheet_overview":      {"zh": "总览",     "en": "Overview"},
    "sheet_construction":  {"zh": "建造部门", "en": "Construction Sectors"},
    "sheet_diff_added_combo":     {"zh": "新增-组合", "en": "Added-Combo"},
    "sheet_diff_removed_combo":   {"zh": "移除-组合", "en": "Removed-Combo"},
    "sheet_diff_changed_combo":   {"zh": "变更-组合", "en": "Changed-Combo"},
    "sheet_diff_added_constr":    {"zh": "新增-建造", "en": "Added-Construction"},
    "sheet_diff_removed_constr":  {"zh": "移除-建造", "en": "Removed-Construction"},
    "sheet_diff_changed_constr":  {"zh": "变更-建造", "en": "Changed-Construction"},

    # --- Combo row column headers ---
    "col_building":        {"zh": "建筑",            "en": "Building"},
    "col_base_pms":        {"zh": "基础生产方式",    "en": "Base PM"},
    "col_secondary_pms":   {"zh": "次要生产方式",    "en": "Secondary PM"},
    "col_automation_pms":  {"zh": "自动化生产方式",  "en": "Automation PM"},
    "col_ownership_pms":   {"zh": "默认所有权",      "en": "Default Ownership"},
    "col_output_value":    {"zh": "产出价值",        "en": "Output Value"},
    "col_input_value":     {"zh": "投入价值",        "en": "Input Value"},
    "col_net_value":       {"zh": "利润",            "en": "Profit"},
    "col_construction":    {"zh": "建造力",          "en": "Construction"},
    "col_employment":      {"zh": "劳动力",          "en": "Employment"},
    "col_wage_mult":       {"zh": "工资倍率",        "en": "Wage Multiplier"},
    "col_roi":             {"zh": "建造力回报率",    "en": "Construction ROI"},
    "col_per_capita":      {"zh": "人均年产值",      "en": "Annual Per-Capita Profit"},
    "col_building_group":  {"zh": "建筑分组",        "en": "Building Group"},
    "col_inputs_str":      {"zh": "投入",            "en": "Inputs"},
    "col_outputs_str":     {"zh": "产出",            "en": "Outputs"},
    "col_notes":           {"zh": "备注",            "en": "Notes"},
    "col_building_id":     {"zh": "建筑ID",          "en": "Building ID"},
    "col_base_ids":        {"zh": "基础_ID",         "en": "Base_ID"},
    "col_secondary_ids":   {"zh": "次要_ID",         "en": "Secondary_ID"},
    "col_automation_ids":  {"zh": "自动化_ID",       "en": "Automation_ID"},
    "col_ownership_ids":   {"zh": "所有权_ID",       "en": "Ownership_ID"},

    # --- Construction sheet column headers (key suffix matches dataclass field) ---
    "ccol_building":               {"zh": "建造部门",                 "en": "Construction Sector"},
    "ccol_pm":                     {"zh": "生产方式",                 "en": "Method"},
    "ccol_inputs_str":             {"zh": "投入",                     "en": "Inputs"},
    "ccol_construction_per_lvl":   {"zh": "建造力 / 级",              "en": "Construction / Level"},
    "ccol_employment":             {"zh": "劳动力 / 级",              "en": "Employment / Level"},
    "ccol_wage_mult":              {"zh": "工资倍率",                 "en": "Wage Multiplier"},
    "ccol_material_cost_per_lvl":  {"zh": "物料成本 / 级",            "en": "Material Cost / Level"},
    "ccol_wage_cost_per_lvl":      {"zh": "工资支出 / 级（wage_weight×员工）", "en": "Wage Cost / Level (wage_weight×emp)"},
    "ccol_material_cost_per_unit": {"zh": "物料成本 / 建造力",        "en": "Material Cost / Construction"},
    "ccol_wage_cost_per_unit":     {"zh": "工资支出 / 建造力",        "en": "Wage Cost / Construction"},
    "ccol_total_cost_per_unit":    {"zh": "综合成本 / 建造力",        "en": "Total Cost / Construction"},
    "ccol_building_id":            {"zh": "建筑ID",                   "en": "Building ID"},
    "ccol_pm_id":                  {"zh": "PM_ID",                    "en": "PM_ID"},

    # --- Bucket names (sheet-per-category) ---
    "bucket_agriculture":  {"zh": "农业",       "en": "Agriculture"},
    "bucket_plantations":  {"zh": "种植园",     "en": "Plantations"},
    "bucket_extraction":   {"zh": "开采业",     "en": "Extraction"},
    "bucket_manufacturing":{"zh": "制造业",     "en": "Manufacturing"},
    "bucket_service":      {"zh": "服务业",     "en": "Service"},
    "bucket_infrastructure":{"zh": "基础设施", "en": "Infrastructure"},
    "bucket_government":   {"zh": "政府",       "en": "Government"},
    "bucket_military":     {"zh": "军政",       "en": "Military"},
    "bucket_monuments":    {"zh": "纪念物",     "en": "Monuments"},
    "bucket_other":        {"zh": "其他",       "en": "Other"},

    # --- Categories (used in code logic; rendered for ownership column etc.) ---
    "cat_base":            {"zh": "基础",       "en": "Base"},
    "cat_secondary":       {"zh": "次要",       "en": "Secondary"},
    "cat_automation":      {"zh": "自动化",     "en": "Automation"},
    "cat_ownership":       {"zh": "所有权",     "en": "Ownership"},

    # --- Info-sheet meta labels ---
    "meta_title":          {"zh": "V3_EMA 报告",   "en": "V3_EMA Report"},
    "meta_game_version":   {"zh": "游戏版本",       "en": "Game Version"},
    "meta_raw_version":    {"zh": "数据版本",       "en": "Raw Version"},
    "meta_generated_at":   {"zh": "生成时间",       "en": "Generated At"},
    "meta_tool_version":   {"zh": "工具版本",       "en": "Tool Version"},
    "meta_data_lang":      {"zh": "数据语言",       "en": "Data Language"},
    "meta_ui_lang":        {"zh": "界面语言",       "en": "UI Language"},
    "meta_unknown":        {"zh": "(未知)",         "en": "(unknown)"},
    "count_goods":         {"zh": "商品数",         "en": "Goods Count"},
    "count_pops":          {"zh": "工种数",         "en": "Pop Types Count"},
    "count_pms":           {"zh": "生产方式数",     "en": "PM Count"},
    "count_pmgs":          {"zh": "生产方式组数",   "en": "PMG Count"},
    "count_buildings":     {"zh": "建筑数",         "en": "Building Count"},
    "count_bgs":           {"zh": "建筑分组数",     "en": "Building Group Count"},
    "count_combo_rows":    {"zh": "组合行",         "en": "Combo Rows"},
    "count_construction_rows": {"zh": "建造部门行", "en": "Construction Rows"},

    # --- Diff info-sheet labels ---
    "diff_title":          {"zh": "V3_EMA 差异报告",   "en": "V3_EMA Diff Report"},
    "diff_old_game":       {"zh": "旧版本游戏",         "en": "Old Game Version"},
    "diff_old_generated":  {"zh": "旧版本生成于",       "en": "Old Generated At"},
    "diff_new_game":       {"zh": "新版本游戏",         "en": "New Game Version"},
    "diff_new_generated":  {"zh": "新版本生成于",       "en": "New Generated At"},
    "diff_compared_at":    {"zh": "比较时间",           "en": "Compared At"},
    "diff_combo_added":    {"zh": "组合 · 新增",        "en": "Combo · Added"},
    "diff_combo_removed":  {"zh": "组合 · 移除",        "en": "Combo · Removed"},
    "diff_combo_changed":  {"zh": "组合 · 变更",        "en": "Combo · Changed"},
    "diff_constr_added":   {"zh": "建造 · 新增",        "en": "Construction · Added"},
    "diff_constr_removed": {"zh": "建造 · 移除",        "en": "Construction · Removed"},
    "diff_constr_changed": {"zh": "建造 · 变更",        "en": "Construction · Changed"},
    "diff_old_suffix":     {"zh": "·旧",                "en": " · Old"},
    "diff_new_suffix":     {"zh": "·新",                "en": " · New"},
    "diff_delta_suffix":   {"zh": "·Δ",                 "en": " · Δ"},
    "diff_rank":           {"zh": "排名",               "en": "Rank"},
    "diff_combo":          {"zh": "组合",               "en": "Combination"},

    # --- Notes phrases ---
    "notes_passive":       {"zh": "无生产",     "en": "no production"},
    "notes_separator":     {"zh": " | ",        "en": " | "},

    # --- Modifier labels (for pm_notes formatting) ---
    "mod_prestige":        {"zh": "威望",                "en": "Prestige"},
    "mod_authority":       {"zh": "权威",                "en": "Authority"},
    "mod_authority_pct":   {"zh": "权威%",               "en": "Authority %"},
    "mod_influence":       {"zh": "影响力",              "en": "Influence"},
    "mod_bureaucracy":     {"zh": "官僚",                "en": "Bureaucracy"},
    "mod_bureaucracy_pct": {"zh": "官僚%",               "en": "Bureaucracy %"},
    "mod_construction":    {"zh": "建造力",              "en": "Construction"},
    "mod_loan_rate":       {"zh": "国债利率",            "en": "Loan Interest Rate"},
    "mod_loan_rate_pct":   {"zh": "国债利率%",           "en": "Loan Interest Rate %"},
    "mod_legitimacy":      {"zh": "合法性",              "en": "Legitimacy"},
    "mod_max_interests":   {"zh": "声索数上限",          "en": "Max Declared Interests"},
    "mod_aristo_pol":      {"zh": "贵族政治影响%",       "en": "Aristocrat Political Strength %"},
    "mod_capi_pol":        {"zh": "资本家政治影响%",     "en": "Capitalist Political Strength %"},
    "mod_clergy_pol":      {"zh": "圣职者政治影响%",     "en": "Clergymen Political Strength %"},
    "mod_intel_pol":       {"zh": "知识分子政治影响%",   "en": "Intelligentsia Political Strength %"},
    "mod_decree_cost":     {"zh": "敕令成本%",           "en": "Decree Cost %"},
    "mod_pollution":       {"zh": "污染",                "en": "Pollution"},
    "mod_radicals_sol":    {"zh": "激进化(SoL)%",        "en": "Radicals from SoL %"},
    "mod_loyalists_sol":   {"zh": "保皇化(SoL)%",        "en": "Loyalists from SoL %"},
    "mod_birth_rate":      {"zh": "出生率%",             "en": "Birth Rate %"},
    "mod_mortality":       {"zh": "死亡率%",             "en": "Mortality %"},
    "mod_high_sol":        {"zh": "高 SoL 上限",         "en": "High SoL Cap"},
    "mod_throughput":      {"zh": "产能",                "en": "Throughput"},
    "mod_throughput_pct":  {"zh": "产能%",               "en": "Throughput %"},
    "mod_production_pct":  {"zh": "产出%",               "en": "Production %"},
    "mod_input_pct":       {"zh": "投入%",               "en": "Input %"},

    # --- Region report ---
    "rsheet_overview":        {"zh": "总览",         "en": "Overview"},
    "rcol_state":             {"zh": "地区",         "en": "State"},
    "rcol_state_id":          {"zh": "地区ID",       "en": "State ID"},
    "rcol_strategic_region":  {"zh": "战略大区",     "en": "Strategic Region"},
    "rcol_arable_land":       {"zh": "可耕地",       "en": "Arable Land"},
    "rcol_arable_buildings":  {"zh": "可耕作建筑",   "en": "Arable Buildings"},
    "rcol_capped_resources":  {"zh": "上限资源",     "en": "Capped Resources"},
    "rcol_capped_total":      {"zh": "资源上限",     "en": "Resource Cap"},
    "rcol_discoverable":      {"zh": "可发现资源",   "en": "Discoverable Resources"},
    "rcol_known_resources":   {"zh": "已知资源",     "en": "Known Resources"},
    "rcol_traits":            {"zh": "地区特性",     "en": "State Traits"},
    "rcol_trait_modifiers":   {"zh": "特性加成",     "en": "Trait Modifiers"},
    "rcol_resource_kinds":    {"zh": "资源种类数",   "en": "Resource Kinds"},
    "rcol_total_capacity":    {"zh": "总潜能",       "en": "Total Potential"},
    "rcol_subsistence":       {"zh": "生存建筑",     "en": "Subsistence Building"},
    "rcol_provinces":         {"zh": "省份数",       "en": "Province Count"},
    "rcol_numeric_id":        {"zh": "编号",         "en": "Numeric ID"},
    "rcol_traits_ids":        {"zh": "特性_ID",      "en": "Trait_IDs"},
    "rcol_strat_id":          {"zh": "战略大区_ID",  "en": "Strategic Region_ID"},
    "totals_label":           {"zh": "合计",         "en": "Total"},
    "pot_suffix":             {"zh": "（潜）",       "en": " (potential)"},

    # Region report bucket sheet names by continent
    "rbucket_western_europe":  {"zh": "西欧",       "en": "Western Europe"},
    "rbucket_southern_europe": {"zh": "南欧",       "en": "Southern Europe"},
    "rbucket_northern_europe": {"zh": "北欧",       "en": "Northern Europe"},
    "rbucket_eastern_europe":  {"zh": "东欧",       "en": "Eastern Europe"},
    "rbucket_north_america":   {"zh": "北美",       "en": "North America"},
    "rbucket_south_america":   {"zh": "南美",       "en": "South America"},
    "rbucket_central_america": {"zh": "中美",       "en": "Central America"},
    "rbucket_africa":          {"zh": "非洲",       "en": "Africa"},
    "rbucket_middle_east":     {"zh": "中东",       "en": "Middle East"},
    "rbucket_central_asia":    {"zh": "中亚",       "en": "Central Asia"},
    "rbucket_india":           {"zh": "印度",       "en": "India"},
    "rbucket_east_asia":       {"zh": "东亚",       "en": "East Asia"},
    "rbucket_southeast_asia":  {"zh": "东南亚",     "en": "Southeast Asia"},
    "rbucket_oceania":         {"zh": "大洋洲",     "en": "Oceania"},
    "rbucket_other":           {"zh": "其他",       "en": "Other"},

    # Region diff sheet names
    "rsheet_diff_added":       {"zh": "新增-地区",  "en": "Added-State"},
    "rsheet_diff_removed":     {"zh": "移除-地区",  "en": "Removed-State"},
    "rsheet_diff_changed":     {"zh": "变更-地区",  "en": "Changed-State"},
    "rcount_states":           {"zh": "地区数",     "en": "State Count"},
    "rcount_state_traits":     {"zh": "特性数",     "en": "Trait Count"},
    "rcount_strategic_regions":{"zh": "战略大区数", "en": "Strategic Region Count"},

    # IG short names (for interest_group_ig_<name>_pol_str_mult etc.)
    "ig_devout":           {"zh": "虔信派",     "en": "Devout"},
    "ig_rural_folk":       {"zh": "乡野庶民",   "en": "Rural Folk"},
    "ig_intelligentsia":   {"zh": "知识分子",   "en": "Intelligentsia"},
    "ig_industrialists":   {"zh": "实业家",     "en": "Industrialists"},
    "ig_armed_forces":     {"zh": "武装力量",   "en": "Armed Forces"},
    "ig_petite_bourgeoisie":{"zh": "小资产",    "en": "Petite Bourgeoisie"},
    "ig_trade_unions":     {"zh": "工会",       "en": "Trade Unions"},
    "ig_landowners":       {"zh": "地主",       "en": "Landowners"},
    "ig_pol_suffix":       {"zh": "政治影响%",  "en": " Political Strength %"},
    "ig_app_suffix":       {"zh": "支持",       "en": " Approval"},
}


@dataclass
class UI:
    """A view of the translation table for one UI language."""
    lang: str

    def __getitem__(self, key: str) -> str:
        entry = _TRANSLATIONS.get(key)
        if entry is None:
            return key
        return entry.get(self.lang) or entry.get("en") or key


def get_ui(game_lang: str) -> UI:
    return UI(lang=ui_lang_for(game_lang))


# Reverse maps: given a label string, what canonical key did it come from?
# Used by diff to interpret xlsx headers regardless of which language they were
# written in. Built lazily on first access.
_LABEL_TO_KEY_CACHE: dict[str, str] | None = None


def label_to_key(label: str) -> str | None:
    """Map a translated label back to its canonical key. Used by diff to read
    xlsx files written in either zh or en."""
    global _LABEL_TO_KEY_CACHE
    if _LABEL_TO_KEY_CACHE is None:
        m: dict[str, str] = {}
        for key, langs in _TRANSLATIONS.items():
            for _lang, label_value in langs.items():
                if label_value not in m:
                    m[label_value] = key
        _LABEL_TO_KEY_CACHE = m
    return _LABEL_TO_KEY_CACHE.get(label)
