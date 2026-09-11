# 问题3本地仿真环境：队友使用入口

这是按题面公开规则编写的 Python 环境，不调用官方模拟器后台。用于在可控案例上调试、比较策略；没有复刻官方隐藏源位置、接收半径分布和误差场，不能把本地成绩当作官方成绩。当前交付以问题3为主。

## 直接运行

Python 3.10+，只使用标准库，无须安装第三方包。以下命令从仓库根目录运行；Windows 可以把 `python` 换成 `py -3.13`。输出目录必须尚不存在。

```sh
python experiments/b_adaptive_q3/test_core.py
python experiments/b_benchmark_scale/test_two_stage.py
python experiments/b_adaptive_q3/example_environment.py

# 基础策略：4个不同布局、误差类型的完整案例
python experiments/b_adaptive_q3/run_local.py --stage smoke --output experiments/b_adaptive_q3/runs/my_smoke

# 两阶段策略：固定七点扫描，然后自由规划路径并按需补测、清除
python experiments/b_benchmark_scale/run_two_stage.py --stage development --policies scan7_r60 --output experiments/b_benchmark_scale/runs/my_development

# 同12个已保存自建案例，比较两套扫描阈值
python experiments/b_benchmark_scale/run_two_stage.py --stage replay --policies scan7_r60 scan7_r30 --output experiments/b_benchmark_scale/runs/my_comparison
```

`run_local.py` 还提供 `--stage holdout`、`--paired-reference`、`--cases 案例.json`、`--config 参数.json`。其中 `reference` 是较笨的逐目标清除格策略，**不是**上面的两阶段七点策略。

`run_two_stage.py` 提供 `development`（12例）、`holdout`（24例）、`stress`（8例）、`replay`（随仓库提供的12例）；可选 `scan7_r60`、`scan7_r30`、`scan13_r60`、`scan19_r60`。这些固定案例此前已被开发者查看过，队友不能把它们称为新的盲测集。新测试可另选种子并用 `generate()` 生成。

## 接入自己的策略

同目录的 [example_environment.py](example_environment.py) 是最小可运行例子。核心接口：

```python
from simulation import LocalEnvironment, Scenario, Source, generate

case = generate(seed=20260911, layout="uniform", noise="smooth")
env = LocalEnvironment(case)
feedback = env.act({"kind": "measure", "position": (0.0, 0.0), "channel": 1})
```

- 动作 `kind` 为 `measure` 或 `clear`；`position` 是 `(x, y)`，单位米；`channel` 是1—20的整数。
- 检测返回 `measure_result`：`no_signal`、`near` 或 `direction`。最后一种另有 `svd_deg`，单位度，正东为0度、逆时针增加。
- 清除返回 `clear_result`：`success` 或 `no_target_in_range`。
- 每次返回包含 `accepted`、累计 `virtual_time_s` 和本次 `costs`。
- `env` 持有源真值，仅供环境和审计使用。公平比较时，策略只接收反馈和公开条件，不能读取 `env.sources`、`env.scenario` 或案例真值。
- `Scenario.to_dict()` / `Scenario.from_dict()` 支持保存、加载同一案例；固定案例、误差类型和种子后，同一动作序列得到同一反馈及虚拟耗时。

接入现有状态时，按 `policy.choose(state)` → `env.act(action)` → `state.update(action, feedback)` 循环。可参考 [run_local.py](run_local.py)；完整结束还必须检查实际全部清除，不能只比较未完成局的较短耗时。

## 规则与边界

| 项目 | 当前实现 |
|---|---|
| 初始位置和测向频道 | `(0, 0)`、频道1 |
| 移动 | 欧氏距离 ÷ 5 m/s |
| 检测 | 5秒；仅检测换频道时另加1秒 |
| 清除 | 成功5秒、失败3秒；不改变测向频道 |
| 接收、近距离、清除边界 | 距离分别不超过该源半径、5米、20米，边界包含 |
| 生成案例 | 10—16个不同频道全向源；位置在半径1800米圆内；接收半径1000—1500米 |
| 布局 | `uniform`、`edge`、`cluster`、`line`，属于团队测试设定 |
| 固定误差场 | `zero`、`smooth`、`biased`、`hashed`；由位置、频道、种子确定 |
| 角度输出 | 加入±1度内自建误差后舍入两位小数，总偏差可能达到1.005度；策略额外保留舍入余量 |

低层 `LocalEnvironment` 允许少量源构造单元测试，不负责完整校验自定义场景是否符合整局题面；调用方须检查源数、坐标、半径、频道和方向。问题3驱动拒绝定向源；环境虽有半圆接收几何，不能据此声称已经交付第四问完整求解。

此接口是进程内 Python 字典接口，不实现 HTTP、登录、请求编号/重试、服务器超时或界面倒计时。现实运行时间与虚拟计费分开记录。

七点扫描保证发现覆盖，不保证第一阶段把全部源缩到20米或60米内。两阶段策略随后仍可能补测、试清；路径优化针对当时估计位置，不等于未知真值下的全局最优。

## 文件和输出

- 本目录：`simulation.py` 环境与案例生成；`geometry.py` 几何；`state.py` 信息状态；`policy.py` 基础策略；`run_local.py` 整局运行；`test_core.py` 15项检查。
- `../b_benchmark_scale/`：`two_stage.py` 两阶段策略、`run_two_stage.py` 批量比较、`test_two_stage.py` 3项检查。
- `../b_overnight/task_cost.py`：两阶段策略的局部补测/清除依赖。
- `../b_oracle_q3/oracle.py`：路径动态规划依赖；其中旧离线报告的独立 `main()` 需要历史实验产物，本交付不使用该入口。
- `../b_overnight/runs/q3_sweep_validation/cases.json`：12个自建案例，供 `--stage replay` 读取，非官方隐藏案例。

运行结果包含 `cases.json`、`results.json`、`RESULTS.md`、逐动作 `actions/*.jsonl` 和代码/参数哈希；两阶段还保存 `plans/`。运行目录中的 `source/` 为审计快照，日常修改应修改上述源文件。新运行结果默认被各实验目录的 `.gitignore` 忽略，避免误交大量产物。

团队比较建议使用同一批案例，先检查全清，再比较每局 `虚拟总秒数 / 源数`。新方法修改后必须重新运行，不能混用旧代码结果。
