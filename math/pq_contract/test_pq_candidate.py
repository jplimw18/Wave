import json
import math
from pathlib import Path
import unittest
from pq_candidate import evaluate


class CandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures = json.loads((Path(__file__).parent / "fixtures.json").read_text())
        cls.ref = fixtures["reference"]
        cls.cases = {case["id"]: case["observation"] for case in fixtures["cases"]}

    def case(self, name):
        return evaluate(self.cases[name], self.ref)

    def test_counts_are_not_discounted_twice(self):
        result = self.case("latency_and_error")
        self.assertAlmostEqual(result["P"], .8)
        self.assertAlmostEqual(result["Q"], 1.)
        self.assertAlmostEqual(result["S"], math.sqrt(1.64))
        self.assertAlmostEqual(result["theta"], math.atan2(1, .8))
        self.assertAlmostEqual(result["D"], math.sqrt(1.04))

    def test_distance_to_fixed_reference_and_triangle(self):
        self.assertEqual(self.case("reference_point")["D"], 0.)
        for name in self.cases:
            result = self.case(name)
            if result["status"] != "ok":
                self.assertIsNone(result["D"])
                continue
            p, q, s, d = (result[key] for key in ("P", "Q", "S", "D"))
            self.assertGreaterEqual(d, 0.)
            self.assertAlmostEqual(d*d, s*s-2*p+1)
            self.assertGreaterEqual(d+1e-12, abs(s-1))
            self.assertLessEqual(d, s+1+1e-12)
            self.assertEqual(d == 0., p == 1. and q == 0.)

    def test_reference_does_not_cap_delivery(self):
        result = self.case("above_throughput_reference")
        self.assertEqual((result["P"], result["Q"], result["S"]), (2., 0., 2.))

    def test_all_errors_have_zero_delivery_and_positive_friction(self):
        result = self.case("all_failed")
        self.assertEqual(result["P"], 0.)
        self.assertAlmostEqual(result["Q"], 5/math.sqrt(2))
        self.assertAlmostEqual(result["theta"], math.pi/2)

    def test_no_traffic_is_not_missing_scrape(self):
        self.assertEqual(self.case("no_traffic")["P"], 0.)
        self.assertIsNone(self.case("no_traffic")["Q"])
        self.assertIsNone(self.case("missing_counts")["P"])
        self.assertEqual(self.case("missing_counts")["status"], "missing")

    def test_missing_latency_retains_only_known_delivery(self):
        result = self.case("missing_latency")
        self.assertEqual(result["P"], .8)
        self.assertIsNone(result["S"])

    def test_invalid_or_reset_is_not_valid_zero(self):
        for case in ("counter_reset", "invalid_counts"):
            self.assertEqual(self.case(case)["status"], "invalid")
            self.assertIsNone(self.case(case)["P"])
        for key in self.ref:
            for value in (0, -1, float("nan"), float("inf"), True):
                invalid = {**self.ref, key: value}
                self.assertEqual(evaluate(self.cases["all_failed"], invalid)["status"], "invalid")

    def test_finite_inputs_cannot_emit_infinity(self):
        obs = {**self.cases["all_failed"], "duration_seconds": 1e-320}
        self.assertEqual(evaluate(obs, self.ref)["status"], "ok")
        obs["failed"] = 0
        self.assertEqual(evaluate(obs, self.ref)["status"], "invalid")

    def test_historical_windows_are_reanalysis_not_correlation(self):
        path = Path(__file__).parent / "fixtures" / "historical-windows.json"
        windows = json.loads(path.read_text())
        self.assertEqual(len(windows), 2)
        for window in windows:
            observation = dict(duration_seconds=window["duration_seconds"],
                               completed=window["total_requests"], failed=window["failed_requests"],
                               mean_latency_seconds=window["latency_seconds"])
            result = evaluate(observation, self.ref)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["Q"], 0.)
            self.assertEqual(result["S"], result["P"])
            self.assertEqual(result["theta"], 0.)
            self.assertAlmostEqual(result["D"], 1-result["P"])


if __name__ == "__main__":
    unittest.main()
