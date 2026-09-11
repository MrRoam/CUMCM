"""第二问正式几何评价器。

长度单位均为米，角度在函数内部均为弧度。这里计算的是两次测向
误差带交集的最小包围圆半径，不是直径的一半。
"""

from __future__ import annotations

import itertools
import math

import numpy as np


ANGLE_ERROR_RAD = math.pi / 180.0
INNER_RADIUS_M = 5.0
OUTER_RADIUS_M = 1500.0
RECEIVE_RADIUS_M = 1000.0


def clip_polygon(poly: np.ndarray, normal: np.ndarray, bound: float) -> np.ndarray:
    """用 ``normal·x <= bound`` 裁剪凸多边形。"""
    output = []
    for start, end in zip(poly, np.roll(poly, -1, axis=0)):
        start_value = float(np.dot(start, normal) - bound)
        end_value = float(np.dot(end, normal) - bound)
        if (start_value <= 0.0) != (end_value <= 0.0):
            output.append(start + start_value / (start_value - end_value) * (end - start))
        if end_value <= 0.0:
            output.append(end)
    return np.asarray(output, dtype=float)


def initial_outer_polygon(arc_steps: int = 16) -> np.ndarray:
    """标准首次测向区域的凸外包多边形。

    标准局部坐标中第一次检测点为原点、示向中心线为+x轴。
    1500米圆弧使用切线外包，5米内弧使用端点弦外包。
    """
    eps = ANGLE_ERROR_RAD
    radius = OUTER_RADIUS_M
    poly = np.array(
        [
            [INNER_RADIUS_M * math.cos(eps), -INNER_RADIUS_M * math.sin(eps)],
            [radius * 1.001, -radius * 1.001 * math.tan(eps)],
            [radius * 1.001, radius * 1.001 * math.tan(eps)],
            [INNER_RADIUS_M * math.cos(eps), INNER_RADIUS_M * math.sin(eps)],
        ],
        dtype=float,
    )
    for angle in np.linspace(-eps, eps, arc_steps + 1):
        poly = clip_polygon(poly, np.array([math.cos(angle), math.sin(angle)]), radius)
    return poly


def _batch_clip(points, counts, normals, bounds):
    count, capacity, _ = points.shape
    rows = np.arange(count)[:, None]
    columns = np.arange(capacity)[None, :]
    next_columns = (columns + 1) % counts[:, None]
    ends = points[rows, next_columns]
    start_values = np.einsum("nvi,ni->nv", points, normals) - bounds[:, None]
    end_values = np.einsum("nvi,ni->nv", ends, normals) - bounds[:, None]
    valid = columns < counts[:, None]
    crossing = valid & ((start_values <= 0.0) != (end_values <= 0.0))
    keep_end = valid & (end_values <= 0.0)
    additions = crossing.astype(int) + keep_end.astype(int)
    offsets = np.cumsum(additions, axis=1) - additions
    output = np.zeros((count, capacity + 1, 2))
    row_index, column_index = np.where(crossing)
    fraction = start_values[row_index, column_index] / (
        start_values[row_index, column_index] - end_values[row_index, column_index]
    )
    output[row_index, offsets[row_index, column_index]] = (
        points[row_index, column_index]
        + fraction[:, None]
        * (ends[row_index, column_index] - points[row_index, column_index])
    )
    row_index, column_index = np.where(keep_end)
    output[
        row_index,
        offsets[row_index, column_index] + crossing[row_index, column_index],
    ] = ends[row_index, column_index]
    new_counts = additions.sum(axis=1)
    if np.any(new_counts < 1):
        raise ArithmeticError("非空测向区域被浮点裁剪错误地裁为空集")
    return output[:, : int(new_counts.max())], new_counts


def minimum_enclosing_circle(poly: np.ndarray):
    """枚举单点圆、直径圆和三点外接圆，返回最小包围圆。"""
    best = (float("inf"), None)
    candidates = [(point, 0.0) for point in poly]
    for first, second in itertools.combinations(poly, 2):
        center = (first + second) / 2.0
        candidates.append((center, float(np.sum((first - center) ** 2))))
    for first, second, third in itertools.combinations(poly, 3):
        matrix = 2.0 * np.array([second - first, third - first])
        if abs(float(np.linalg.det(matrix))) < 1e-12:
            continue
        center = np.linalg.solve(
            matrix,
            np.array(
                [
                    np.dot(second, second) - np.dot(first, first),
                    np.dot(third, third) - np.dot(first, first),
                ]
            ),
        )
        candidates.append((center, float(np.sum((first - center) ** 2))))
    for center, radius_squared in candidates:
        if radius_squared < best[0] and np.all(
            np.sum((poly - center) ** 2, axis=1) <= radius_squared + 1e-6
        ):
            best = (radius_squared, center)
    if best[1] is None:
        raise ArithmeticError("未能构造最小包围圆")
    return math.sqrt(best[0]), best[1]


def localization_radii(
    initial_poly: np.ndarray,
    second_point: np.ndarray,
    sources: np.ndarray,
    error_rads: np.ndarray,
    return_polygons: bool = False,
):
    """批量计算给定真实源和第二次误差下的最小包围圆半径。"""
    delta = sources - second_point
    measured_angles = np.arctan2(delta[:, 1], delta[:, 0]) + error_rads
    points = np.broadcast_to(
        initial_poly, (len(measured_angles), len(initial_poly), 2)
    ).copy()
    counts = np.full(len(measured_angles), len(initial_poly))
    for angle, sign in (
        (measured_angles - ANGLE_ERROR_RAD, 1),
        (measured_angles + ANGLE_ERROR_RAD, -1),
    ):
        normals = sign * np.column_stack([np.sin(angle), -np.cos(angle)])
        points, counts = _batch_clip(
            points, counts, normals, normals @ second_point + 1e-9
        )
    valid = np.arange(points.shape[1])[None, :] < counts[:, None]
    differences = points[:, :, None, :] - points[:, None, :, :]
    distances_squared = np.einsum("nvwi,nvwi->nvw", differences, differences)
    distances_squared = np.where(
        valid[:, :, None] & valid[:, None, :], distances_squared, -1.0
    )
    capacity = points.shape[1]
    pair = distances_squared.reshape(len(measured_angles), -1).argmax(axis=1)
    rows = np.arange(len(measured_angles))
    centers = (
        points[rows, pair // capacity] + points[rows, pair % capacity]
    ) / 2.0
    radii_squared = distances_squared[
        rows, pair // capacity, pair % capacity
    ] / 4.0
    far_squared = np.sum((points - centers[:, None, :]) ** 2, axis=2)
    needs_general_circle = np.any(
        valid & (far_squared > radii_squared[:, None] + 1e-7), axis=1
    )
    result = np.sqrt(np.maximum(0.0, radii_squared))
    for index in np.flatnonzero(needs_general_circle):
        result[index], centers[index] = minimum_enclosing_circle(
            points[index, : counts[index]]
        )
    result[np.linalg.norm(delta, axis=1) <= INNER_RADIUS_M] = INNER_RADIUS_M
    if return_polygons:
        return result, centers, points, counts
    return result


def area_uniform_grid(
    radial_count: int,
    angle_count: int,
    error_count: int,
    endpoints: bool = False,
):
    """构造面积均匀真源与[-1°,1°]均匀二次误差的确定性网格。"""
    if endpoints:
        unit = np.linspace(0.0, 1.0, radial_count)
        angles = np.linspace(-ANGLE_ERROR_RAD, ANGLE_ERROR_RAD, angle_count)
        errors = np.linspace(-ANGLE_ERROR_RAD, ANGLE_ERROR_RAD, error_count)
    else:
        unit = (np.arange(radial_count) + 0.5) / radial_count
        angles = -ANGLE_ERROR_RAD + 2.0 * ANGLE_ERROR_RAD * (
            np.arange(angle_count) + 0.5
        ) / angle_count
        errors = -ANGLE_ERROR_RAD + 2.0 * ANGLE_ERROR_RAD * (
            np.arange(error_count) + 0.5
        ) / error_count
    radii = np.sqrt(
        INNER_RADIUS_M**2
        + unit * (OUTER_RADIUS_M**2 - INNER_RADIUS_M**2)
    )
    radial_grid, angle_grid, error_grid = np.meshgrid(
        radii, angles, errors, indexing="ij"
    )
    sources = np.column_stack(
        [
            radial_grid.ravel() * np.cos(angle_grid.ravel()),
            radial_grid.ravel() * np.sin(angle_grid.ravel()),
        ]
    )
    return sources, error_grid.ravel()


def is_receive_feasible(initial_poly: np.ndarray, point) -> bool:
    return bool(
        np.max(np.linalg.norm(initial_poly - np.asarray(point), axis=1))
        <= RECEIVE_RADIUS_M + 1e-8
    )


def upper_receive_boundary(initial_poly: np.ndarray, x: float):
    """给定局部横坐标，返回上半平面接收可行域的最大纵坐标。"""
    dx = initial_poly[:, 0] - x
    if np.any(np.abs(dx) > RECEIVE_RADIUS_M):
        return None
    roots = np.sqrt(RECEIVE_RADIUS_M**2 - dx**2)
    lower = float(np.max(initial_poly[:, 1] - roots))
    upper = float(np.min(initial_poly[:, 1] + roots))
    return upper if upper >= max(0.0, lower) else None
