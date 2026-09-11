"""仅测试使用全配对穷举作独立对照；正式算法不调用此路径。"""

from fractions import Fraction as F
import math
import random
import unittest

from src.q1.examples import demo_observations
from src.q1.geometry import (HalfPlane as H, analyze, bearing_halfplanes, diameter,
                             distance2, halfplane_intersection)


def box(x0, x1, y0, y1):
    return [H(-1, 0, -x0), H(1, 0, x1), H(0, -1, -y0), H(0, 1, y1)]


def brute_vertices(planes):
    """直接克拉默法则枚举，再对全部输入约束检查；不使用主算法求交。"""
    vertices = set()
    for i, p in enumerate(planes):
        for q in planes[i + 1:]:
            det = p.a * q.b - p.b * q.a
            if det == 0:
                continue
            x = F(p.c * q.b - p.b * q.c, det)
            y = F(p.a * q.c - p.c * q.a, det)
            if all(h.a * x + h.b * y <= h.c for h in planes):
                vertices.add((x, y))
    return vertices


class GeometryTests(unittest.TestCase):
    def check_bounded_oracle(self, planes):
        region = halfplane_intersection(planes)
        expected = brute_vertices(planes)
        self.assertEqual(set(region.vertices), expected)
        if not expected:
            self.assertEqual(region.status, "empty")
            return
        self.assertNotEqual(region.status, "unbounded")
        d2, _, steps = diameter(region.vertices)
        self.assertEqual(d2, max(distance2(a, b) for a in expected for b in expected))
        self.assertLessEqual(steps, 2 * len(expected))
        self.assertLessEqual(region.stats["intersections"], 8 * (len(planes) + 4))

    def test_rectangle_and_circle(self):
        result = analyze(box(0, 3, 0, 4))
        self.assertEqual(result["diameter_m"], 5)
        self.assertTrue(result["diameter_circle_covers"])
        self.check_bounded_oracle(box(0, 3, 0, 4))

    def test_acute_triangle_circle_failure(self):
        # 顶点 (0,0)、(4,0)、(2,3)，底边直径圆不含第三点。
        result = analyze([H(0, -1, 0), H(-3, 2, 0), H(3, 2, 12)])
        self.assertFalse(result["diameter_circle_covers"])

    def test_bearing_counterexample(self):
        observations = demo_observations()["acute_triangle_counterexample"]
        planes = bearing_halfplanes(observations)
        result = analyze(planes)
        self.assertEqual(result["status"], "polygon")
        self.assertEqual(len(result["vertices"]), 3)
        self.assertAlmostEqual(result["diameter_m"], 20, places=9)
        self.assertFalse(result["diameter_circle_covers"])
        self.check_bounded_oracle(planes)
        # 独立按 atan2 与角度差检查一个真实源；未假设官方误差分布。
        truth = (10, 10 * math.sqrt(3) / 3)
        for obs in observations:
            dx, dy = truth[0] - obs["x"], truth[1] - obs["y"]
            true_angle = math.degrees(math.atan2(dy, dx)) % 360
            error = (obs["bearing_deg"] - true_angle + 180) % 360 - 180
            self.assertLess(abs(error), 1)
            self.assertGreater(math.hypot(dx, dy), 5)
            self.assertLess(math.hypot(dx, dy), 1500)

    def test_degenerate_and_empty(self):
        for planes, status, count in [(box(0, 0, 0, 1), "segment", 2),
                                      (box(0, 0, 0, 0), "point", 1),
                                      (box(2, 1, 0, 1), "empty", 0)]:
            with self.subTest(status=status):
                region = halfplane_intersection(planes)
                self.assertEqual((region.status, len(region.vertices)), (status, count))
                self.check_bounded_oracle(planes)
        self.assertTrue(analyze(box(0, 0, 0, 0))["diameter_circle_covers"])
        self.assertTrue(analyze(box(0, 0, 0, 1))["diameter_circle_covers"])
        # 三条非平行约束在同一点相遇。
        self.assertEqual(halfplane_intersection([H(-1, 0, 0), H(0, -1, 0), H(1, 1, 0)]).status, "point")

    def test_unbounded(self):
        for planes in [[], [H(1, 0, 1)], [H(-1, 0, 0), H(1, 0, 1)],
                       [H(-1, 0, 0), H(1, 0, 0)], [H(-1, 0, 0), H(0, -1, 0)],
                       [H(-1, 0, 0), H(1, 0, 0), H(0, -1, 0)]]:
            with self.subTest(planes=planes):
                result = halfplane_intersection(planes)
                self.assertEqual(result.status, "unbounded")
                self.assertEqual(result.vertices, [])

    def test_parallel_duplicates(self):
        planes = box(-1, 1, -1, 1)
        self.check_bounded_oracle(planes + planes + [H(10, 0, 20), H(2, 0, 2)])

    def test_nearly_parallel_large_vertex(self):
        planes = [H(-1, 0, 0), H(0, -1, 0), H(1, 1000000, 1000000)]
        self.check_bounded_oracle(planes)
        self.assertIn((F(1000000), F(0)), halfplane_intersection(planes).vertices)

    def test_transform_invariance(self):
        base = [H(-1, 0, 0), H(0, -1, 0), H(3, 4, 12)]
        d2 = diameter(halfplane_intersection(base).vertices)[0]
        for size in [F(1, 1000000000), F(1), F(10**9)]:
            # x'=s*x+tx, y'=s*y+ty；精确平移与缩放。
            tx, ty = F(10**12), F(-10**12)
            transformed = [H(p.a, p.b, size*p.c+p.a*tx+p.b*ty) for p in base]
            self.assertEqual(diameter(halfplane_intersection(transformed).vertices)[0], size*size*d2)
        rotated = [H(-p.b, p.a, p.c) for p in base]
        self.assertEqual(diameter(halfplane_intersection(rotated).vertices)[0], d2)

    def test_random_bounded_against_enumeration(self):
        rng = random.Random(20260911)
        for _ in range(180):
            planes = box(-20, 20, -20, 20)
            for _ in range(rng.randrange(1, 14)):
                a, b = rng.randint(-8, 8), rng.randint(-8, 8)
                if a or b:
                    planes.append(H(a, b, rng.randint(-10, 30)))
            rng.shuffle(planes)
            self.check_bounded_oracle(planes)

    def test_random_general_classification(self):
        rng = random.Random(421)
        # 原始整数系数绝对值<=8，有限顶点绝对坐标<=128；1000框用于独立穷举。
        for _ in range(180):
            planes = []
            for _ in range(rng.randint(1, 10)):
                a, b = rng.randint(-5, 5), rng.randint(-5, 5)
                if a or b:
                    planes.append(H(a, b, rng.randint(-8, 8)))
            expected = brute_vertices(planes + box(-1000, 1000, -1000, 1000))
            actual = halfplane_intersection(planes)
            if not expected:
                self.assertEqual(actual.status, "empty")
            elif any(abs(x) == 1000 or abs(y) == 1000 for x, y in expected):
                self.assertEqual(actual.status, "unbounded")
            else:
                self.assertEqual(set(actual.vertices), expected)

    def test_random_bearings(self):
        rng = random.Random(7301)
        for _ in range(40):
            observations = []
            for j in range(6):
                ang = j * math.tau / 6 + rng.uniform(-0.1, 0.1)
                r = rng.uniform(500, 1200)
                x, y = r * math.cos(ang), r * math.sin(ang)
                theta = (math.degrees(math.atan2(-y, -x)) + rng.uniform(-0.9, 0.9)) % 360
                observations.append({"x": x, "y": y, "bearing_deg": theta})
            planes = bearing_halfplanes(observations)
            self.check_bounded_oracle(planes)
            self.assertTrue(all(p.slack((F(0), F(0))) >= 0 for p in planes))

    def test_forward_wedge_and_angle_wrap(self):
        planes = bearing_halfplanes([{"x": 0, "y": 0, "bearing_deg": 0}])
        self.assertTrue(all(p.slack((F(100), F(0))) >= 0 for p in planes))
        self.assertFalse(all(p.slack((F(-100), F(0))) >= 0 for p in planes))
        for angle in [0, 1, 89, 90, 179, 180, 269, 270, 359]:
            self.assertEqual(len(bearing_halfplanes([{"x": 0, "y": 0, "bearing_deg": angle}])), 2)

    def test_input_validation(self):
        for angle in [-1, 360, float("nan"), float("inf"), True]:
            with self.assertRaises((ValueError, OverflowError)):
                bearing_halfplanes([{"x": 0, "y": 0, "bearing_deg": angle}])
        with self.assertRaises(ValueError):
            H(0, 0, 1)
        with self.assertRaises(ValueError):
            bearing_halfplanes([])
        with self.assertRaises(KeyError):
            bearing_halfplanes([{"x": 0, "y": 0}])

    def test_many_active_edges_and_labels(self):
        points = [(F(i), F(i*i)) for i in range(-64, 65)]
        planes = []
        for i, p in enumerate(points):
            q = points[(i+1) % len(points)]
            dx, dy = q[0]-p[0], q[1]-p[1]
            planes.append(H(dy, -dx, dy*p[0]-dx*p[1], str(i)))
        region = halfplane_intersection(planes)
        self.assertEqual(set(region.vertices), set(points))
        self.assertLessEqual(region.stats["intersections"], 8*(len(planes)+4))
        for i, p in enumerate(region.vertices):
            h = planes[int(region.edge_labels[i])]
            self.assertEqual(h.slack(p), 0)
            self.assertEqual(h.slack(region.vertices[(i+1) % len(points)]), 0)
        expected = max(distance2(a, b) for a in points for b in points)
        self.assertEqual(diameter(region.vertices)[0], expected)


if __name__ == "__main__":
    unittest.main()
