"""B 题第一问三种区域构造算法的同口径对照。

比较对象：
A. src.q1 当前的极角排序 + 双端队列；
B. 枚举全部直线对交点，再逐约束排除；
C. 从有证明的辅助框开始，按输入顺序逐半平面裁剪多边形。

三者使用相同 HalfPlane/Fraction 表示，计时包含区域构造和同一个旋转卡壳
直径函数，不包含输入生成和 JSON 写盘。此脚本是探索性基准，不是官方测试。
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import statistics
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.q1.geometry import HalfPlane, cross, diameter, halfplane_intersection, intersection


def coefficient_bound(planes: list[HalfPlane]) -> int:
    magnitude = max(1, *(abs(v) for p in planes for v in (p.a, p.b, p.c)))
    return 2 * magnitude * magnitude + 1


def clean_ring(points):
    out = []
    for p in points:
        if not out or p != out[-1]:
            out.append(p)
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    # 删除落在相邻边之间的共线点，保持与方法 A 的顶点定义一致。
    changed = True
    while changed and len(out) >= 3:
        changed = False
        keep = []
        for i, p in enumerate(out):
            if cross((p[0] - out[i - 1][0], p[1] - out[i - 1][1]),
                     (out[(i + 1) % len(out)][0] - p[0], out[(i + 1) % len(out)][1] - p[1])) == 0:
                changed = True
            else:
                keep.append(p)
        out = keep
    return out


def order_vertices(points):
    if len(points) <= 2:
        return sorted(points)
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return sorted(points, key=lambda p: math.atan2(float(p[1] - cy), float(p[0] - cx)))


def solve_a(planes):
    region = halfplane_intersection(planes)
    if region.status != "polygon":
        raise ValueError(f"基准仅比较有界非退化输入，实际为 {region.status}")
    d2 = diameter(region.vertices)[0]
    return region.vertices, d2, {"intersections": region.stats["intersections"]}


def solve_b_all_pairs(planes):
    vertices = set()
    pair_intersections = feasibility_tests = 0
    for i, a in enumerate(planes):
        for b in planes[i + 1:]:
            pair_intersections += 1
            p = intersection(a, b)
            if p is None:
                continue
            feasible = True
            for h in planes:
                feasibility_tests += 1
                if h.slack(p) < 0:
                    feasible = False
                    break
            if feasible:
                vertices.add(p)
    ordered = clean_ring(order_vertices(vertices))
    if len(ordered) < 3:
        raise ValueError("全配对法没有得到有界非退化多边形")
    return ordered, diameter(ordered)[0], {
        "pair_intersections": pair_intersections,
        "feasibility_tests": feasibility_tests,
    }


def clip_polygon(vertices, h, counters):
    if not vertices:
        return []
    result = []
    counters["edge_scans"] += len(vertices)
    for i, q in enumerate(vertices):
        p = vertices[i - 1]
        sp, sq = h.slack(p), h.slack(q)
        inside_p, inside_q = sp >= 0, sq >= 0
        if inside_p != inside_q:
            t = Fraction(sp) / Fraction(sp - sq)
            result.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
            counters["intersections"] += 1
        if inside_q:
            result.append(q)
    return clean_ring(result)


def solve_c_incremental(planes):
    bound = coefficient_bound(planes)
    vertices = [(-bound, -bound), (bound, -bound), (bound, bound), (-bound, bound)]
    counters = {"edge_scans": 0, "intersections": 0, "peak_vertices": 4,
                "sum_vertices_before_update": 0}
    for h in planes:
        counters["sum_vertices_before_update"] += len(vertices)
        vertices = clip_polygon(vertices, h, counters)
        counters["peak_vertices"] = max(counters["peak_vertices"], len(vertices))
        if not vertices:
            break
    if len(vertices) < 3 or any(abs(x) == bound or abs(y) == bound for x, y in vertices):
        raise ValueError("增量法没有得到有界非退化多边形")
    return vertices, diameter(vertices)[0], counters


def active_polygon(size: int):
    """抛物线链 + 上方弦；每条输入约束均成为最终边界。"""
    points = [(i, i * i) for i in range(-(size // 2), size - size // 2)]
    planes = []
    for i, p in enumerate(points):
        q = points[(i + 1) % len(points)]
        dx, dy = q[0] - p[0], q[1] - p[1]
        planes.append(HalfPlane(dy, -dx, dy * p[0] - dx * p[1], f"active:{i}"))
    return planes


def mostly_redundant(size: int):
    planes = [HalfPlane(-1, 0, 100, "left"), HalfPlane(1, 0, 100, "right"),
              HalfPlane(0, -1, 100, "bottom"), HalfPlane(0, 1, 100, "top")]
    rng = random.Random(20260911 + size)
    seen = {(1, 0), (-1, 0), (0, 1), (0, -1)}
    while len(planes) < size:
        a, b = rng.randint(-10000, 10000), rng.randint(-10000, 10000)
        if not (a or b):
            continue
        g = math.gcd(a, b)
        a, b = a // g, b // g
        if (a, b) in seen:
            continue
        seen.add((a, b))
        planes.append(HalfPlane(a, b, 1000 * (abs(a) + abs(b)), f"loose:{len(planes)}"))
    return planes


def fingerprint(vertices):
    return sorted((str(x), str(y)) for x, y in vertices)


def one_case(scenario, size, repeats):
    original = active_polygon(size) if scenario.startswith("active") else mostly_redundant(size)
    if scenario == "active_shuffled":
        random.Random(731 + size).shuffle(original)
    methods = [("A_sorted_deque", solve_a), ("B_all_pairs_filter", solve_b_all_pairs),
               ("C_incremental_clip", solve_c_incremental)]
    baseline = None
    rows = []
    for name, solver in methods:
        solver(original)  # 预热；不计时。
        durations = []
        last = None
        for _ in range(repeats):
            start = time.perf_counter_ns()
            last = solver(original)
            durations.append((time.perf_counter_ns() - start) / 1e6)
        vertices, d2, counters = last
        signature = (fingerprint(vertices), str(d2))
        if baseline is None:
            baseline = signature
        if signature != baseline:
            raise AssertionError(f"{scenario}/{size}/{name} 与方法 A 结果不一致")
        rows.append({"scenario": scenario, "halfplanes": size, "output_vertices": len(vertices),
                     "method": name, "repeats": repeats,
                     "median_ms": statistics.median(durations),
                     "min_ms": min(durations), "max_ms": max(durations),
                     "operation_counts": counters})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="缩小规模，仅检查脚本")
    args = parser.parse_args()
    sizes = [8, 16, 32] if args.quick else [8, 16, 32, 64, 96, 128]
    scenarios = ["active_ordered", "active_shuffled", "mostly_redundant"]
    rows = []
    for scenario in scenarios:
        for size in sizes:
            repeats = 3 if size >= 96 else 5
            rows.extend(one_case(scenario, size, repeats))
            print(scenario, size, "done", flush=True)
    root = Path(__file__).resolve().parents[1]
    source = Path(__file__)
    report = {
        "status": "exploratory_benchmark_not_official_test",
        "human_review": "pending",
        "timestamp_local": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "timer": "time.perf_counter_ns",
        "timed_scope": "region construction + shared rotating-calipers diameter; excludes input generation and JSON I/O",
        "numeric_representation": "shared HalfPlane integer normalization and Fraction exact predicates",
        "seed_notes": "redundant=20260911+size; shuffle=731+size",
        "script_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "rows": rows,
    }
    output = root / "outputs/q1/algorithm_comparison.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output.relative_to(root).as_posix())


if __name__ == "__main__":
    main()
