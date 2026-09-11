"""生成明确标记为自建的第一问算例、物理核验和可追溯结果。"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import platform
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from experiments.b_q1.solver import solve, json_safe


def edge_observations(vertices, backoff=1000.0):
    """从逆时针边向后延长，另一条边界能否容纳多边形由算例另行检查。"""
    observations = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        observations.append({
            "position_m": [a[0] - backoff * dx / length, a[1] - backoff * dy / length],
            "bearing_deg": (math.degrees(math.atan2(dy, dx)) + 1.0) % 360,
        })
    return observations


def example_inputs():
    triangle = [[0.0, 0.0], [40.0, 0.0], [20.0, 20 * math.sqrt(3)]]
    rectangle = [[0.0, 0.0], [4.0, 0.0], [4.0, 3.0], [0.0, 3.0]]
    return {
        "crossing": {"label": "两次垂直方向测向交会", "observations": [
            {"position_m": [-500.0, 0.0], "bearing_deg": 0.0},
            {"position_m": [0.0, -500.0], "bearing_deg": 90.0}],
            "source_m": [0.0, 0.0], "reception_radius_m": 1100.0},
        "rectangle": {"label": "4米×3米矩形解析核对", "observations": edge_observations(rectangle),
            "source_m": [2.0, 1.5], "reception_radius_m": 1100.0,
            "expected_vertices_m": rectangle, "expected_diameter_m": 5.0},
        "triangle": {"label": "40米等边三角形覆盖反例", "observations": edge_observations(triangle),
            "source_m": [20.0, 20 * math.sqrt(3) / 3], "reception_radius_m": 1100.0,
            "expected_vertices_m": triangle, "expected_diameter_m": 40.0,
            "minimum_cover_radius_m": 40 / math.sqrt(3)},
    }


def physical_check(example):
    s, radius = example["source_m"], example["reception_radius_m"]
    rows = []
    for observation in example["observations"]:
        p = observation["position_m"]
        distance = math.dist(s, p)
        truth = math.degrees(math.atan2(s[1] - p[1], s[0] - p[0])) % 360
        error = (observation["bearing_deg"] - truth + 180) % 360 - 180
        rows.append({"distance_m": distance, "true_bearing_deg": truth,
                     "error_deg": error, "valid": 5 < distance <= radius and abs(error) <= 1.0})
    return {"source_within_target_disk": math.hypot(*s) <= 1800,
            "valid_reception_radius": 1000 <= radius <= 1500,
            "observations": rows,
            "all_valid": math.hypot(*s) <= 1800 and 1000 <= radius <= 1500 and all(r["valid"] for r in rows)}


def source_hashes():
    paths = [HERE / name for name in ("solver.py", "run_examples.py", "test_solver.py", "verify.py", "plot_results.py")]
    paths += [REPO / "experiments/b_overnight/q2_geometry.py",
              REPO / "experiments/b_adaptive_q3/geometry.py", REPO / "problem/B题.md"]
    return {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    (HERE / "examples").mkdir(exist_ok=True)
    (HERE / "results").mkdir(exist_ok=True)
    outputs = {}
    for name, example in example_inputs().items():
        example["origin"] = "自建解析算例；非官方案例。source_m 仅用于事后验证，不传给求解器。"
        path = HERE / "examples" / (name + ".json")
        path.write_text(json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        physical = physical_check(example)
        if not physical["all_valid"]:
            raise AssertionError(name + " 不满足物理条件")
        outputs[name] = {"input": example, "result": solve(example["observations"]), "physical_check": physical,
                         "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
              "python": platform.python_version(), "error_half_width_deg": 1.0,
              "source_sha256": source_hashes(), "examples": outputs}
    (HERE / "results/examples.json").write_text(json.dumps(json_safe(report), ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({name: row["result"]["diameter_m"] for name, row in outputs.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
