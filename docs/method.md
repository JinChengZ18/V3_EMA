# V3_EAT — 实现细节与设计文档

**中文** | [English](method.en.md)

本文记录 V3_EAT 的内部架构、数据流、输出 schema 与跨版本差分的实现。面向打算扩展或集成本工具的开发者；普通使用者只需看 [README](../README.md) 即可。

经济学层面的指标定义、简化公理与无偏性讨论见 [economics.md](economics.md)。

---

## 1. Pipeline

```
launcher-settings.json ────┐
common/{goods,pop_types,                   ┌── 总览 sheet
  production_methods,                       │
  production_method_groups,                 ├── 农业 / 种植园 / 开采业 / 制造业 / ...
  buildings,                                │     （按 building_group root 分桶）
  building_groups,                          │
  script_values}                            ├── 建造部门 sheet
   ↓ PDX parser (parser/pdx_parser)         │     （成本/建造力，反向条件格式）
   ↓ Localization yml (parser/yml_loc)      │
GameData (model.py)              ──────────►├── 信息 sheet (game_version, counts)
   ↓                                        │
build_rows / build_construction_rows        ↓
(analysis/rows.py, analysis/construction.py)   v3_eat_report.xlsx

旧报告 ┐
        ├── read_report → diff_snapshots ─► 信息/新增/移除/变更 sheet
新报告 ┘                                    v3_eat_diff.xlsx
```

## 2. 模块结构

```
v3_eat/
├── parser/
│   ├── pdx_tokenizer.py      # PDX 词法分析（处理 ?= != hsv{} 等特殊语法）
│   ├── pdx_parser.py         # 递归下降语法分析 + 目录批量加载
│   └── yml_loc.py            # 本地化 yml 解析 + $ref$ 递归
├── model.py                  # dataclass：Good / PopType / PM / PMG / Building / GameData
├── loader.py                 # parser → 模型，统一入口；含游戏版本读取
├── analysis/
│   ├── metrics.py            # 纯函数指标（gross/net/roi/per_capita 等）
│   ├── rows.py               # 建筑 × PMG 笛卡尔积行装配
│   ├── construction.py       # 建造部门特别分析
│   └── diff.py               # 读已生成的 xlsx + 计算差异
├── output/
│   ├── csv_writer.py         # UTF-8 BOM csv
│   ├── xlsx_writer.py        # 多 sheet xlsx + 现代化样式 + 信息 sheet
│   └── diff_writer.py        # diff xlsx 输出
├── util/
│   ├── logging.py
│   └── strings.py            # BG_BUCKET 宏分类、PMG 类别推导
├── cli.py                    # argparse 命令分发
└── __main__.py               # 支持 python -m v3_eat
```

## 3. 输出 Schema

### v3_eat_report.xlsx

| Sheet | 内容 |
|---|---|
| 信息 | 游戏版本、原始版本号、工具版本、生成时间、对象计数 |
| 总览 | 全量组合行（建筑 × 基础 PM × 次要 PM × 自动化 PM） |
| 农业 / 种植园 / 开采业 / 制造业 / 服务业 / 基础设施 / 政府 / 军政 / 纪念物 | 按建筑组父链根（`bg_extraction` / `bg_manufacturing` / …）分桶；组内按利润降序 |
| 建造部门 | 建造部门 PM 的「建造力/级、物料成本/级、工资支出/级、单位建造力成本」横评 |

每行字段（19 列）：

```
建筑 | 基础生产方式 | 次要生产方式 | 自动化生产方式
| 产出价值 | 投入价值 | 利润 | 建造力 | 劳动力 | 工资倍率 | 建造力回报率 | 人均年产值
| 建筑分组 | 投入 | 产出
| 建筑ID | 基础_ID | 次要_ID | 自动化_ID
```

### v3_eat_diff.xlsx

| Sheet | 内容 |
|---|---|
| 信息 | 双方游戏版本、双方生成时间、比较时间、6 类计数 |
| 新增-组合 / 移除-组合 | 仅在新/旧报告中出现的 (建筑 × 组合) 行 |
| 变更-组合 | 双方都有但数值变化超过 ε 的行；每个变更字段以 旧 / 新 / Δ 三列并排，Δ 列条件格式（增=绿，减=红） |
| 新增-建造 / 移除-建造 / 变更-建造 | 同上，针对建造部门 sheet |

## 4. 可复现性

每个生成的 xlsx 在「信息」sheet 与 workbook properties 中记录：

- 游戏版本（`launcher-settings.json` 的 `version` 字段，如 `1.13.4 (Matcha)`）
- 原始版本号（`rawVersion` 字段）
- 工具版本（`v3_eat.__version__`）
- 生成时间戳（ISO-8601 本地时间）
- 解析对象计数（商品/工种/PM/PMG/建筑/组合行/建造部门行）

任何 V3_EAT 输出 xlsx 都能精确定位到一个 (game_version, tool_version) 二元组。`diff` 命令读取双方的「信息」sheet 后会在差异工作簿中展示这个二元组对照。

## 5. 跨版本差分实现

```bash
python -m v3_eat diff <old.xlsx> <new.xlsx> [--out diff.xlsx] [--eps-abs 0.01] [--eps-rel 0.005]
```

### 5.1 键定义

- 组合行 key：`(建筑ID, 基础_ID, 次要_ID, 自动化_ID)` 四元组
- 建造部门 key：`(建筑ID, PM_ID)` 二元组

### 5.2 比较字段

- 组合行：`产出价值, 投入价值, 利润, 建造力, 劳动力, 工资倍率, 建造力回报率, 人均年产值`
- 建造部门：`建造力/级, 劳动力/级, 工资倍率, 物料成本/级, 工资支出/级, 物料成本/建造力, 工资支出/建造力, 综合成本/建造力`

### 5.3 ε 阈值

```
变更触发条件 = abs(old - new) > max(eps_abs, eps_rel × max(|old|, |new|))
```

默认 `eps_abs=0.01, eps_rel=0.005`。这避免了浮点 round-trip 抖动（xlsx 存读会产生 ~1e-15 量级误差）误报为真实变更。

### 5.4 三段桶

每个 sheet 的 diff 分为：
- **added**（仅 new 有）→ 「新增-」sheet
- **removed**（仅 old 有）→ 「移除-」sheet
- **changed**（双方有但数值变更）→ 「变更-」sheet，仅展示**实际有变化**的字段，避免列宽爆炸

## 6. 限制

工具在简化公理 A1–A4 下运行，详见 [economics.md §7](economics.md)：

- A1：商品按基础价 `cost` 估值，不模拟动态市场
- A2：建筑 1 级且 100% 雇满
- A3：不计法律 / 科技 / 公司加成
- A4：静态截面，不模拟周演化

故本工具适合**结构性比较与排序**（哪个 PM 组合更优、哪些建筑被改动），不适合直接预测国家财政。

## 7. 未来扩展

- **动态价格**：从 saves 读出实时市场价覆盖 `cost`
- **Save-game 集成**：`.v3` 二进制解析，分析具体国家的实际经济结构
- **法律/科技层叠**：建模 throughput / production_efficiency 修饰链
- **模组兼容**：探测 mod 路径并合并 override
- **回归基线套件**：维护一组「金标准」xlsx，CI 中跑 diff，自动告警异常变更

## 8. 测试

`tests/test_diff.py` 含 3 个测例（新增 / 移除 / 数值变更 + ε 阈值上下界），可作 pytest 运行或纯脚本运行：

```powershell
python tests\test_diff.py
```

测例使用程序化构造的小 xlsx fixture（通过 `xlsx_writer` 写最小数据集，再人为修改其中一份），验证 `diff_snapshots` 在三段桶上的正确性。

## 9. 数据来源汇总

| 内容 | 文件 |
|---|---|
| 游戏版本 | `launcher/launcher-settings.json` |
| 商品价格 / 工种工资 | `common/{goods,pop_types}/*.txt` |
| 生产方式 / 组 / 建筑 | `common/{production_methods,production_method_groups,buildings}/*.txt` |
| 建筑组父链 | `common/building_groups/00_building_groups.txt` |
| 建造档位 | `common/script_values/building_values.txt` |
| 本地化 | `localization/{lang}/*.yml` |
