# 第三问探索：按方法导航

按“探索方法”组织，每个方法目录同时包含思路文档、实现代码和原始结果。点击方法名可查看该方法的完整文件索引；代码目录保留既有标识，维持导入和历史运行记录可追溯。


## 合入后的运行入口（2026-09-12）

本目录保留 PR #9 的历史实验、失败轨迹和冻结快照，仍未晋升正式模型。历史 `runs/`、演示与报告作为只读证据保留；新数值和日志写入 `outputs/experiments/b_q3/<run-id>/`。不要直接执行历史文档中会重写原目录的报告、演示构建或归档脚本。

已补齐 `b_overnight/coverage.py` 与问题三专用 `sweep_policy.py`，无须先合并整个 PR #6。Python 3.13；离线诊断使用 NumPy，策略主体及主测试使用标准库。统一运行记录 `execution.json` 保存命令、Python 版本、基础提交、实际源码快照和状态；未结束的运行不能当作成功结果。每次使用新目录，不自动续用旧结果。

从仓库根目录运行，例如：

```powershell
python experiments/b_q3/probability_patrol/runner.py --policy patrol --stage development --out outputs/experiments/b_q3/patrol_reproduce_01 --workers 1
python experiments/b_q3/adaptive_second/run.py --stage pilot --samples 16 --workers 1 --out outputs/experiments/b_q3/second_reproduce_01
python experiments/b_q3/refinement/postcheck.py --stage micro --out outputs/experiments/b_q3/refinement_reproduce_01 --workers 1 --modes current f1 f3
python experiments/b_q3/boundary_penalty/run_confirmation.py --out outputs/experiments/b_q3/boundary_reproduce_01
python experiments/b_q3/review_pr9.py --out outputs/experiments/b_q3/review_reproduce_01
```

信念树与可清除效用的 `run.py`、函数对照 `run_activation.py`、边界开发 `run_boundary.py` 同样要求新的 `--out`；旧决策预演 `decision_pilot/run.py --stage smoke --output <run-id>` 写入 `outputs/experiments/b_q3/decision_pilot/<run-id>/`。这些性能批次可能需要较长时间，上面的示例不是本次全部执行记录。

历史综述引用的 `b_method_families`、`research` 及旧官方演练输入仍未随本 PR 提供，因此不宣称相关综述构建、旧演练审计或冻结交接包在当前主分支可以独立重建。完整运行依赖、实测范围和剩余限制见 [PR #9 审查记录](../../docs/pr9_review.md)。

## 方法目录

| 方法 | 探索内容 | 阅读提示 |
| --- | --- | --- |
| [旧基线：完成工作量评分与固定扫描](legacy_baseline/方法索引.md) | 早期 W/G 评分、候选点讨论、七点扫描参照和真实演练核验。 | 演练核验与历史讨论；基线实现位于相邻实验目录。 |
| [中心逼近续行与阶段交界预演](decision_pilot/方法索引.md) | 扫描后比较多目标行动块，用预演完成费用选择续行动作。 | 保留失败复盘和冻结交接包。 |
| [两点起搜与概率巡检（R1—R4）](probability_patrol/方法索引.md) | 两点开始，结合途中共享补测、局部定位、清除及查漏路线。 | 保留各轮配置、冻结结果；概率模块与实际接入边界见原文。 |
| [自适应第二站](adaptive_second/方法索引.md) | 依据第一站反馈选择第二站位置，并对照是否同时选择频道。 | 保留条件采样、在线接口和第二站配对实验。 |
| [补测过滤与多次清除（F1—F4）](refinement/方法索引.md) | F1去冗余、F2条件试算、F3多次覆盖清除、F4独立复查。 | 原报告保留F3研究候选，不采用F4；含逐步演示。 |
| [统一行动与多步信念树（U1/T3/M3）](belief_tree/方法索引.md) | 从统一行动中搜索一层、三层反馈，或加入整站扫描动作。 | 原报告停止当前候选；未实施方向另见NEXT_DESIGN。 |
| [可清除效用、逐频道路线与函数对照](clearability/方法索引.md) | S1—S4整套规则，以及另行隔离的线性/Sigmoid函数对照。 | 两组实验分开阅读；原报告不支持默认替换F3。 |
| [边界面积惩罚](boundary_penalty/方法索引.md) | 按接收圆越出任务区域的面积比例，在F3候选评分中加入惩罚。 | 单因素路线；保留开发及固定参数确认记录。 |

## 先看哪一条

主要演进为：旧基线 → 中心逼近失败复盘 → 两点起搜 → 自适应第二站 → F系列。F3之后分别探索了信念树、可清除效用/逐频道路线和边界惩罚，后三条是并列探索。具体依赖、采用范围与实验批次以各方法模型和报告为准；顺序不代表性能排名。

仅研究、未完整实施的想法仍放在所属路线的文档中，例如[信念树后续设计](belief_tree/NEXT_DESIGN.md)。目录外已有[模型重评](../b_method_families/Q3_RESEARCH_REASSESSMENT.md)和[研究资料](../research/)，保留原位置。

## 跨方法综述与整理记录

- [AI1/AI2/AI3完整综述](cross_method/README.md)：跨路线的优化历程、性能分组、时间尺度与现象总结。
- [整理记录](ORGANIZATION.md)：原路径到新路径、保留边界、校验说明。

这里的状态摘自原报告，不代表本次重新验证性能；本次没有运行新实验或官方测试。
