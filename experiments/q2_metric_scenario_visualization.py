"""绘制面积平均半径方案与离散最坏半径方案的差异场景。

复现：python experiments/q2_metric_scenario_visualization.py
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import q2_strategy_comparison as geometry
from q2_metric_tradeoff import scenario_values


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "q2"
FONT_PATH = Path("C:/Windows/Fonts/msyh.ttc")

BG = "#fafafa"
INK = "#202124"
MUTED = "#60646c"
GRID = "#d9dce1"
MEAN = "#e76f51"
ROBUST = "#277da1"
SOURCE = "#2a9d55"
REGION = "#b7bdc8"


def font(size, bold=False):
    path = Path("C:/Windows/Fonts/msyhbd.ttc") if bold else FONT_PATH
    return ImageFont.truetype(str(path), size)


def mapper(box, bounds):
    left, top, right, bottom = box
    xmin, xmax, ymin, ymax = bounds

    def transform(point):
        x, y = point
        px = left + (x - xmin) / (xmax - xmin) * (right - left)
        py = bottom - (y - ymin) / (ymax - ymin) * (bottom - top)
        return px, py

    return transform


def equal_scale_bounds(bounds, plot_box):
    """扩展数据边界，使横纵坐标每米使用相同像素尺度。"""
    xmin, xmax, ymin, ymax = bounds
    width = plot_box[2] - plot_box[0]
    height = plot_box[3] - plot_box[1]
    data_ratio = (xmax - xmin) / (ymax - ymin)
    plot_ratio = width / height
    if data_ratio < plot_ratio:
        target = (ymax - ymin) * plot_ratio
        center = (xmin + xmax) / 2
        xmin, xmax = center - target / 2, center + target / 2
    else:
        target = (xmax - xmin) / plot_ratio
        center = (ymin + ymax) / 2
        ymin, ymax = center - target / 2, center + target / 2
    return xmin, xmax, ymin, ymax


def panel_frame(draw, box, title, subtitle=None):
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=18, fill="#ffffff", outline="#d5d8de", width=2)
    draw.text((left + 24, top + 18), title, font=font(30, True), fill=INK)
    if subtitle:
        draw.text((left + 24, top + 58), subtitle, font=font(20), fill=MUTED)


def draw_axes(draw, plot_box, bounds, x_label, y_label, x_ticks, y_ticks):
    left, top, right, bottom = plot_box
    tr = mapper(plot_box, bounds)
    for value in x_ticks:
        x, _ = tr((value, bounds[2]))
        draw.line((x, top, x, bottom), fill=GRID, width=1)
        label = f"{value:g}"
        w = draw.textlength(label, font=font(17))
        draw.text((x - w / 2, bottom + 8), label, font=font(17), fill=MUTED)
    for value in y_ticks:
        _, y = tr((bounds[0], value))
        draw.line((left, y, right, y), fill=GRID, width=1)
        label = f"{value:g}"
        w = draw.textlength(label, font=font(17))
        draw.text((left - w - 10, y - 10), label, font=font(17), fill=MUTED)
    draw.rectangle(plot_box, outline="#aeb3bb", width=2)
    w = draw.textlength(x_label, font=font(19))
    draw.text(((left + right - w) / 2, bottom + 38), x_label, font=font(19), fill=INK)
    draw.text((left, top - 29), y_label, font=font(19), fill=INK)
    return tr


def circle_points(center, radius, count=180):
    angles = np.linspace(0, 2 * math.pi, count, endpoint=False)
    return [(center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)) for a in angles]


def scenario_geometry(poly, point, source, error):
    values = geometry.radii(
        poly,
        np.asarray(point),
        np.asarray([source]),
        np.asarray([error]),
        return_polys=True,
    )
    radii, centers, polygons, counts = values
    return {
        "radius": float(radii[0]),
        "center": centers[0].copy(),
        "polygon": polygons[0, : counts[0]].copy(),
    }


def draw_overview(image, box, poly, mean_point, robust_point):
    draw = ImageDraw.Draw(image)
    panel_frame(draw, box, "两个指标把第二点推向不同方向", "所有候选仍位于保证二次接收的上边界")
    plot = (box[0] + 85, box[1] + 105, box[2] - 30, box[3] - 70)
    bounds = equal_scale_bounds((-50, 1550, -80, 720), plot)
    tr = draw_axes(draw, plot, bounds, "东向 x / 米", "北向 y / 米", [0, 500, 1000, 1500], [0, 300, 600])

    # 首次定位扇形与保守接收边界。
    ImageDraw.Draw(image, "RGBA").polygon([tr(p) for p in poly], fill=(183, 189, 200, 95))
    boundary = []
    for x in np.linspace(0, 1500, 500):
        upper = geometry.safe_b(poly, float(x))
        if upper is not None:
            boundary.append(tr((x, upper)))
    if len(boundary) > 1:
        draw.line(boundary, fill="#777e89", width=4)

    draw.ellipse((*np.subtract(tr((0, 0)), (7, 7)), *np.add(tr((0, 0)), (7, 7))), fill=INK)
    draw.text(np.add(tr((0, 0)), (10, 6)), "第一次检测点", font=font(18), fill=INK)
    for point, color, label, shape in [
        (mean_point, MEAN, "面积平均最优 (870, 502)", "circle"),
        (robust_point, ROBUST, "最坏值最优 (843, 546)", "square"),
    ]:
        px, py = tr(point)
        if shape == "circle":
            draw.ellipse((px - 10, py - 10, px + 10, py + 10), fill=color, outline="#ffffff", width=2)
        else:
            draw.rectangle((px - 9, py - 9, px + 9, py + 9), fill=color, outline="#ffffff", width=2)
        draw.text((px + 14, py - 13), label, font=font(18), fill=color)

    distance = float(np.linalg.norm(np.asarray(mean_point) - np.asarray(robust_point)))
    draw.text((box[0] + 105, box[3] - 48), f"两点相距 {distance:.1f} 米，但到原点的路程只差约 0.14 米", font=font(20, True), fill=INK)


def draw_distance_effect(image, box, source, delta):
    draw = ImageDraw.Draw(image)
    panel_frame(draw, box, "差异来自近端与远端场景的取舍", "纵轴 = 平均方案半径 − 最坏方案半径；正值表示最坏方案更好")
    plot = (box[0] + 95, box[1] + 115, box[2] - 35, box[3] - 70)
    ranges = np.linalg.norm(source, axis=1)
    bounds = (0, 1500, -2.0, 3.1)
    tr = draw_axes(draw, plot, bounds, "真实源距离 / 米", "半径差 / 米", [0, 300, 600, 900, 1200, 1500], [-2, -1, 0, 1, 2, 3])
    bins = np.linspace(0, 1500, 26)
    centers, means, lows, highs = [], [], [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (ranges >= lo) & (ranges < hi)
        if not np.any(mask):
            continue
        values = delta[mask]
        centers.append((lo + hi) / 2)
        means.append(float(values.mean()))
        lows.append(float(np.quantile(values, 0.1)))
        highs.append(float(np.quantile(values, 0.9)))
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    band = [tr(p) for p in zip(centers, highs)] + [tr(p) for p in reversed(list(zip(centers, lows)))]
    odraw.polygon(band, fill=(39, 125, 161, 40))
    image.alpha_composite(overlay) if image.mode == "RGBA" else image.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(image)
    draw.line([tr((bounds[0], 0)), tr((bounds[1], 0))], fill="#7c828c", width=3)
    draw.line([tr(p) for p in zip(centers, means)], fill=ROBUST, width=5)
    for p in zip(centers, means):
        x, y = tr(p)
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=ROBUST)
    draw.text((plot[0] + 15, plot[1] + 15), "近端：最坏值方案通常更小", font=font(19, True), fill=ROBUST)
    draw.text((plot[2] - 280, plot[3] - 38), "远端：面积平均方案通常更小", font=font(19, True), fill=MEAN)


def draw_scenario(image, box, title, scenario, mean_geo, robust_geo):
    draw = ImageDraw.Draw(image)
    source = np.asarray(scenario["source"])
    angle = math.degrees(math.atan2(source[1], source[0]))
    radius = float(np.linalg.norm(source))
    subtitle = (
        f"源距 {radius:.1f} m，方向 {angle:.3f}°，第二次误差 {math.degrees(scenario['error']):.3f}°"
    )
    panel_frame(draw, box, title, subtitle)

    all_points = np.vstack([
        mean_geo["polygon"], robust_geo["polygon"], source[None, :],
        np.asarray(circle_points(mean_geo["center"], mean_geo["radius"])),
        np.asarray(circle_points(robust_geo["center"], robust_geo["radius"])),
    ])
    xmin, ymin = all_points.min(axis=0)
    xmax, ymax = all_points.max(axis=0)
    span = max(xmax - xmin, ymax - ymin, 20.0)
    margin = 0.13 * span
    bounds = (xmin - margin, xmax + margin, ymin - margin, ymax + margin)
    plot = (box[0] + 105, box[1] + 115, box[2] - 35, box[3] - 105)
    bounds = equal_scale_bounds(bounds, plot)
    tr = mapper(plot, bounds)
    draw.rectangle(plot, outline="#aeb3bb", width=2)

    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.polygon([tr(p) for p in mean_geo["polygon"]], fill=(231, 111, 81, 55), outline=(231, 111, 81, 200), width=4)
    odraw.polygon([tr(p) for p in robust_geo["polygon"]], fill=(39, 125, 161, 55), outline=(39, 125, 161, 200), width=4)
    image.paste(overlay, (0, 0), overlay)
    draw = ImageDraw.Draw(image)
    draw.line([tr(p) for p in circle_points(mean_geo["center"], mean_geo["radius"]) + [circle_points(mean_geo["center"], mean_geo["radius"])[0]]], fill=MEAN, width=4)
    draw.line([tr(p) for p in circle_points(robust_geo["center"], robust_geo["radius"]) + [circle_points(robust_geo["center"], robust_geo["radius"])[0]]], fill=ROBUST, width=4)
    for geo, color in ((mean_geo, MEAN), (robust_geo, ROBUST)):
        cx, cy = tr(geo["center"])
        draw.line((cx - 7, cy, cx + 7, cy), fill=color, width=3)
        draw.line((cx, cy - 7, cx, cy + 7), fill=color, width=3)
    sx, sy = tr(source)
    draw.ellipse((sx - 8, sy - 8, sx + 8, sy + 8), fill=SOURCE, outline="#ffffff", width=2)
    draw.text((sx + 10, sy - 16), "真实源", font=font(18), fill=SOURCE)

    line_y = box[3] - 78
    draw.ellipse((box[0] + 28, line_y - 2, box[0] + 44, line_y + 14), outline=MEAN, width=4)
    draw.text((box[0] + 55, line_y - 8), f"面积平均方案：{mean_geo['radius']:.3f} m", font=font(20, True), fill=MEAN)
    draw.rectangle((box[0] + 360, line_y - 2, box[0] + 376, line_y + 14), outline=ROBUST, width=4)
    draw.text((box[0] + 387, line_y - 8), f"最坏值方案：{robust_geo['radius']:.3f} m", font=font(20, True), fill=ROBUST)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    poly = geometry.initial_polygon()
    mean_point = np.array([870.0, geometry.safe_b(poly, 870.0)])
    robust_point = np.array([843.0, geometry.safe_b(poly, 843.0)])
    samples = geometry.source_grid(320, 17, 17, "area", False)
    source, errors = samples
    mean_radii = scenario_values(poly, mean_point, samples)
    robust_radii = scenario_values(poly, robust_point, samples)
    delta = mean_radii - robust_radii

    cases = {
        "robust_advantage": int(np.argmax(delta)),
        "mean_advantage": int(np.argmin(delta)),
    }
    details = {}
    for name, index in cases.items():
        src = source[index]
        err = errors[index]
        details[name] = {
            "index": index,
            "source": src.tolist(),
            "source_range_m": float(np.linalg.norm(src)),
            "source_angle_deg": float(math.degrees(math.atan2(src[1], src[0]))),
            "error_deg": float(math.degrees(err)),
            "mean_strategy_radius_m": float(mean_radii[index]),
            "robust_strategy_radius_m": float(robust_radii[index]),
            "mean_minus_robust_m": float(delta[index]),
            "error": float(err),
        }

    image = Image.new("RGB", (1900, 1500), BG)
    draw = ImageDraw.Draw(image)
    draw.text((60, 32), "第二检测点：平均表现与最坏表现的取舍", font=font(42, True), fill=INK)
    draw.text((60, 88), "同一真实源与同一测向误差下，比较二次定位区域及其最小包围圆", font=font(24), fill=MUTED)

    draw_overview(image, (50, 140, 935, 690), poly, mean_point, robust_point)
    draw_distance_effect(image, (965, 140, 1850, 690), source, delta)

    robust_case = details["robust_advantage"]
    mean_case = details["mean_advantage"]
    robust_source = np.asarray(robust_case["source"])
    mean_source = np.asarray(mean_case["source"])
    draw_scenario(
        image,
        (50, 725, 935, 1450),
        "近端代表情形：最坏值方案明显占优",
        robust_case,
        scenario_geometry(poly, mean_point, robust_source, robust_case["error"]),
        scenario_geometry(poly, robust_point, robust_source, robust_case["error"]),
    )
    draw_scenario(
        image,
        (965, 725, 1850, 1450),
        "远端代表情形：面积平均方案明显占优",
        mean_case,
        scenario_geometry(poly, mean_point, mean_source, mean_case["error"]),
        scenario_geometry(poly, robust_point, mean_source, mean_case["error"]),
    )

    image_path = OUTPUT / "q2_metric_scenario_comparison.png"
    image.save(image_path, quality=95)
    record = {
        "status": "探索性可视化，代表情形从面积均匀加密网格中按两方案半径差自动选择",
        "mean_strategy_point_m": mean_point.tolist(),
        "robust_strategy_point_m": robust_point.tolist(),
        "sample_count": len(source),
        "mean_minus_robust_summary_m": {
            "mean": float(delta.mean()),
            "positive_fraction": float(np.mean(delta > 0)),
            "quantiles": {str(q): float(np.quantile(delta, q)) for q in (0, 0.05, 0.5, 0.95, 1)},
        },
        "representative_cases": {
            key: {k: v for k, v in value.items() if k != "error"}
            for key, value in details.items()
        },
        "code_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                Path(__file__).resolve(),
                Path(geometry.__file__).resolve(),
                ROOT / "experiments" / "q2_metric_tradeoff.py",
            )
        },
    }
    (OUTPUT / "q2_metric_scenario_comparison.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(image_path)
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
