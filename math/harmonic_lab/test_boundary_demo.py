import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pq_contract"))
from bounded_candidate import classify_point
from boundary_demo import make_trajectories


class BoundaryCandidateTests(unittest.TestCase):
    def test_boundary_and_reference_cases(self):
        boundary = classify_point(1/math.sqrt(2), 1/math.sqrt(2))
        ideal = classify_point(1, 0)
        rest = classify_point(0, 0)
        corner = classify_point(1, 1)
        self.assertEqual(boundary["boundary_status"], "fronteira")
        self.assertAlmostEqual(boundary["boundary_radius"], math.sqrt(2-math.sqrt(2)))
        self.assertEqual(ideal["boundary_status"], "dentro")
        self.assertEqual(rest["boundary_status"], "fora")
        self.assertEqual(corner["boundary_status"], "fora")
        self.assertFalse(rest["geometrically_efficient"])

    def test_same_angle_different_radius_can_be_outside(self):
        result = classify_point(.1, .1)
        self.assertEqual(result["boundary_status"], "fora")
        self.assertGreater(result["D"], result["boundary_radius"])
        self.assertNotAlmostEqual(math.hypot(.1-1, .1), math.hypot(.5-1, .5))

    def test_missing_and_domain_validation(self):
        missing = classify_point(None, 0)
        self.assertEqual(missing["boundary_status"], "ausente")
        self.assertIsNone(missing["D"])
        with self.assertRaises(ValueError): classify_point(1.01, .2)

    def test_demo_trajectories_stay_normalized_and_include_named_cases(self):
        _, paths = make_trajectories()
        self.assertEqual(len(paths), 4)
        self.assertEqual(paths[0].shape, (12,2))
        all_points=np.concatenate(paths)
        self.assertTrue(np.all((all_points>=0)&(all_points<=1)))
        self.assertTrue(np.allclose(paths[0][0], [1,0]))
        self.assertTrue(np.allclose(paths[1][0], [1/math.sqrt(2)]*2))


if __name__ == "__main__": unittest.main()
