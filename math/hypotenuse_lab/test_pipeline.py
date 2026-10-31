"""Verificações da candidata operacional explícita e do pipeline completo."""
import copy
import math
import unittest

import numpy as np

from pipeline import REFERENCES, analyze, derive, synthetic_input


class PipelineTests(unittest.TestCase):
    def observation(self, **changes):
        row = dict(service="api-a", window=0, duration_seconds=5, completed=100,
                   failed=0, mean_latency_seconds=.05, cpu_cores=.1)
        row.update(changes)
        return row

    def test_reference_and_residual_geometry(self):
        result = derive(self.observation(), "synthetic")
        self.assertEqual(result["S"], 1)
        self.assertAlmostEqual(result["P"], .5)
        self.assertAlmostEqual(result["Q"], math.sqrt(.75))
        self.assertAlmostEqual(result["D"]**2, 2-2*result["P"])

    def test_latency_and_errors_have_declared_roles(self):
        result = derive(self.observation(failed=20, mean_latency_seconds=.2), "synthetic")
        self.assertAlmostEqual(result["goodput_per_second"], 16)
        self.assertAlmostEqual(result["quality_factor"], .5)
        self.assertAlmostEqual(result["P_raw"], .2)
        self.assertEqual(result["raw"]["failed"], 20)

    def test_clipping_is_explicit_and_retains_raw(self):
        result = derive(self.observation(completed=300), "synthetic")
        self.assertEqual(result["P_raw"], 1.5)
        self.assertEqual(result["P"], 1)
        self.assertEqual(result["Q"], 0)
        self.assertTrue(result["clipping_applied"])
        self.assertEqual(result["restriction_delta"], -.5)

    def test_idle_missing_invalid_and_all_failed_are_distinct(self):
        idle = derive(self.observation(completed=0, failed=0, mean_latency_seconds=None), "synthetic")
        self.assertEqual(idle["operational_state"], "ocioso")
        self.assertIsNone(idle["P"])
        self.assertEqual(idle["S"], 1)
        for change in (dict(completed=None), dict(mean_latency_seconds=None), dict(counter_reset=True), dict(failed=101)):
            self.assertIsNone(derive(self.observation(**change), "synthetic")["Q"])
        all_failed = derive(self.observation(failed=100), "synthetic")
        self.assertEqual((all_failed["P"], all_failed["Q"]), (0, 1))

    def test_cpu_is_not_used_to_manufacture_hypotenuse(self):
        first = derive(self.observation(cpu_cores=.01), "synthetic")
        second = derive(self.observation(cpu_cores=9), "synthetic")
        for key in ("S", "P", "Q", "D"):
            self.assertEqual(first[key], second[key])

    def test_invalid_references_and_finiteness(self):
        for key, value in [("S_reference", .5), ("throughput_per_second", 0), ("latency_seconds", float("nan"))]:
            ref = dict(REFERENCES, **{key: value})
            self.assertEqual(derive(self.observation(), "synthetic", ref)["status"], "invalid")
        self.assertEqual(derive(self.observation(duration_seconds=0), "synthetic")["status"], "invalid")

    def test_radial_threshold_on_fixed_unit_circle(self):
        low = derive(self.observation(completed=70, duration_seconds=2.5), "synthetic")
        high = derive(self.observation(completed=71, duration_seconds=2.5), "synthetic")
        boundary = derive(self.observation(completed=100, duration_seconds=100/(40/math.sqrt(2))), "synthetic")
        self.assertEqual(low["boundary_status"], "fora")
        self.assertEqual(high["boundary_status"], "dentro")
        self.assertEqual(boundary["boundary_status"], "fronteira")

    def test_full_synthetic_chain_and_rank_energy(self):
        records = [derive(row, "synthetic") for row in synthetic_input()["rows"]]
        result = analyze(records)["decomposition"]
        self.assertEqual(result["shape"], [2, 3, 10])
        self.assertEqual(result["wave_tensor_shape"], [2, 10, 64])
        self.assertLessEqual(result["wave_matrix_rank"], 2)
        self.assertLess(result["hosvd_full_relative_error"], 1e-12)
        self.assertLess(result["max_factor_orthogonality_error"], 1e-12)
        self.assertLess(result["core_norm_error"], 1e-12)
        self.assertLess(result["max_cycle_energy_error"], 1e-12)
        self.assertTrue(any(row["clipping_applied"] for row in records))
        self.assertTrue(all(abs(row["S"]**2-row["P"]**2-row["Q"]**2) < 1e-12 for row in records))

    def test_missing_window_mask_and_duplicates(self):
        records = [derive(row, "synthetic") for row in synthetic_input()["rows"]]
        records[0] = derive(self.observation(completed=None), "synthetic")
        result = analyze(records)
        self.assertIn(0, result["omitted_window_indices"])
        self.assertIsNone(result["tensor"][0][0][0])
        self.assertEqual(result["decomposition"]["shape"], [2, 3, 9])
        with self.assertRaises(ValueError):
            analyze(records+[copy.deepcopy(records[0])])


if __name__ == "__main__":
    unittest.main()
