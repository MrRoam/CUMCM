"""人工构造的教学/验证输入，不是官方案例或模拟器结果。"""

import math


def demo_observations():
    triangle = [(0.0, 0.0), (20.0, 0.0), (10.0, 10 * math.sqrt(3))]
    acute = []
    for i, a in enumerate(triangle):
        b = triangle[(i + 1) % 3]
        dx, dy = (b[0] - a[0]) / 20, (b[1] - a[1]) / 20
        acute.append({"x": a[0] - 1000 * dx, "y": a[1] - 1000 * dy,
                      "bearing_deg": (math.degrees(math.atan2(dy, dx)) + 1) % 360})
    return {
        "cross_bearings": [{"x": -1000, "y": 0, "bearing_deg": 0},
                           {"x": 0, "y": -1000, "bearing_deg": 90}],
        "acute_triangle_counterexample": acute,
        "single_bearing_unbounded": [{"x": 0, "y": 0, "bearing_deg": 0}],
    }
