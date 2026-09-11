"""从全局尺度绘制第二问两种平均口径造成的选点差异。

复现：python experiments/q2_large_scale_position_visualization.py
输出：outputs/q2/q2_large_scale_position_difference.png
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import q2_strategy_comparison as geometry


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "q2"
FONT_REGULAR = Path("C:/Windows/Fonts/msyh.ttc")
FONT_BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")

BG = "#f7f8fa"
INK = "#1f2933"
MUTED = "#5f6b76"
GRID = "#dce1e7"
AXIS = "#8a949e"
AREA = "#e76f51"
RADIAL = "#277da1"
FEASIBLE_FILL = (111, 179, 154, 64)
FEASIBLE_EDGE = "#4d9a7c"
P1_FILL = (152, 162, 179, 90)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def transform_factory(plot_box, bounds):
    left, top, right, bottom = plot_box
    xmin, xmax, ymin, ymax = bounds

    def transform(point):
        x, y = point
        return (
            left + (x - xmin) / (xmax - xmin) * (right - left),
            bottom - (y - ymin) / (ymax - ymin) * (bottom - top),
        )

    return transform


def feasible_upper_region(poly: np.ndarray, count: int = 1800) -> np.ndarray:
    """返回 y>=0 的保守二次接收候选区域边界。"""
    x_min = float(np.max(poly[:, 0] - 1000.0))
    x_max = float(np.min(poly[:, 0] + 1000.0))
    upper = []
    lower = []
    for x in np.linspace(x_min, x_max, count):
        dx = poly[:, 0] - x
        if np.any(np.abs(dx) > 1000.0):
            continue
        root = np.sqrt(np.maximum(0.0, 1_000_000.0 - dx * dx))
        lo = max(0.0, float(np.max(poly[:, 1] - root)))
        hi = float(np.min(poly[:, 1] + root))
        if lo <= hi:
            lower.append((x, lo))
            upper.append((x, hi))
    return np.asarray(lower + upper[::-1])


def line_arrow(draw, start, end, color, width=5, head=14):
    draw.line((*start, *end), fill=color, width=width)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    a = (end[0] - head * ux + 0.55 * head * nx, end[1] - head * uy + 0.55 * head * ny)
    b = (end[0] - head * ux - 0.55 * head * nx, end[1] - head * uy - 0.55 * head * ny)
    draw.polygon([end, a, b], fill=color)


def rounded_label(draw, xy, lines, color, anchor="la"):
    title, detail = lines
    title_font = font(25, True)
    detail_font = font(20)
    title_w = draw.textlength(title, font=title_font)
    detail_w = draw.textlength(detail, font=detail_font)
    width = max(title_w, detail_w) + 34
    height = 76
    x, y = xy
    if anchor == "ra":
        x -= width
    draw.rounded_rectangle((x, y, x + width, y + height), radius=13,
                           fill="#ffffff", outline=color, width=3)
    draw.text((x + 17, y + 9), title, font=title_font, fill=color)
    draw.text((x + 17, y + 43), detail, font=detail_font, fill=MUTED)
    return x, y, x + width, y + height


def draw_dimension(draw, tr, first, second, label):
    p = np.asarray(first, dtype=float)
    q = np.asarray(second, dtype=float)
    delta = q - p
    normal = np.array([delta[1], -delta[0]], dtype=float)
    normal /= np.linalg.norm(normal)
    if normal[1] < 0:
        normal *= -1
    offset = 48.0 * normal
    a, b = p + offset, q + offset
    pa, pb = tr(a), tr(b)
    p0, q0 = tr(p), tr(q)
    draw.line((*p0, *pa), fill=MUTED, width=2)
    draw.line((*q0, *pb), fill=MUTED, width=2)
    line_arrow(draw, pa, pb, INK, width=3, head=12)
    line_arrow(draw, pb, pa, INK, width=3, head=12)
    mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
    text_font = font(26, True)
    text_w = draw.textlength(label, font=text_font)
    box = (mid[0] - text_w / 2 - 10, mid[1] - 39, mid[0] + text_w / 2 + 10, mid[1] - 5)
    draw.rounded_rectangle(box, radius=8, fill="#ffffff")
    draw.text((mid[0] - text_w / 2, mid[1] - 38), label, font=text_font, fill=INK)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    tradeoff_path = OUTPUT / "metric_tradeoff.json"
    data = json.loads(tradeoff_path.read_text(encoding="utf-8"))
    area_point = np.asarray(data["finalists"]["area_mean"]["point_m"], dtype=float)
    radial_point = np.asarray(data["finalists"]["radial_mean"]["point_m"], dtype=float)
    area_move = float(data["finalists"]["area_mean"]["move_distance_m"])
    radial_move = float(data["finalists"]["radial_mean"]["move_distance_m"])
    separation = float(np.linalg.norm(area_point - radial_point))
    angle_difference = abs(
        math.degrees(math.atan2(area_point[1], area_point[0]))
        - math.degrees(math.atan2(radial_point[1], radial_point[0]))
    )

    poly = geometry.initial_polygon()
    feasible_region = feasible_upper_region(poly)

    width, height = 1900, 1180
    image = Image.new("RGBA", (width, height), BG)
    draw = ImageDraw.Draw(image)

    draw.text((80, 42), "同一接收约束，不同“平均”定义使第二检测点相隔约145米",
              font=font(42, True), fill=INK)
    draw.text((82, 103),
              "橙色按扇形面积均匀取平均；蓝色按距离均匀取平均。两者不是“平均值与最坏值”的比较。",
              font=font(24), fill=MUTED)

    plot = (125, 205, 1775, 1082)
    bounds = (-65.0, 1535.0, -100.0, 750.3)
    tr = transform_factory(plot, bounds)

    # 网格、坐标和中心线。
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
    x0, y0 = tr((0, 0))
    x1, _ = tr((1500, 0))
    draw.line((x0, y0, x1, y0), fill=AXIS, width=3)

    # 首次定位扇形与二次接收可行域。
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.polygon([tr(p) for p in poly], fill=P1_FILL)
    odraw.polygon([tr(p) for p in feasible_region], fill=FEASIBLE_FILL)
    image.alpha_composite(overlay)
    draw = ImageDraw.Draw(image)
    draw.line([tr(p) for p in feasible_region] + [tr(feasible_region[0])],
              fill=FEASIBLE_EDGE, width=4)

    # 两条移动路线。
    origin = tr((0, 0))
    line_arrow(draw, origin, tr(area_point), AREA, width=6, head=18)
    line_arrow(draw, origin, tr(radial_point), RADIAL, width=6, head=18)
    draw.ellipse((origin[0] - 9, origin[1] - 9, origin[0] + 9, origin[1] + 9),
                 fill=INK, outline="#ffffff", width=2)
    draw.text((origin[0] + 15, origin[1] + 12), "第一次检测点", font=font(21, True), fill=INK)

    # 两个第二检测点。
    ap = tr(area_point)
    rp = tr(radial_point)
    draw.ellipse((ap[0] - 13, ap[1] - 13, ap[0] + 13, ap[1] + 13),
                 fill=AREA, outline="#ffffff", width=3)
    draw.rounded_rectangle((rp[0] - 12, rp[1] - 12, rp[0] + 12, rp[1] + 12),
                           radius=3, fill=RADIAL, outline="#ffffff", width=3)
    draw_dimension(draw, tr, area_point, radial_point, f"两点直线距离 {separation:.1f} m")

    # 标签和解释。
    area_box = rounded_label(
        draw, tr((1060, 430)),
        ("面积均匀平均最优", f"({area_point[0]:.1f}, {area_point[1]:.1f}) m · 更向前"),
        AREA,
    )
    radial_box = rounded_label(
        draw, tr((610, 720)),
        ("径向均匀平均最优", f"({radial_point[0]:.1f}, {radial_point[1]:.1f}) m · 更向侧方"),
        RADIAL,
    )
    draw.line((*ap, area_box[0], (area_box[1] + area_box[3]) / 2), fill=AREA, width=2)
    draw.line((*rp, radial_box[2], (radial_box[1] + radial_box[3]) / 2), fill=RADIAL, width=2)

    draw.text(tr((1110, 42)), "第一次测向所得可能区域（±1°）", font=font(20), fill="#6d7480")
    region_label = tr((530, 250))
    draw.rounded_rectangle((region_label[0] - 12, region_label[1] - 8,
                            region_label[0] + 365, region_label[1] + 34),
                           radius=9, fill=(255, 255, 255, 215))
    draw.text(region_label, "保证所有可能源点都能二次接收的候选区",
              font=font(20, True), fill=FEASIBLE_EDGE)

    # 底部结论条。
    conclusion_y = 1097
    draw.rounded_rectangle((360, conclusion_y, 1540, 1164), radius=16,
                           fill="#ffffff", outline="#cfd5dc", width=2)
    move_diff = abs(area_move - radial_move)
    time_diff = move_diff / 5.0
    summary = (
        f"位置方向差 {angle_difference:.2f}°，但两条路线都约 1004 m；"
        f"路程仅差 {move_diff:.2f} m（按 5 m/s 仅差 {time_diff:.2f} s）"
    )
    tw = draw.textlength(summary, font=font(23, True))
    draw.text(((width - tw) / 2, conclusion_y + 18), summary, font=font(23, True), fill=INK)

    png_path = OUTPUT / "q2_large_scale_position_difference.png"
    image.convert("RGB").save(png_path, quality=95)

    record = {
        "status": "探索性可视化，非正式模型结果",
        "comparison": "面积均匀平均半径最优 vs 径向均匀平均半径最优",
        "area_mean_point_m": area_point.tolist(),
        "radial_mean_point_m": radial_point.tolist(),
        "position_difference_m": separation,
        "bearing_difference_deg": angle_difference,
        "move_distance_m": {"area_mean": area_move, "radial_mean": radial_move},
        "move_distance_difference_m": move_diff,
        "move_time_difference_at_5mps_s": time_diff,
        "plot_bounds_m": list(bounds),
        "equal_xy_scale": True,
        "source": "outputs/q2/metric_tradeoff.json",
        "code_sha256": {
            str(Path("experiments/q2_large_scale_position_visualization.py")): sha256(Path(__file__)),
            str(Path("experiments/q2_strategy_comparison.py")): sha256(ROOT / "experiments" / "q2_strategy_comparison.py"),
            str(Path("outputs/q2/metric_tradeoff.json")): sha256(tradeoff_path),
        },
    }
    (OUTPUT / "q2_large_scale_position_difference.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
