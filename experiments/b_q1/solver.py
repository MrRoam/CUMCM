"""第一问入口：纯 ±1° 测向扇形交会；长度为米，东起逆时针角度。"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from experiments.b_overnight import q2_geometry as shared

ERROR_DEG = 1.0
DISTANCE_TOLERANCE_M = 1e-7
PARALLEL_TOLERANCE = 1e-12  # 共有算法中的无量纲阈值；不是角度误差。


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " 必须是有限数值")
    try:
        result = float(value)
    except (OverflowError, ValueError):
        raise ValueError(label + " 必须是有限数值") from None
    if not math.isfinite(result):
        raise ValueError(label + " 必须是有限数值")
    return result


def validate_observations(observations):
    if not isinstance(observations, (list, tuple)):
        raise ValueError("observations 必须是观测列表")
    clean = []
    for i, row in enumerate(observations):
        if not isinstance(row, dict):
            raise ValueError(f"观测 {i} 必须是对象")
        position = row.get("position_m")
        if not isinstance(position, (list, tuple)) or len(position) != 2:
            raise ValueError(f"观测 {i} 的 position_m 必须有两个坐标")
        p = tuple(_number(x, f"观测 {i} 坐标") for x in position)
        theta = _number(row.get("bearing_deg"), f"观测 {i} 示向度")
        if not 0 <= theta < 360:
            raise ValueError("示向度应在 [0,360) 度内")
        clean.append({"position_m": p, "bearing_deg": theta})
    return clean


def solve(observations):
    """输入同一源的观测；返回状态、逆时针顶点、直径及最远端点。

    空集的 diameter_m 为 None，无界集为 math.inf；有限退化集正常计算。
    使用局部原点减少公共平移造成的消减误差，不添加任何空间边框。
    """
    rows = validate_observations(observations)
    origin = rows[0]["position_m"] if rows else (0.0, 0.0)
    halfplanes = []
    for row in rows:
        p = tuple(x - o for x, o in zip(row["position_m"], origin))
        if not all(math.isfinite(x) for x in p):
            raise ValueError("坐标差溢出，输入超出浮点计算范围")
        halfplanes.extend(shared.bearing_halfplanes(p, row["bearing_deg"], ERROR_DEG))
    region = shared.halfplane_region(halfplanes, tolerance=DISTANCE_TOLERANCE_M)
    status = region["kind"]
    vertices = region["vertices"]
    if any(not all(math.isfinite(x) for x in p) for p in vertices):
        raise ArithmeticError("边界交点溢出，无法可靠计算")
    if status not in ("empty", "unbounded") and not vertices:
        raise ArithmeticError("数值分类矛盾：有界非空区域没有顶点")
    pair = None
    if status == "empty":
        diameter = None
    elif status == "unbounded":
        diameter = math.inf
    else:
        diameter, pair = shared.polygon_diameter(vertices)
    absolute = lambda p: [p[0] + origin[0], p[1] + origin[1]] if p is not None else None
    return {
        "status": status,
        "vertices_m": [absolute(p) for p in vertices],
        "diameter_m": diameter,
        "diameter_endpoints_m": [absolute(p) for p in pair] if pair else None,
        "feasible_point_m": absolute(region["witness"]),
        "recession_direction": region.get("recession_direction"),
        "observation_count": len(rows),
        "model": "intersection_of_forward_bearing_wedges",
        "error_half_width_deg": ERROR_DEG,
        "numerics": {
            "distance_tolerance_m": DISTANCE_TOLERANCE_M,
            "parallel_tolerance": PARALLEL_TOLERANCE,
            "local_origin_m": list(origin),
            "note": "双精度近似；接近平行阈值、容差尺度的退化判别不构成精确算术证书。",
        },
    }


def json_safe(value):
    """以标准 JSON 字符串表示正无穷，不生成非标准 Infinity 数值。"""
    if isinstance(value, float) and math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


def main():
    # Windows终端和重定向文件均使用UTF-8，避免中文诊断信息因系统代码页乱码。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="含 observations 列表的 JSON")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict) or "observations" not in data:
            raise ValueError("输入对象必须含 observations")
        result = solve(data["observations"])
        text = json.dumps(json_safe(result), ensure_ascii=False, indent=2, allow_nan=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
    except (ValueError, ArithmeticError, OSError) as exc:
        parser.exit(2, f"输入或计算错误：{exc}\n")


if __name__ == "__main__":
    main()
