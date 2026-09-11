# 实验索引

目录与产物约定见[实验规范](../docs/experiment_rules.md)。以下均为探索代码，不能直接作为论文正式依据。

| 入口 | 用途与状态 |
|---|---|
| [问题3自建环境](b_adaptive_q3/README.md) | Python 标准库环境、固定误差场、基础策略；已通过本地单元与整局验证 |
| [两阶段策略](b_benchmark_scale/README.md) | 固定扫描后规划路径并补测清除；依赖 b_oracle_q3/oracle.py、b_overnight/task_cost.py |
| [C题材料核对脚本](c_framing_inspect.py) | 主分支已有历史探索；本次未运行，依赖未随本次交付的 C 题材料 |

保存的12个自建案例位于 `b_overnight/runs/q3_sweep_validation/cases.json`，作为固定重放输入保留。新运行产物写入 `outputs/experiments/<实验目录>/<run-id>/`。
