"""第一问的解析、整体性质、边界和独立入口检查。"""
import itertools
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from experiments.b_q1.solver import solve, shared, ERROR_DEG
from experiments.b_q1.run_examples import example_inputs, edge_observations


class Q1Tests(unittest.TestCase):
    def assert_vertices(self, actual, expected, tolerance=1e-6):
        self.assertEqual(len(actual), len(expected))
        for p in expected:
            self.assertLessEqual(min(math.dist(p, q) for q in actual), tolerance)

    def test_rectangle_from_real_observations(self):
        example = example_inputs()["rectangle"]
        result = solve(example["observations"])
        self.assertEqual(result["status"], "polygon")
        self.assert_vertices(result["vertices_m"], example["expected_vertices_m"])
        self.assertAlmostEqual(result["diameter_m"], 5, places=7)
        self.assertAlmostEqual(math.dist(*result["diameter_endpoints_m"]), 5, places=7)

    def test_triangle_from_real_observations(self):
        example = example_inputs()["triangle"]
        result = solve(example["observations"])
        self.assert_vertices(result["vertices_m"], example["expected_vertices_m"])
        self.assertAlmostEqual(result["diameter_m"], 40, places=7)
        # 独立核对三条边，避免只用被测函数的返回值自证。
        for a, b in itertools.combinations(result["vertices_m"], 2):
            self.assertAlmostEqual(math.dist(a, b), 40, places=7)

    def test_counterexample_physics_and_cover(self):
        example = example_inputs()["triangle"]
        source = example["source_m"]
        for row in example["observations"]:
            p = row["position_m"]
            dx, dy = source[0] - p[0], source[1] - p[1]
            distance = math.hypot(dx, dy)
            self.assertAlmostEqual(distance, math.sqrt(1020**2 + 400 / 3), places=7)
            self.assertTrue(5 < distance < 1100)
            true_angle = math.degrees(math.atan2(dy, dx)) % 360
            error = (row["bearing_deg"] - true_angle + 180) % 360 - 180
            self.assertLess(abs(error), 1)
        self.assertLess(math.hypot(*source), 1800)
        radius = 40 / math.sqrt(3)
        self.assertGreater(radius, 20)
        for p in example["expected_vertices_m"]:
            self.assertAlmostEqual(math.dist(source, p), radius)
            for row in example["observations"]:
                self.assertTrue(5 < math.dist(p, row["position_m"]) <= 1100)
        # 最小半径的普遍下界来自正文的平方距离恒等式，不依赖抽样证明。

    def test_two_bearings_analytic_quadrilateral(self):
        t = math.tan(math.radians(1))
        expected = [[500*t/(1-t)]*2, [-500*t/(1+t)]*2,
                    [500*t*(1-t)/(1+t*t), -500*t*(1+t)/(1+t*t)],
                    [-500*t*(1+t)/(1+t*t), 500*t*(1-t)/(1+t*t)]]
        result = solve(example_inputs()["crossing"]["observations"])
        self.assert_vertices(result["vertices_m"], expected)
        self.assertAlmostEqual(result["diameter_m"], 1000*math.sqrt(2)*t/(1-t*t), places=7)
        self.assertEqual(ERROR_DEG, 1.0)

    def test_every_vertex_satisfies_original_angles(self):
        for example in example_inputs().values():
            result = solve(example["observations"])
            for p in result["vertices_m"]:
                for row in example["observations"]:
                    q = row["position_m"]
                    actual = math.degrees(math.atan2(p[1]-q[1], p[0]-q[0]))
                    error = (actual-row["bearing_deg"]+180) % 360-180
                    self.assertLessEqual(abs(error), 1 + 1e-9)

    def test_translation_and_rotation(self):
        rng = random.Random(20260911)
        for name, example in example_inputs().items():
            original = solve(example["observations"])
            for _ in range(12):
                angle = rng.uniform(0, 360)
                c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                shift = [rng.uniform(-2000, 2000), rng.uniform(-2000, 2000)]
                transform = lambda p: [c*p[0]-s*p[1]+shift[0], s*p[0]+c*p[1]+shift[1]]
                observations = [{"position_m": transform(row["position_m"]),
                                 "bearing_deg": (row["bearing_deg"]+angle) % 360}
                                for row in example["observations"]]
                result = solve(observations)
                self.assert_vertices(result["vertices_m"], [transform(p) for p in original["vertices_m"]])
                self.assertAlmostEqual(result["diameter_m"], original["diameter_m"], places=6, msg=name)

    def test_permutation_and_duplicate_observations(self):
        for name in ("triangle", "rectangle"):
            rows = example_inputs()[name]["observations"]
            original = solve(rows)
            for ordered in itertools.permutations(rows):
                result = solve(list(ordered) + [ordered[0]])
                self.assert_vertices(result["vertices_m"], original["vertices_m"])
                self.assertAlmostEqual(result["diameter_m"], original["diameter_m"], places=6)

    def test_add_observations_cannot_increase_diameter(self):
        example = example_inputs()["triangle"]
        rows = example["observations"][:]
        source = example["source_m"]
        previous = solve(rows)["diameter_m"]
        for a in (15, 85, 170, 240, 315):
            # 距真源600米且误差为0的额外观测，每次都与同一个源相容。
            p = [source[0]-600*math.cos(math.radians(a)), source[1]-600*math.sin(math.radians(a))]
            rows.append({"position_m": p, "bearing_deg": a})
            result = solve(rows)
            self.assertEqual(result["status"], "polygon")
            self.assertLessEqual(result["diameter_m"], previous + 1e-7)
            previous = result["diameter_m"]
        self.assertLess(previous, 40)

    def test_empty_and_unbounded(self):
        self.assertEqual(solve([])["status"], "unbounded")
        result = solve([{"position_m": [0, 0], "bearing_deg": 0}])
        self.assertEqual(result["status"], "unbounded")
        self.assertTrue(math.isinf(result["diameter_m"]))
        rows = [{"position_m": [0, 0], "bearing_deg": 180},
                {"position_m": [10, 0], "bearing_deg": 0}]
        result = solve(rows)
        self.assertEqual(result["status"], "empty")
        self.assertIsNone(result["diameter_m"])

    def test_point_and_segment(self):
        # 此处检查几何退化，不声称顶点处还能取得示向度。
        point = solve([{"position_m": [0, 0], "bearing_deg": a} for a in (0, 180)])
        self.assertEqual(point["status"], "point")
        self.assertEqual(point["diameter_m"], 0)
        segment = solve([{"position_m": [0, 0], "bearing_deg": 1},
                         {"position_m": [10, 0], "bearing_deg": 181}])
        self.assertEqual(segment["status"], "segment")
        self.assertAlmostEqual(segment["diameter_m"], 10)

    def test_nearly_parallel_finite_region_has_no_box_cap(self):
        eps = 1e-6
        result = shared.halfplane_region([((1, 0), 4), ((-1, 0), 0),
                                          ((-1, eps), 3*eps), ((1, -eps), 0)])
        self.assertEqual(result["kind"], "polygon")
        self.assert_vertices(result["vertices"], [[0, 0], [0, 3], [4, 4/eps], [4, 4/eps+3]])
        diameter, _ = shared.polygon_diameter(result["vertices"])
        self.assertAlmostEqual(diameter, math.hypot(4, 4/eps+3), places=6)

    def test_bearing_wrap(self):
        rows = [{"position_m": [-500, 0], "bearing_deg": 359.8},
                {"position_m": [0, -500], "bearing_deg": 90}]
        result = solve(rows)
        self.assertEqual(result["status"], "polygon")
        self.assertTrue(all(-20 < x < 20 for p in result["vertices_m"] for x in p))

    def test_invalid_input(self):
        invalid = [None, [3], [{"position_m": [0], "bearing_deg": 0}],
                   [{"position_m": [0, float("nan")], "bearing_deg": 0}],
                   [{"position_m": [True, 0], "bearing_deg": 0}]]
        invalid += [[{"position_m": [0, 0], "bearing_deg": a}]
                    for a in (None, -1, 360, float("inf"), "90")]
        for rows in invalid:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                solve(rows)

    def test_cli_standard_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            output = Path(tmp) / "result.json"
            path.write_text(json.dumps({"observations": []}), encoding="utf-8")
            command = [sys.executable, str(Path(__file__).with_name("solver.py")), str(path), "--output", str(output)]
            proc = subprocess.run(command, capture_output=True, cwd=tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(result["diameter_m"], "Infinity")
            path.write_text(json.dumps(example_inputs()["rectangle"]), encoding="utf-8")
            proc = subprocess.run(command, capture_output=True, cwd=tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertAlmostEqual(json.loads(output.read_text(encoding="utf-8"))["diameter_m"], 5, places=7)
            path.write_text(json.dumps({"observations": [{"position_m": [0, 0], "bearing_deg": 400}]}), encoding="utf-8")
            self.assertEqual(subprocess.run(command, capture_output=True, cwd=tmp).returncode, 2)

    def test_import_does_not_use_foreign_geometry(self):
        code = ("import sys, types; sys.modules['geometry']=types.ModuleType('geometry'); "
                "from experiments.b_q1.solver import solve; "
                "assert solve([])['status']=='unbounded'")
        result = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
