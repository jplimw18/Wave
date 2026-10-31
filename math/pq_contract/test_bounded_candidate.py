import json
import math
from pathlib import Path
import unittest

from bounded_candidate import BALANCED_POINT, BOUNDARY_ATOL, BOUNDARY_RADIUS, classify_point, evaluate, normalize_unit
from pq_candidate import evaluate as evaluate_unbounded


class BoundedCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = json.loads((Path(__file__).parent / "bounded_fixtures.json").read_text())
        cls.ref = fixture["reference"]
        cls.cases = {case["id"]: case["observation"] for case in fixture["observations"]}

    def test_unit45_reference_is_on_boundary(self):
        self.assertAlmostEqual(BOUNDARY_RADIUS, 0.7653668647301795)
        self.assertEqual(classify_point(*BALANCED_POINT)["boundary_status"], "fronteira")
        self.assertNotAlmostEqual(BOUNDARY_RADIUS, 1/math.sqrt(2))

    def test_key_points_and_equal_angle_counterexample(self):
        for point, expected in [((1, 0), "dentro"), ((0, 0), "fora"), ((1, 1), "fora"), ((.1, .1), "fora")]:
            self.assertEqual(classify_point(*point)["boundary_status"], expected)
        self.assertAlmostEqual(math.atan2(.1, .1), math.pi/4)

    def test_boundary_tolerance_is_explicit(self):
        for multiplier, expected in [(-2, "dentro"), (-.5, "fronteira"), (.5, "fronteira"), (2, "fora")]:
            result = classify_point(1, BOUNDARY_RADIUS+multiplier*BOUNDARY_ATOL)
            self.assertEqual(result["boundary_status"], expected)

    def test_bidirectional_clipping_preserves_raw_value(self):
        for value, expected in [(-.3, 0), (.4, .4), (1.8, 1)]:
            normalized = normalize_unit(value)
            self.assertEqual(normalized["raw"], value)
            self.assertEqual(normalized["value"], expected)
            self.assertEqual(normalized["clipped"], value != expected)
        self.assertIsNone(normalize_unit(None)["value"])

    def test_observation_clipping_does_not_change_unbounded_model(self):
        observation = self.cases["above_throughput_reference"]
        old = evaluate_unbounded(observation, self.ref)
        new = evaluate(observation, self.ref)
        self.assertEqual(old["P"], 2)
        self.assertEqual(new["P"], 1)
        self.assertEqual(new["raw_indices"]["P"], 2)
        self.assertTrue(new["normalization"]["P"]["above_one"])
        observation = self.cases["latency_only_above_reference"]
        new = evaluate(observation, self.ref)
        self.assertAlmostEqual(new["Q"], 1/math.sqrt(2))
        self.assertTrue(new["normalization"]["z_latency"]["above_one"])
        self.assertTrue(new["raw_q_above_one"])

    def test_normalized_domain_does_not_bound_s_and_d_to_one(self):
        result = evaluate(self.cases["all_failed_with_latency_excess"], self.ref)
        self.assertTrue(0 <= result["P"] <= 1 and 0 <= result["Q"] <= 1)
        self.assertAlmostEqual(result["D"], math.sqrt(2))
        self.assertGreater(result["D"], 1)
        self.assertAlmostEqual(math.hypot(1, 1), math.sqrt(2))

    def test_absence_and_idleness_are_separate_from_geometry(self):
        idle = evaluate(self.cases["no_traffic"], self.ref)
        self.assertEqual(idle["operational_state"], "ocioso")
        self.assertEqual(idle["boundary_status"], "ausente")
        self.assertIsNone(idle["Q"])
        for name in ("missing_counts", "missing_latency", "invalid_negative_count"):
            result = evaluate(self.cases[name], self.ref)
            self.assertEqual(result["boundary_status"], "ausente")
            self.assertIsNone(result["geometrically_efficient"])

    def test_invalid_points_are_not_silently_clipped(self):
        for point in [(1.1, 0), (0, -.1), (float("nan"), 0), (True, 0)]:
            with self.assertRaises(ValueError):
                classify_point(*point)
        for value in (float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                normalize_unit(value)


if __name__ == "__main__":
    unittest.main()
