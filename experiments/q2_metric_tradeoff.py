"""问题2不同定位质量指标对第二检测点位置的影响。

复现：python experiments/q2_metric_tradeoff.py

本脚本沿用 q2_strategy_comparison.py 的几何评价器，只比较指标与搜索结果；
输出仍是探索性结果，不构成连续全局最优证明或官方模拟器成绩。
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

import q2_strategy_comparison as geometry


ROOT = Path(__file__).resolve().parents[1]


def scenario_values(poly, point, samples, chunk=2048):
    source, errors = samples
    p = np.asarray(point, dtype=float)
    return np.concatenate(
        [geometry.radii(poly, p, source[i : i + chunk], errors[i : i + chunk])
         for i in range(0, len(source), chunk)]
    )


def training_metrics(poly, point, samples):
    area = scenario_values(poly, point, samples["area"])
    radial = scenario_values(poly, point, samples["radial"])
    worst = scenario_values(poly, point, samples["worst"])
    return {
        "area_mean_m": float(area.mean()),
        "radial_mean_m": float(radial.mean()),
        "sample_worst_m": float(worst.max()),
    }


def point_key(point):
    return tuple(round(float(x), 9) for x in point)


def coarse_candidates(poly, step=25.0):
    result = []
    for x in np.arange(0.0, 1500.0 + step / 2, step):
        upper = geometry.safe_b(poly, float(x))
        if upper is None:
            continue
        ys = list(np.arange(0.0, upper + 1e-9, step)) + [upper]
        for y in ys:
            point = (float(x), float(y))
            if geometry.feasible(poly, point):
                result.append(point)
    # 显式纳入已有方案，避免网格对齐造成虚假劣化。
    for x in (750.0, 788.0, 870.0):
        upper = geometry.safe_b(poly, x)
        if upper is not None:
            result.append((x, float(upper)))
    return list(dict.fromkeys(point_key(p) for p in result))


def objective(metrics, kind, normalizers=None, worst_weight=None):
    if kind in metrics:
        return metrics[kind]
    mean_regret = 0.5 * (
        metrics["area_mean_m"] / normalizers["area_mean_m"]
        + metrics["radial_mean_m"] / normalizers["radial_mean_m"]
    ) - 1.0
    worst_regret = metrics["sample_worst_m"] / normalizers["sample_worst_m"] - 1.0
    if kind == "minimax_regret":
        return max(mean_regret, worst_regret)
    return (1.0 - worst_weight) * mean_regret + worst_weight * worst_regret


def refine(poly, start, kind, evaluate, normalizers=None, worst_weight=None):
    current = point_key(start)
    current_value = objective(evaluate(current), kind, normalizers, worst_weight)
    for step in (10.0, 5.0, 2.0, 1.0, 0.5):
        for _ in range(30):
            x, y = current
            trials = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                           (1, 1), (1, -1), (-1, 1), (-1, -1)):
                trials.append((x + dx * step, y + dy * step))
            for trial_x in (x - step, x, x + step):
                upper = geometry.safe_b(poly, trial_x)
                if upper is not None:
                    trials.append((trial_x, float(upper)))
            best_point, best_value = current, current_value
            for trial in trials:
                if trial[1] < -1e-9 or not geometry.feasible(poly, trial):
                    continue
                trial = point_key(trial)
                value = objective(evaluate(trial), kind, normalizers, worst_weight)
                if value < best_value - 1e-12:
                    best_point, best_value = trial, value
            if best_point == current:
                break
            current, current_value = best_point, best_value
    return current, current_value


def evaluate_final(poly, point, samples):
    area = scenario_values(poly, point, samples["area"])
    radial = scenario_values(poly, point, samples["radial"])
    worst = scenario_values(poly, point, samples["worst"])
    worst_index = int(np.argmax(worst))
    source, errors = samples["worst"]
    g = source[worst_index]
    return {
        "point_m": [float(point[0]), float(point[1])],
        "move_distance_m": float(math.hypot(*point)),
        "move_seconds": float(math.hypot(*point) / 5.0),
        "receive_max_distance_m": float(np.max(np.linalg.norm(poly - point, axis=1))),
        "area_mean_m": float(area.mean()),
        "area_p95_m": float(np.quantile(area, 0.95)),
        "area_radius_le20_fraction": float(np.mean(area <= 20.0)),
        "radial_mean_m": float(radial.mean()),
        "radial_p95_m": float(np.quantile(radial, 0.95)),
        "radial_radius_le20_fraction": float(np.mean(radial <= 20.0)),
        "sample_worst_m": float(worst[worst_index]),
        "sample_worst_source_m": [float(g[0]), float(g[1])],
        "sample_worst_error_deg": float(np.degrees(errors[worst_index])),
    }


def arc_refinement_check(selected):
    """检查首次扇形圆弧由16段加密到64段后关键候选排序是否改变。"""
    names = ["area_mean", "radial_mean", "sample_worst", "blend_w050"]
    samples = {
        "area": geometry.source_grid(40, 5, 5, "area", False),
        "radial": geometry.source_grid(40, 5, 5, "radial", False),
        "worst": geometry.source_grid(61, 5, 5, "radial", False, True),
    }
    results = []
    for arc_steps in (16, 64):
        poly = geometry.initial_polygon(arc_steps)
        values = {}
        for name in names:
            point = selected[name]
            values[name] = {}
            for metric, sample in samples.items():
                radii = scenario_values(poly, point, sample)
                values[name][metric] = float(radii.max() if metric == "worst" else radii.mean())
        results.append(values)
    return {
        "checked_candidates": names,
        "sample_counts": {key: len(value[0]) for key, value in samples.items()},
        "max_metric_difference_m": {
            metric: max(abs(results[1][name][metric] - results[0][name][metric]) for name in names)
            for metric in samples
        },
        "ordering_unchanged": {
            metric: (
                sorted(names, key=lambda name: results[0][name][metric])
                == sorted(names, key=lambda name: results[1][name][metric])
            )
            for metric in samples
        },
    }


def build_report(result):
    labels = {
        "area_mean": "面积均值最优",
        "radial_mean": "径向均值最优",
        "sample_worst": "离散最坏值最优",
        "blend_w025": "融合：最坏权重0.25",
        "blend_w050": "融合：最坏权重0.50",
        "blend_w075": "融合：最坏权重0.75",
        "minimax_regret": "融合：最小最大相对损失",
    }
    rows = result["finalists"]
    lines = [
        "# 问题2：不同指标与融合指标的选点影响",
        "",
        "状态：探索性数值比较；沿用标准完整扇形、保守二次接收条件和现有几何评价器，非连续全局最优证明。",
        "",
        "平均指标分别按面积均匀、径向均匀计算；最坏指标是加密有限网格上的最大最小包围圆半径。融合前将两种平均值和最坏值分别除以其单指标最优值，再比较相对损失。",
        "",
        "|方案|第二点坐标/米|面积平均半径/米|径向平均半径/米|网格最坏半径/米|面积下≤20米比例|径向下≤20米比例|移动时间/秒|",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, row in rows.items():
        p = row["point_m"]
        lines.append(
            f"|{labels[key]}|({p[0]:.3f}, {p[1]:.3f})|{row['area_mean_m']:.6f}|"
            f"{row['radial_mean_m']:.6f}|{row['sample_worst_m']:.6f}|"
            f"{100*row['area_radius_le20_fraction']:.3f}%|"
            f"{100*row['radial_radius_le20_fraction']:.3f}%|{row['move_seconds']:.3f}|"
        )
    lines += [
        "",
        f"所有最终候选之间的最大位置距离为 {result['position_effects']['max_pairwise_distance_m']:.3f} 米。",
        f"面积均值最优点与离散最坏值最优点相距 {result['position_effects']['area_to_worst_distance_m']:.3f} 米；径向均值最优点与离散最坏值最优点相距 {result['position_effects']['radial_to_worst_distance_m']:.3f} 米。",
        "",
        "验证网格：两种平均值各使用320×17×17个中点场景；最坏值使用301×17×17个含边界场景。最坏值仍是离散下界，不能写成连续严格最坏上界。",
        "",
        f"完整运行墙钟时间：{result['runtime']['seconds']:.2f} 秒。",
    ]
    return "\n".join(lines) + "\n"


def main():
    started = time.perf_counter()
    poly = geometry.initial_polygon()
    checks = geometry.checks(poly)
    train = {
        "area": geometry.source_grid(24, 3, 3, "area", False),
        "radial": geometry.source_grid(24, 3, 3, "radial", False),
        "worst": geometry.source_grid(31, 5, 5, "radial", False, True),
    }
    final_samples = {
        "area": geometry.source_grid(320, 17, 17, "area", False),
        "radial": geometry.source_grid(320, 17, 17, "radial", False),
        "worst": geometry.source_grid(301, 17, 17, "radial", False, True),
    }

    cache = {}

    def evaluate(point):
        key = point_key(point)
        if key not in cache:
            cache[key] = training_metrics(poly, key, train)
        return cache[key]

    coarse = coarse_candidates(poly)
    print("coarse candidates", len(coarse), flush=True)
    for i, point in enumerate(coarse, 1):
        evaluate(point)
        if i % 250 == 0:
            print("coarse evaluated", i, flush=True)

    key_map = {
        "area_mean": "area_mean_m",
        "radial_mean": "radial_mean_m",
        "sample_worst": "sample_worst_m",
    }
    selected = {}
    for label, metric_key in key_map.items():
        start = min(coarse, key=lambda p: evaluate(p)[metric_key])
        selected[label], _ = refine(poly, start, metric_key, evaluate)
        print("single", label, selected[label], evaluate(selected[label]), flush=True)

    normalizers = {
        metric_key: evaluate(selected[label])[metric_key]
        for label, metric_key in key_map.items()
    }
    for weight in (0.25, 0.50, 0.75):
        label = f"blend_w{int(weight*100):03d}"
        start = min(
            coarse,
            key=lambda p: objective(evaluate(p), "blend", normalizers, weight),
        )
        selected[label], _ = refine(
            poly, start, "blend", evaluate, normalizers, weight
        )
        print("blend", weight, selected[label], evaluate(selected[label]), flush=True)

    start = min(
        coarse,
        key=lambda p: objective(evaluate(p), "minimax_regret", normalizers),
    )
    selected["minimax_regret"], _ = refine(
        poly, start, "minimax_regret", evaluate, normalizers
    )
    print("minimax", selected["minimax_regret"], evaluate(selected["minimax_regret"]), flush=True)

    finalists = {}
    for label, point in selected.items():
        print("final evaluation", label, point, flush=True)
        finalists[label] = evaluate_final(poly, point, final_samples)

    points = {key: np.array(row["point_m"]) for key, row in finalists.items()}
    distances = [
        float(np.linalg.norm(a - b))
        for i, a in enumerate(points.values())
        for b in list(points.values())[i + 1 :]
    ]
    result = {
        "status": "探索性多指标比较，非连续最坏值证明，非官方成绩",
        "definitions": {
            "feasible": "max distance to initial outer polygon <= 1000 m",
            "average_models": ["area-uniform", "radial-uniform"],
            "sample_worst": "maximum over endpoint grid; lower bound on continuous worst case",
            "blend": "weighted normalized relative loss; mean component averages area and radial relative losses",
        },
        "search": {
            "coarse_step_m": 25.0,
            "coarse_candidates": len(coarse),
            "refinement_steps_m": [10.0, 5.0, 2.0, 1.0, 0.5],
            "training_samples": {key: len(value[0]) for key, value in train.items()},
            "evaluated_points": len(cache),
            "training_normalizers": normalizers,
        },
        "validation": {
            "geometry_checks": checks,
            "final_samples": {key: len(value[0]) for key, value in final_samples.items()},
            "all_feasible": all(geometry.feasible(poly, row["point_m"]) for row in finalists.values()),
            "arc_refinement": arc_refinement_check(selected),
        },
        "finalists": finalists,
        "position_effects": {
            "max_pairwise_distance_m": max(distances),
            "area_to_worst_distance_m": float(np.linalg.norm(points["area_mean"] - points["sample_worst"])),
            "radial_to_worst_distance_m": float(np.linalg.norm(points["radial_mean"] - points["sample_worst"])),
        },
        "code_sha256": {},
        "runtime": {
            "seconds": time.perf_counter() - started,
            "python": sys.version,
            "numpy": np.__version__,
        },
    }
    for path in (Path(__file__).resolve(), Path(geometry.__file__).resolve()):
        result["code_sha256"][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()

    folder = ROOT / "outputs" / "q2"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metric_tradeoff.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "metric_tradeoff.md").write_text(build_report(result), encoding="utf-8")
    print("finished", json.dumps(result["position_effects"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
