"""面积均匀平均最小包围圆半径的第二检测点策略。"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .geometry import (
    area_uniform_grid,
    initial_outer_polygon,
    is_receive_feasible,
    localization_radii,
    upper_receive_boundary,
)


HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "strategy_config.json"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def local_selected_point(side: str = "left") -> np.ndarray:
    """返回以首次检测点为原点、首次示向为+x轴的局部选点。"""
    point = np.asarray(load_config()["selected_local_point_m"], dtype=float)
    if side == "right":
        point[1] *= -1.0
    elif side != "left":
        raise ValueError("side只能是left或right")
    return point


def recommend_second_point(
    first_point_m=(0.0, 0.0), bearing_deg: float = 0.0, side: str = "left"
):
    """把标准局部选点平移、旋转到全局坐标。

    仅当首次可能区域没有被1800米目标圆域等额外边界裁剪时可直接使用。
    """
    local = local_selected_point(side)
    angle = math.radians(float(bearing_deg))
    rotation = np.array(
        [[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]]
    )
    return np.asarray(first_point_m, dtype=float) + rotation @ local


def scenario_values(initial_poly, point, samples, chunk_size: int = 2048):
    sources, errors = samples
    point = np.asarray(point, dtype=float)
    return np.concatenate(
        [
            localization_radii(
                initial_poly,
                point,
                sources[start : start + chunk_size],
                errors[start : start + chunk_size],
            )
            for start in range(0, len(sources), chunk_size)
        ]
    )


def evaluate_point(point, radial_count=320, angle_count=17, error_count=17):
    """在独立面积均匀中点网格上评价一个局部坐标候选。"""
    poly = initial_outer_polygon()
    point = np.asarray(point, dtype=float)
    if not is_receive_feasible(poly, point):
        raise ValueError("候选点不满足1000米保守接收约束")
    values = scenario_values(
        poly,
        point,
        area_uniform_grid(radial_count, angle_count, error_count),
    )
    return {
        "point_m": point.tolist(),
        "sample_count": int(len(values)),
        "area_mean_radius_m": float(values.mean()),
        "p95_radius_m": float(np.quantile(values, 0.95)),
        "sample_max_radius_m": float(values.max()),
        "radius_le20_fraction": float(np.mean(values <= 20.0)),
        "move_distance_m": float(np.linalg.norm(point)),
        "move_seconds_at_5mps": float(np.linalg.norm(point) / 5.0),
        "receive_max_distance_m": float(
            np.max(np.linalg.norm(poly - point, axis=1))
        ),
    }


def _point_key(point):
    return tuple(round(float(value), 9) for value in point)


def search_area_mean(
    radial_count=24,
    angle_count=3,
    error_count=3,
    coarse_step_m=25.0,
    refinement_steps_m=(10.0, 5.0, 2.0, 1.0, 0.5),
):
    """按当前确定性粗网格与边界局部细化复算面积平均候选。

    返回当前搜索得到的最佳可行点，不声称连续全局最优。
    """
    poly = initial_outer_polygon()
    samples = area_uniform_grid(radial_count, angle_count, error_count)
    cache = {}

    def score(point):
        key = _point_key(point)
        if key not in cache:
            cache[key] = float(scenario_values(poly, key, samples).mean())
        return cache[key]

    candidates = []
    for x in np.arange(0.0, 1500.0 + coarse_step_m / 2.0, coarse_step_m):
        upper = upper_receive_boundary(poly, float(x))
        if upper is None:
            continue
        for y in list(np.arange(0.0, upper + 1e-9, coarse_step_m)) + [upper]:
            point = (float(x), float(y))
            if is_receive_feasible(poly, point):
                candidates.append(_point_key(point))
    candidates.append(_point_key(local_selected_point()))
    candidates = list(dict.fromkeys(candidates))
    current = min(candidates, key=score)
    current_score = score(current)

    for step in refinement_steps_m:
        for _ in range(30):
            x, y = current
            trials = [
                (x + dx * step, y + dy * step)
                for dx, dy in (
                    (1, 0),
                    (-1, 0),
                    (0, 1),
                    (0, -1),
                    (1, 1),
                    (1, -1),
                    (-1, 1),
                    (-1, -1),
                )
            ]
            for trial_x in (x - step, x, x + step):
                upper = upper_receive_boundary(poly, trial_x)
                if upper is not None:
                    trials.append((trial_x, upper))
            best_point, best_score = current, current_score
            for trial in trials:
                if trial[1] < -1e-9 or not is_receive_feasible(poly, trial):
                    continue
                trial = _point_key(trial)
                trial_score = score(trial)
                if trial_score < best_score - 1e-12:
                    best_point, best_score = trial, trial_score
            if best_point == current:
                break
            current, current_score = best_point, best_score
    return {
        "point_m": list(current),
        "training_area_mean_radius_m": current_score,
        "training_sample_count": len(samples[0]),
        "evaluated_point_count": len(cache),
        "continuous_global_optimum_proved": False,
    }
