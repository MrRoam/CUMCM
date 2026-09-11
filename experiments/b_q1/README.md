# 第一问完整候选结果

第一问的区域构造、直径算法、正确性证明、合法测向反例、程序和图表已形成。31项测试通过；尚未登记团队人工审阅与正式采纳。

**先读 [完整解答](SOLUTION.md)**；实际运行证据见 [验证记录](results/VALIDATION.md)。核心结论：直径等于最远顶点对距离，但直径为40米的定位区域未必能被半径20米的圆覆盖。

## 内容入口

| 内容 | 位置 |
| --- | --- |
| 完整推导、证明、算例及后续子问联系 | [SOLUTION.md](SOLUTION.md) |
| 独立函数与命令行入口 | [solver.py](solver.py) |
| 自建观测输入 | [examples/](examples/) |
| 算例生成及物理条件核验 | [run_examples.py](run_examples.py) |
| 第一问测试与验证执行器 | [test_solver.py](test_solver.py)、[verify.py](verify.py) |
| 完整数值、输入与源码散列 | [results/examples.json](results/examples.json) |
| 测试原始输出与源码散列 | [results/validation.json](results/validation.json) |
| 两幅PNG/SVG图及生成脚本 | [figures/](figures/)、[plot_results.py](plot_results.py) |

## 复现命令

在仓库根目录运行。求解、算例生成和测试使用本机已验证的Python3.13标准库，无需额外安装。

```powershell
py -3.13 experiments/b_q1/run_examples.py
py -3.13 experiments/b_q1/solver.py experiments/b_q1/examples/triangle.json
& D:/anaconda/python.exe experiments/b_q1/plot_results.py
py -3.13 experiments/b_q1/verify.py
```

制图命令使用本机已有Python3.7、Matplotlib2.2.3；该解释器路径只是本机复现指令，不是代码依赖的固定目录。在其他环境可用已安装Matplotlib的Python执行同一脚本。Windows默认使用微软雅黑字体；其他系统通过 `--font 路径` 指定中文字体。

生成顺序为：算例与数值 → 图表 → 验证。输出使用脚本所在目录定位，重新生成会覆盖本目录中相应生成物。源码改变后应按此顺序重新生成，避免保留过期结果。

## 输入与输出

输入是一个包含 `observations` 的JSON对象。每条观测属于同一干扰源，坐标单位米，示向度为东起逆时针角，范围 `[0,360)`：

```json
{
  "observations": [
    {"position_m": [-500, 0], "bearing_deg": 0},
    {"position_m": [0, -500], "bearing_deg": 90}
  ]
}
```

调用函数：

```python
from experiments.b_q1.solver import solve
result = solve(observations)
```

| 输出字段 | 含义 |
| --- | --- |
| `status` | `polygon`、`segment`、`point`、`empty`、`unbounded` |
| `vertices_m` | 有界多边形的逆时针顶点；线段端点或单点；无界时只列有限顶点，不代表整个区域 |
| `diameter_m` | 有界集的直径；空集为 `None` / JSON `null`；无界函数返回 `math.inf`，JSON输出字符串 `"Infinity"` |
| `diameter_endpoints_m` | 有限直径对应端点；空集及无界集为 `null` |
| `feasible_point_m` | 非空区域的一个可行点 |
| `recession_direction` | 无界时可无限前进的方向 |
| `error_half_width_deg`、`numerics` | 物理半张角1°及单独记录的浮点容差 |

空观测列表表示尚无约束，返回全平面无界。格式不合、非有限数值和越界角度抛出异常；命令行错误退出码为2。算法不接收目标域或距离圆盘，不在调用中引入第三问的角度余量。自建输入中的源坐标、接收半径和解析答案是验证元数据，求解器不会读取。

## 复用关系与范围

本目录直接复用 `../b_overnight/q2_geometry.py` 的三个几何函数，后者按文件路径加载 `../b_adaptive_q3/geometry.py`。这些相对位置是复现依赖，不能仅复制本目录后假定它完全独立。共有模块本轮仅修正同名导入风险，几何核心和原冻结底座未改动；旧16项几何回归已通过。

主定义依据[题面](../../problem/B题.md)，已有研究来自[夜间推导](../b_overnight/MODEL_Q1_Q2.md)。本目录维护新增完整解答，历史材料保留用于追溯。

当前浮点实现适用于题目尺度的正常观测及已验证边界算例；接近数值阈值时不是严格几何证书，详见完整解答第7节。实验成果已完成本计划中的计算和AI核验，正式采纳后仍按仓库规则进入 `src/`、`outputs/` 和唯一论文源稿。本轮未启动模拟器或改动第三问行动策略。
