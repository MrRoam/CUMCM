# 第一问验证记录

UTC时间：2026-09-11T05:11:41.945240+00:00；Python：3.13.5。

结果：通过；共 31 项测试。

包含第一问完整输入链、解析算例、变换不变性、追加观测、必要边界及旧共有几何回归。
随机旋转/平移种子为20260911，每个解析案例12次；这是几何性质检查，不是失败率估计。
源码散列与原始运行输出见同目录 validation.json；本记录由脚本生成。
执行和核验由AI完成，团队人工审阅状态尚未登记。

## 生成物一致性

- example_source_hashes_current: True
- example_inputs_unchanged: True
- all_examples_physically_valid: True
- figure_input_current: True
- figure_script_current: True
- figure_files_unchanged: True

## experiments.b_q1.test_solver

```text
test_add_observations_cannot_increase_diameter (experiments.b_q1.test_solver.Q1Tests.test_add_observations_cannot_increase_diameter) ... ok
test_bearing_wrap (experiments.b_q1.test_solver.Q1Tests.test_bearing_wrap) ... ok
test_cli_standard_json (experiments.b_q1.test_solver.Q1Tests.test_cli_standard_json) ... ok
test_counterexample_physics_and_cover (experiments.b_q1.test_solver.Q1Tests.test_counterexample_physics_and_cover) ... ok
test_empty_and_unbounded (experiments.b_q1.test_solver.Q1Tests.test_empty_and_unbounded) ... ok
test_every_vertex_satisfies_original_angles (experiments.b_q1.test_solver.Q1Tests.test_every_vertex_satisfies_original_angles) ... ok
test_import_does_not_use_foreign_geometry (experiments.b_q1.test_solver.Q1Tests.test_import_does_not_use_foreign_geometry) ... ok
test_invalid_input (experiments.b_q1.test_solver.Q1Tests.test_invalid_input) ... ok
test_nearly_parallel_finite_region_has_no_box_cap (experiments.b_q1.test_solver.Q1Tests.test_nearly_parallel_finite_region_has_no_box_cap) ... ok
test_permutation_and_duplicate_observations (experiments.b_q1.test_solver.Q1Tests.test_permutation_and_duplicate_observations) ... ok
test_point_and_segment (experiments.b_q1.test_solver.Q1Tests.test_point_and_segment) ... ok
test_rectangle_from_real_observations (experiments.b_q1.test_solver.Q1Tests.test_rectangle_from_real_observations) ... ok
test_translation_and_rotation (experiments.b_q1.test_solver.Q1Tests.test_translation_and_rotation) ... ok
test_triangle_from_real_observations (experiments.b_q1.test_solver.Q1Tests.test_triangle_from_real_observations) ... ok
test_two_bearings_analytic_quadrilateral (experiments.b_q1.test_solver.Q1Tests.test_two_bearings_analytic_quadrilateral) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.400s

OK
```

## experiments.b_overnight.test_q2_geometry

```text
test_empty_unbounded_point_segment (experiments.b_overnight.test_q2_geometry.Q1GeometryTests.test_empty_unbounded_point_segment) ... ok
test_equilateral_diameter_circle_fails (experiments.b_overnight.test_q2_geometry.Q1GeometryTests.test_equilateral_diameter_circle_fails) ... ok
test_equilateral_is_realizable_by_three_bearing_wedges (experiments.b_overnight.test_q2_geometry.Q1GeometryTests.test_equilateral_is_realizable_by_three_bearing_wedges) ... ok
test_halfplane_strip_without_vertices_is_nonempty (experiments.b_overnight.test_q2_geometry.Q1GeometryTests.test_halfplane_strip_without_vertices_is_nonempty) ... ok
test_rectangle_diameter (experiments.b_overnight.test_q2_geometry.Q1GeometryTests.test_rectangle_diameter) ... ok
test_wedge_wrap_and_wrong_direction (experiments.b_overnight.test_q2_geometry.Q1GeometryTests.test_wedge_wrap_and_wrong_direction) ... ok
test_zero_error_is_ray_not_line (experiments.b_overnight.test_q2_geometry.Q1GeometryTests.test_zero_error_is_ray_not_line) ... ok
test_continuous_angle_bin_bound_covers_non_bin_readings (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_continuous_angle_bin_bound_covers_non_bin_readings) ... ok
test_fifty_metre_indistinguishable_pair (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_fifty_metre_indistinguishable_pair) ... ok
test_first_region_covers_all_angular_boundaries (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_first_region_covers_all_angular_boundaries) ... ok
test_history_enlarges_reliable_region (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_history_enlarges_reliable_region) ... ok
test_inner_candidate_polygon_is_safe (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_inner_candidate_polygon_is_safe) ... ok
test_multiple_history_certificate_against_direct_rule (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_multiple_history_certificate_against_direct_rule) ... ok
test_previous_success_and_empty_fail_closed (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_previous_success_and_empty_fail_closed) ... ok
test_translation_does_not_change_reception (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_translation_does_not_change_reception) ... ok
test_universal_counterexample_direct_physical_checks (experiments.b_overnight.test_q2_geometry.Q2GeometryTests.test_universal_counterexample_direct_physical_checks) ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.008s

OK
```
