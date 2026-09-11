"""第二问面积平均策略的快速自动检查。"""

import math
import unittest

import numpy as np

from .geometry import (
    area_uniform_grid,
    initial_outer_polygon,
    is_receive_feasible,
    localization_radii,
    minimum_enclosing_circle,
    upper_receive_boundary,
)
from .strategy import local_selected_point, recommend_second_point


class StrategyTests(unittest.TestCase):
    def test_selected_point_is_on_receive_boundary(self):
        poly = initial_outer_polygon()
        point = local_selected_point()
        self.assertTrue(is_receive_feasible(poly, point))
        self.assertAlmostEqual(point[1], upper_receive_boundary(poly, point[0]), places=8)
        self.assertAlmostEqual(
            float(np.max(np.linalg.norm(poly - point, axis=1))), 1000.0, places=7
        )

    def test_mirror_choice(self):
        left = local_selected_point("left")
        right = local_selected_point("right")
        np.testing.assert_allclose(right, left * np.array([1.0, -1.0]))

    def test_global_rotation_and_translation(self):
        first = np.array([30.0, -20.0])
        point = recommend_second_point(first, 90.0, "left")
        local = local_selected_point()
        np.testing.assert_allclose(
            point, first + np.array([-local[1], local[0]]), atol=1e-10
        )
        self.assertAlmostEqual(np.linalg.norm(point - first), np.linalg.norm(local), places=10)

    def test_area_grid_uses_squared_radius_uniformity(self):
        sources, errors = area_uniform_grid(4, 3, 5)
        radii_squared = np.unique(np.round(np.sum(sources**2, axis=1), 8))
        self.assertEqual(len(radii_squared), 4)
        self.assertTrue(np.all(np.diff(radii_squared) > 0.0))
        self.assertEqual(len(sources), 4 * 3 * 5)
        self.assertEqual(len(errors), len(sources))

    def test_minimum_enclosing_circle_special_cases(self):
        cases = [
            (
                np.array([[0, 0], [2, 0], [1, math.sqrt(3)]], dtype=float),
                2 / math.sqrt(3),
            ),
            (np.array([[0, 0], [4, 0], [4, 2], [0, 2]], dtype=float), math.sqrt(5)),
            (np.array([[0, 0], [1, 0], [3, 0]], dtype=float), 1.5),
        ]
        for poly, expected in cases:
            radius, _ = minimum_enclosing_circle(poly)
            self.assertAlmostEqual(radius, expected, places=9)

    def test_true_source_is_inside_localization_circle(self):
        poly = initial_outer_polygon()
        sources, errors = area_uniform_grid(5, 3, 3)
        radii, centers, _, _ = localization_radii(
            poly, local_selected_point(), sources, errors, return_polygons=True
        )
        distances = np.linalg.norm(sources - centers, axis=1)
        self.assertTrue(np.all(distances <= radii + 1e-6))


if __name__ == "__main__":
    unittest.main()
