# B题第二问：面积均匀平均半径选点包

## 给接手AI的30秒结论

当前暂定策略是：在完整首次测向窄扇形和1000米保守二次接收约束下，按扇形**面积均匀**赋权，最小化两次测向交集的**最小包围圆半径平均值**。标准局部坐标中的第二检测点取：

```text
左侧：(870.000,  501.683285691) m
右侧：(870.000, -501.683285691) m
```

两点关于首次示向中心线对称。现有搜索只支持标准场景，属于“当前搜索得到的最佳可行解”，没有连续全局最优证明。

## 必读顺序

1. `strategy_config.json`：唯一的方案口径、常量、采纳坐标和适用范围。
2. `strategy.py`：坐标变换、面积平均评价和可复算搜索。
3. `geometry.py`：误差带裁剪、面积均匀网格和最小包围圆评价器。
4. `outputs/q2/adopted_average_strategy.json`：加密网格复核结果与源码哈希。
5. `outputs/q2/adopted_average_strategy_receipt.json`：官方题面、评价器、配置和结果的可校验来源凭据。
6. `docs/B题/project_handoff.md`：全项目上下文及第二问边界。

不要优先读取旧聊天结论，也不要把`experiments/`中的径向均匀或融合指标重新当成当前决策。

## 模型输入与输出

局部坐标约定：第一次检测点为原点，第一次示向中心线为+x轴，左侧为+y。首次可能源位于距离5—1500米、角度±1°的窄扇形。第二点必须到该区域所有外包顶点不超过1000米。

对每个面积均匀真源位置和均匀二次误差，程序计算两次测向误差带交集的最小包围圆半径；目标是这些半径的算术平均值最小。这里的“半径”不是直径的一半。

`recommend_second_point`只做刚体变换：给定第一次检测点和首次示向角，把标准局部坐标旋转、平移到全局坐标。若首次扇形被1800米目标圆域或其他信息裁剪，必须重新构造可行区域并优化，不能直接套用。

## 运行方式

在仓库根目录执行：

```console
python -m unittest src.q2.test_strategy
python -m src.q2 recommend --first-x 0 --first-y 0 --bearing-deg 0 --side left
python -m src.q2 verify-selected
python -m src.q2 search
python C:/Users/qieji/.codex/skills/modeling-team/scripts/result_receipt.py check outputs/q2/adopted_average_strategy_receipt.json --root .
```

最后一条中的技能脚本路径是本机核验入口，换电脑时按实际Codex技能安装位置替换；通用复算不依赖该脚本。`verify-selected`默认评价320×17×17＝92480个场景；`search`默认训练网格为24×3×3。输出只写入`outputs/q2/`。长验证用于复核，不应在实时决策时运行；实时策略直接调用`recommend_second_point`。

## 可以与不可以主张什么

可以主张：在配置文件定义的标准合成场景中，当前确定性搜索得到面积平均半径约30.505米的可行点；相对于离散最坏值点，二者路程时间差可忽略，因此暂选面积平均方案。

不可以主张：题面规定了面积均匀概率、当前点是连续全局最优、任意初始位置都可直接套用、两次测向保证半径不超过20米、完整清除任务一定更快，或已经通过团队人工核验。

## 下一位AI最先做什么

先运行快速测试，再校验`outputs/q2/adopted_average_strategy.json`中的源码哈希和92480场景均值。只有首次扇形被目标边界裁剪、接收信息被加强、或策略目标改变时才重跑搜索；否则不要重新讨论径向均匀与面积均匀的选择。
