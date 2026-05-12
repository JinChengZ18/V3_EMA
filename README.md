# EMA — Victoria 3 计量经济自动化模组

**中文** | [English](README.en.md)

Econometrics Automation，即EMA模组，是一套V3计量经济学研究的全自动管线工具。它并不涉及游戏内容的任何修改，而是从本地文件提取数据，并生产结构化的Excel报告。

### 为什么做这个模组？

Victoria 3 中的经济决策空间由 ~440 种生产方式（PM）、~200 个生产方式组（PMG）、~110 座建筑构成，理论组合空间 1500 余种。任何依赖人工抄表的经济分析都容易在每次补丁后陈旧，毕竟你永远不知道P社究竟暗改了什么（或者他们写在了某次日志里，但你已经很久没玩V3了），这一方面给维护者带来了痛苦，另一方面也使得玩家不可避免地遭受过时攻略的困扰。

EMA可以方便快捷地实现端到端的V3经济分析，从而解决上述问题：

- 一行命令，**当前版本**全部 1500+ 组合的经济指标导出 Excel
- 一行命令，**两个版本**的报表做差分，精确告诉玩家哪些建筑、哪些字段被改了多少
- 报告自动嵌入游戏版本号（如 `1.13.4 (Matcha)`），便于历史归档



## 安装

### 第一步：解压到任意位置

把 `V3_EMA` 文件夹放在你喜欢的任何地方都可以（**不必再放进游戏目录**，避免被 Steam 校验文件时误删）。常见的位置如 `D:\tools\V3_EMA\` 或 `C:\Users\你\Documents\V3_EMA\`。

### 第二步：装 Python 与依赖

需要 Python ≥ 3.10。在 V3_EMA 目录打开 PowerShell：

```powershell
python -m pip install openpyxl
```

只有一个依赖（`openpyxl`，写 Excel 用）。

### 第三步：首次运行 —— 找到游戏

工具默认按以下顺序自动找到 V3 安装位置：

1. CLI 参数 `--game-root <path>`（一次性覆盖）
2. 环境变量 `V3_GAME_ROOT`
3. 缓存文件 `<V3_EMA>/.game_root`
4. **自动扫描 Steam 库**（Windows 注册表 + `libraryfolders.vdf`）—— **多数用户到这一步即可**
5. 如果 V3_EMA 自己就在游戏目录下，向上回溯找到游戏根

绝大多数情况下你不需要做任何配置。如果自动检测失败，三种解决方式任选其一：

```powershell
python -m v3_ema config --game-root "E:\STEAM\steamapps\common\Victoria 3"   # 持久化保存
python -m v3_ema report --game-root "E:\STEAM\steamapps\common\Victoria 3"    # 单次覆盖
$env:V3_GAME_ROOT = "E:\STEAM\steamapps\common\Victoria 3"; python -m v3_ema report  # 环境变量
```

辅助命令：

```powershell
python -m v3_ema config --show     # 查看当前缓存的路径与实际解析路径
python -m v3_ema config --clear    # 清缓存，下次重新检测
```



## 使用

### 功能 1：建筑产值表

```powershell
# 生成当前版本（默认中文）
python -m v3_ema report

# 跨版本对比 —— 项目内置 1.13.4 基线，可直接用
python -m v3_ema report --out current.xlsx
python -m v3_ema diff baseline_buildings_v1.13.4.xlsx current.xlsx

# 切换语言（V3 全部 11 种）
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

输出位置：`V3_EMA\out\buildings\{reports,diffs}\`。

报表包含 12 张 sheet：信息 / 总览 / 农业 / 种植园 / 开采业 / 制造业 / 服务业 / 基础设施 / 政府 / 军政 / 纪念物 / 建造部门。每行核心字段：建筑 / 基础-次要-自动化生产方式 / 产出价值 / 投入价值 / 利润 / 建造力 / 劳动力 / 工资倍率 / 建造力回报率 / 人均年产值。Diff 工作簿含「新增-组合 / 移除-组合 / 变更-组合」等 6 张 sheet，变更字段以「旧 / 新 / Δ」三列并排，Δ 自动绿/红着色。

### 功能 2：地区资源统计

```powershell
# 生成当前版本（默认中文）
python -m v3_ema regions report

# 跨版本对比 —— 项目内置 1.13.4 基线，可直接用
python -m v3_ema regions report --out current.xlsx
python -m v3_ema regions diff baseline_regions_v1.13.4.xlsx current.xlsx

# 切换语言
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

输出位置：`V3_EMA\out\regions\{reports,diffs}\`。

报表按 14 个大洲分桶（西欧 / 南欧 / 北欧 / 东欧 / 北美 / 中美 / 南美 / 非洲 / 中东 / 中亚 / 印度 / 东亚 / 东南亚 / 大洋洲）。**首行是合计**（该桶内全部地区资源总和）。每行核心字段：地区 / 战略大区 / 可耕地 / 可耕作建筑 / 上限总和 / **每种资源的单项列**（铁矿/煤矿/林业营地/油田 等，方便排序对比）/ 总产能容量 / 地区特性。

### 工具命令

```powershell
python -m v3_ema verify                       # 自检（确认能正确解析当前游戏）
python -m v3_ema dump-pm pm_simple_farming    # 调试单个生产方式的解析结果
python tests\test_diff.py                     # 跑测例（应有 6 个 PASS）
```

通用参数：`--game-root <path>` 指定别的游戏根目录；`--ui-lang zh|en` 强制 UI 语言（默认根据 `--lang` 推断：simp_chinese → 中文 UI，其余 → 英文）。

---

## 进阶文档

- **V3 经济运行原理 + 工具的简化假设**：[docs/economics.md](docs/economics.md)
- **架构、模块、输出 schema、diff 实现细节**：[docs/method.md](docs/method.md)



## 数据来源

| 内容                 | 文件                                                         |
| -------------------- | ------------------------------------------------------------ |
| 游戏版本             | `launcher/launcher-settings.json`                            |
| 商品价格 / 工种工资  | `common/{goods,pop_types}/*.txt`                             |
| 生产方式 / 组 / 建筑 | `common/{production_methods,production_method_groups,buildings}/*.txt` |
| 建筑组父链           | `common/building_groups/00_building_groups.txt`              |
| 建造档位             | `common/script_values/building_values.txt`                   |
| 本地化               | `localization/{lang}/*.yml`                                  |
