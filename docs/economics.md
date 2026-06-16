# V3 经济学原理与计算假设

**中文** | [English](economics.en.md)

本文档面向使用 V3_EAT 进行经济分析的研究者，简述 Victoria 3 的经济运行机制，并明确 V3_EAT 在工具计算中所采用的简化假设。所有指标定义以本文档为准；具体实现见 `v3_eat/analysis/`。

## 1. 时间尺度（Tick Model）

V3 引擎以**周（week）**为最小经济结算单位，1 年 = 52 周。所有经济流（投入、产出、工资、利润）默认以「单位时间 = 周」为底。

V3_EAT 报表中：
- 「产出价值」「投入价值」「利润」均为**周值**（与游戏 tooltip 一致）。
- 「人均年产值」为**年化值**：`profit × 52 / employment`，对齐游戏 tooltip 中「人均产值」字样的口径。
- 「建造力回报率」`= profit / construction_cost`，量纲为「周利润 / 单位建造力」，是横向比较投资性价比的不变量。

## 2. 建筑层级与生产方式槽位

```
buildings (114)
  └── production_method_groups (197)
        └── production_methods (436)
```

每个建筑同时绑定多个 PMG（生产方式组）。每个 PMG 在每一时刻**有且仅有 1 个 PM 处于激活状态**。因此一个建筑的实际经济运行状态由所有 PMG 的当前选择共同决定 —— 即笛卡尔积 `∏_{pmg} |PMs(pmg)|` 的一个具体点。

V3_EAT 显式枚举此空间（去除「所有权」类 PMG 后约 1568 个组合行），用以回答：「这个建筑在某个具体配置下经济产出如何？」

PMG 的角色由命名前缀推导：
- `pmg_base_*` → 基础（每建筑一组）
- `pmg_secondary_*`、`pmg_canning`、`pmg_distillery` 等 → 次要（可有多组）
- `pmg_automation_*`、`pmg_harvesting_process_*`、`pmg_train_automation_*` → 自动化（可有多组）
- `pmg_ownership_*`、`pmg_serfdom` → 所有权（**不参与经济组合**，对产出无影响）

## 3. 修饰器尺度（Modifier Scaling）

PM 文件在 `building_modifiers` 块下用三种尺度声明效应：

| 尺度 | 含义 | 例 |
|---|---|---|
| `workforce_scaled` | 与现役劳动力人数线性 | `goods_output_grain_add = 20`：满员 1 级建筑每周产 20 谷物 |
| `level_scaled` | 与建筑等级线性 | `building_employment_laborers_add = 4000`：每级雇 4000 工人 |
| `unscaled` | 与等级无关，建筑级别独立 | `building_laborers_mortality_mult = 0.3` |

V3_EAT 假设建筑**1 级且满员**，此时 workforce_scaled 数值即为该 PM 对建筑的实际贡献。

## 4. 商品定价（Goods Pricing）

每种商品在 `common/goods/00_goods.txt` 中定义 `cost`（基础价）。游戏内运行时实际价格 = `cost × 供需扩张系数`，扩张系数随省份/国家供需失衡浮动于 [0.25, 1.75] 区间。

**A1（简化公理）**：V3_EAT 始终以 `cost` 计价，不模拟动态市场。后果：
- 报表对「**比较两个建筑的相对优劣**」无偏（rank ordering 保持），只要对比双方面对相似的市场条件；
- 对「**绝对利润数值**」有偏 —— 实际游戏中过剩商品价格下跌会使产出价值缩水。

## 5. 工资形成（Wage Formation）

V3 工资逻辑：建筑的现金流（产出价值 − 投入成本）按**雇佣加权 wage_weight**在各 pop 类型间分配。每种 pop 在 `common/pop_types/*.txt` 中有静态 `wage_weight`：

| pop | weight | pop | weight |
|---|---|---|---|
| slaves | 0 | shopkeepers / clergymen / engineers | 3 |
| peasants | 0.2 | bureaucrats / academics | 4 |
| laborers / soldiers | 1 | aristocrats / capitalists / officers | 5 |
| machinists / clerks | 1.5 | farmers | 2 |

V3_EAT 列「工资倍率」定义为雇佣加权平均：

```
wage_mult = Σ(employment_i × wage_weight_i) / Σ employment_i
```

这是「**每单位劳动力的工资敏感度**」的线性代理 —— 数值越大，该 PM 选项的工资支出占比越高。

## 6. 建造部门（Construction Sector）

`building_construction_sector` 是特殊建筑：它的产出不是商品，而是国家级模拟的**建造力（country_construction_add）**。建造力进入国家池，被各项目（含其他建筑）以 `required_construction` 数额消耗。

V3_EAT 为建造部门单独开「建造部门」sheet，列含：

```
物料成本 / 建造力  =  Σ(input qty × goods.cost) / construction_per_lvl
工资支出 / 建造力  =  Σ(employment × wage_weight) / construction_per_lvl
综合成本 / 建造力  =  上两项之和
```

「越低越好」，故采用反向条件格式（绿=低，红=高）。

## 7. 简化公理（Simplification Axioms）

| ID | 公理 | 影响 |
|---|---|---|
| **A1** | 所有商品按基础价 `cost` 计价 | 绝对利润有偏，相对排序无偏 |
| **A2** | 建筑 1 级且 100% 雇满 | 忽略招聘 ramp、proportionality 折扣 |
| **A3** | 不计法律 / 科技 / 公司加成 | 忽略 throughput / production_efficiency 修饰链 |
| **A4** | 静态截面，不模拟周演化 | 忽略价格反馈、人口流动、企业资金积累 |

## 8. 指标无偏性（Validity Discussion）

| 指标 | 在 A1–A4 下 |
|---|---|
| **产出/投入物量** | 完全准确（直接读 PM 字段） |
| **劳动力人数** | 完全准确（level_scaled 字段） |
| **建造力（required_construction）** | 完全准确（script_value 查表） |
| **工资倍率** | 准确（pop_type 静态字段） |
| **绝对利润** | **有偏**：受 A1 影响；用于「方向性」分析而非财务预测 |
| **建造力回报率** | **rank-ordering 无偏**：A1 误差对所有建筑同向作用 |
| **人均年产值** | rank-ordering 无偏，绝对值低估正向收益 |

## 9. 跨版本回归（Cross-Version Regression）

V3_EAT `diff` 命令在保留 A1–A4 假设下做严格的**结构差分**：识别新增/移除的 (建筑 × 组合) 单元，以及在双方都存在的单元中数值变化超过 ε 的字段。这不是经济仿真意义上的「价格变动」，而是**模组/补丁层面的脚本变更检测**，适合：

- 游戏更新后定位被改动的建筑/PM
- 模组开发回归测试
- 比对不同模组之间的经济参数差异

## 参考

- `common/production_methods/*` — PM 定义
- `common/production_method_groups/*` — PMG 列表
- `common/buildings/*` — 建筑、PMG 引用、required_construction
- `common/script_values/building_values.txt` — 建造力档位常量
- `common/pop_types/*.txt` — wage_weight 等
- `common/goods/00_goods.txt` — cost 等
- `common/building_groups/00_building_groups.txt` — parent_group 父链
- `launcher/launcher-settings.json` — 游戏版本
