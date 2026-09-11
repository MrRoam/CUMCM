"""全局尺度绘制面积均匀平均值方案与离散最坏值方案。

复现：python experiments/q2_large_scale_mean_vs_worst.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import q2_strategy_comparison as geometry
from q2_large_scale_position_visualization import (
    AXIS,
    BG,
    FEASIBLE_EDGE,
    FEASIBLE_FILL,
    GRID,
    INK,
    MUTED,
    P1_FILL,
    draw_dimension,
    feasible_upper_region,
    font,
    line_arrow,
    rounded_label,
    transform_factory,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "q2"
AVERAGE = "#e76f51"
WORST = "#277da1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    tradeoff_path = OUTPUT / "metric_tradeoff.json"
    data = json.loads(tradeoff_path.read_text(encoding="utf-8"))
    average = data["finalists"]["area_mean"]
    worst = data["finalists"]["sample_worst"]
    average_point = np.asarray(average["point_m"], dtype=float)
    worst_point = np.asarray(worst["point_m"], dtype=float)

    separation = float(np.linalg.norm(average_point - worst_point))
    move_difference = abs(float(average["move_distance_m"]) - float(worst["move_distance_m"]))
    time_difference = move_difference / 5.0
    mean_penalty = float(worst["area_mean_m"] - average["area_mean_m"])
    worst_gain = float(average["sample_worst_m"] - worst["sample_worst_m"])
    mean_penalty_pct = 100.0 * mean_penalty / float(average["area_mean_m"])
    worst_gain_pct = 100.0 * worst_gain / float(average["sample_worst_m"])

    poly = geometry.initial_polygon()
    feasible_region = feasible_upper_region(poly)

    width, height = 1900, 1180
    image = Image.new("RGBA", (width, height), BG)
    draw = ImageDraw.Draw(image)
    draw.text((80, 40), "面积均匀平均方案 vs 最坏值方案：第二检测点相距51.5米",
              font=font(42, True), fill=INK)
    draw.text((82, 101),
              "两种策略使用相同的1000米接收约束；蓝色“最坏值”仍是当前加密网格上的最大值。",
              font=font(24), fill=MUTED)

    plot = (125, 205, 1775, 1030)
    bounds = (-65.0, 1535.0, -75.0, 725.0)
    tr = transform_factory(plot, bounds)

    for x in [0, 250, 500, 750, 1000, 1250, 1500]:
        px, _ = tr((x, 0))
        draw.line((px, plot[1], px, plot[3]), fill=GRID, width=1)
        label = str(x)
        tw = draw.textlength(label, font=font(18))
        draw.text((px - tw / 2, plot[3] + 9), label, font=font(18), fill=MUTED)
    for y in [0, 200, 400, 600]:
        _, py = tr((0, y))
        draw.line((plot[0], py, plot[2], py), fill=GRID, width=1)
        label = str(y)
        tw = draw.textlength(label, font=font(18))
        draw.text((plot[0] - tw - 11, py - 11), label, font=font(18), fill=MUTED)
    draw.rectangle(plot, outline="#adb5bd", width=2)
    draw.text((plot[2] - 170, plot[3] + 42), "x / 米", font=font(21), fill=INK)
    draw.text((plot[0] - 2, plot[1] - 34), "y / 米", font=font(21), fill=INK)
    origin = tr((0, 0))
    center_end = tr((1500, 0))
    draw.line((*origin, *center_end), fill=AXIS, width=3)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.polygon([tr(p) for p in poly], fill=P1_FILL)
    odraw.polygon([tr(p) for p in feasible_region], fill=FEASIBLE_FILL)
    image.alpha_composite(overlay)
    draw = ImageDraw.Draw(image)
    draw.line([tr(p) for p in feasible_region] + [tr(feasible_region[0])],
              fill=FEASIBLE_EDGE, width=4)

    # 路线几乎重合，先画平均方案，再用稍细的最坏值方案覆盖其上方。
    line_arrow(draw, origin, tr(average_point), AVERAGE, width=9, head=19)
    line_arrow(draw, origin, tr(worst_point), WORST, width=5, head=17)
    draw.ellipse((origin[0] - 9, origin[1] - 9, origin[0] + 9, origin[1] + 9),
                 fill=INK, outline="#ffffff", width=2)
    draw.text((origin[0] + 15, origin[1] + 12), "第一次检测点", font=font(21, True), fill=INK)

    ap = tr(average_point)
    wp = tr(worst_point)
    draw.ellipse((ap[0] - 13, ap[1] - 13, ap[0] + 13, ap[1] + 13),
                 fill=AVERAGE, outline="#ffffff", width=3)
    draw.rounded_rectangle((wp[0] - 12, wp[1] - 12, wp[0] + 12, wp[1] + 12),
                           radius=3, fill=WORST, outline="#ffffff", width=3)
    draw_dimension(draw, tr, average_point, worst_point, f"两点相距 {separation:.1f} m")

    average_box = rounded_label(
        draw, tr((1060, 430)),
        ("最小面积平均半径", f"({average_point[0]:.1f}, {average_point[1]:.1f}) m"),
        AVERAGE,
    )
    worst_box = rounded_label(
        draw, tr((650, 690)),
        ("最小离散最坏半径", f"({worst_point[0]:.1f}, {worst_point[1]:.1f}) m"),
        WORST,
    )
    draw.line((*ap, average_box[0], (average_box[1] + average_box[3]) / 2), fill=AVERAGE, width=2)
    draw.line((*wp, worst_box[2], (worst_box[1] + worst_box[3]) / 2), fill=WORST, width=2)

    region_label = tr((520, 225))
    draw.rounded_rectangle((region_label[0] - 12, region_label[1] - 8,
                            region_label[0] + 365, region_label[1] + 34),
                           radius=9, fill=(255, 255, 255, 215))
    draw.text(region_label, "保证所有可能源点都能二次接收的候选区",
              font=font(20, True), fill=FEASIBLE_EDGE)
    draw.text(tr((1110, 36)), "第一次测向所得可能区域（±1°）",
              font=font(20), fill="#6d7480")

    # 图下直接给出对决策最重要的变化量。
    band_y = 1068
    draw.rounded_rectangle((170, band_y, 1730, 1164), radius=16,
                           fill="#ffffff", outline="#cfd5dc", width=2)
    left = (
        f"改用最坏值方案：最坏半径下降 {worst_gain:.3f} m（{worst_gain_pct:.2f}%）"
    )
    right = (
        f"代价：面积平均半径上升 {mean_penalty:.3f} m（{mean_penalty_pct:.2f}%）"
    )
    draw.text((215, band_y + 14), left, font=font(23, True), fill=WORST)
    draw.text((1020, band_y + 14), right, font=font(23, True), fill=AVERAGE)
    travel = (
        f"移动路程仅差 {move_difference:.3f} m；按 5 m/s 计，时间仅差 {time_difference:.3f} s"
    )
    tw = draw.textlength(travel, font=font(22))
    draw.text(((width - tw) / 2, band_y + 53), travel, font=font(22), fill=INK)

    png_path = OUTPUT / "q2_large_scale_mean_vs_worst.png"
    image.convert("RGB").save(png_path, quality=95)

    record = {
        "status": "探索性可视化；最坏值是有限加密网格最大值",
        "comparison": "面积均匀平均半径最优 vs 离散最坏半径最优",
        "area_mean_point_m": average_point.tolist(),
        "sample_worst_point_m": worst_point.tolist(),
        "position_difference_m": separation,
        "move_distance_m": {
            "area_mean": float(average["move_distance_m"]),
            "sample_worst": float(worst["move_distance_m"]),
        },
        "move_distance_difference_m": move_difference,
        "move_time_difference_at_5mps_s": time_difference,
        "tradeoff": {
            "sample_worst_radius_improvement_m": worst_gain,
            "sample_worst_radius_improvement_pct": worst_gain_pct,
            "area_mean_radius_penalty_m": mean_penalty,
            "area_mean_radius_penalty_pct": mean_penalty_pct,
        },
        "equal_xy_scale": True,
        "source": "outputs/q2/metric_tradeoff.json",
        "code_sha256": {
            "experiments/q2_large_scale_mean_vs_worst.py": sha256(Path(__file__)),
            "experiments/q2_strategy_comparison.py": sha256(ROOT / "experiments" / "q2_strategy_comparison.py"),
            "outputs/q2/metric_tradeoff.json": sha256(tradeoff_path),
        },
    }
    (OUTPUT / "q2_large_scale_mean_vs_worst.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
