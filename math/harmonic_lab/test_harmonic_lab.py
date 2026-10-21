import unittest

import numpy as np

from harmonic_lab import coefficients, distance, hosvd, reconstruct, rotation


class HarmonicLabTests(unittest.TestCase):
    def test_rotation_and_phase_reconstruction(self):
        theta = 0.73
        r = rotation(theta)
        self.assertTrue(np.allclose(r.T @ r, np.eye(2)))
        p, q = 1.7, -0.4
        t = np.linspace(0, 1, 200)
        s = np.hypot(p, q)
        self.assertTrue(np.allclose(reconstruct(t, 2*np.pi, p, q), s*np.sin(2*np.pi*t+np.arctan2(q,p))))

    def test_complete_uniform_cycle_orthogonality_and_energy(self):
        n = 800
        t = np.arange(n)/n
        y = reconstruct(t, 2*np.pi, 2.0, -0.5)
        design = np.column_stack((np.sin(2*np.pi*t), np.cos(2*np.pi*t)))
        self.assertTrue(np.allclose(design.T@design/n, 0.5*np.eye(2), atol=1e-12))
        self.assertAlmostEqual(float(np.mean(y*y)), (2.0**2+0.5**2)/2, places=12)
        p,q,s,theta,rank = coefficients(y, 2*np.pi, t)
        self.assertEqual(rank, 2)
        self.assertAlmostEqual(p, 2.0); self.assertAlmostEqual(q, -0.5)

    def test_zero_amplitude_and_invalid_inputs(self):
        self.assertIsNone(coefficients(np.zeros(8), 1.0)[3])
        with self.assertRaises(ValueError): coefficients([1, np.nan], 1)
        with self.assertRaises(ValueError): coefficients([1,2], 0)
        with self.assertRaises(ValueError): coefficients([1,2], 1, [0, np.inf])
        with self.assertRaises(ValueError): reconstruct([0, np.nan], 1, 1, 1)

    def test_rank_deficient_fit_and_nonuniform_recovery(self):
        # Repeated phase samples produce identical design rows and rank one.
        t = np.zeros(5)
        rank_fit = coefficients(np.ones(5)*2, 1, t)
        self.assertEqual(rank_fit[4], 1)
        t = np.array([0.03, 0.17, 0.29, 0.46, 0.71, 0.93])
        y = reconstruct(t, 2*np.pi, 1.25, 0.8)
        fit = coefficients(y, 2*np.pi, t)
        self.assertEqual(fit[4], 2)
        self.assertAlmostEqual(fit[0], 1.25); self.assertAlmostEqual(fit[1], 0.8)

    def test_hosvd_full_and_truncated(self):
        x = np.arange(24., dtype=float).reshape(2,3,4)
        full, core, factors = hosvd(x)
        small, _, used = hosvd(x, (1,1,1))
        self.assertTrue(np.allclose(full,x,atol=1e-12))
        self.assertAlmostEqual(float(np.linalg.norm(core)), float(np.linalg.norm(x)))
        self.assertTrue(np.linalg.norm(small-x) > 0)
        self.assertEqual([f.shape[1] for f in used], [1,1,1])
        for factor in factors:
            self.assertTrue(np.allclose(factor.T @ factor, np.eye(factor.shape[1]), atol=1e-12))
        matrix = np.array([[1.,2.,3.],[4.,5.,6.]])
        u,s,vh = np.linalg.svd(matrix, full_matrices=False)
        self.assertTrue(np.allclose(u @ np.diag(s) @ vh, matrix))
        self.assertGreater(np.linalg.norm(matrix-u[:,:1] @ np.diag(s[:1]) @ vh[:1]), 0)
        with self.assertRaises(ValueError): hosvd(np.empty((2,0,3)))
        with self.assertRaises(ValueError): hosvd(np.ones((2,2)), (1.5, 1))
        with self.assertRaises(ValueError): hosvd(np.ones((2,2)), (True, 1))

    def test_projection_nonidentifiability(self):
        m = np.array([[1.,0.],[0.,1.],[1.,1.]])
        n = np.array([1.,1.,-1.])
        self.assertTrue(np.allclose(n@m, 0))

    def test_reference_distance_properties(self):
        self.assertEqual(distance(1, 0), 0)
        self.assertEqual(distance(0, 0), 1)
        self.assertGreaterEqual(distance(-2, 3), 0)
        self.assertIsNone(distance(None, 2))
        self.assertIsNone(distance(1, np.nan))
        self.assertIsNone(distance(1.7e308, 1.7e308))
        p, q = 2.2, -0.7
        s = np.hypot(p, q)
        d = distance(p, q)
        self.assertLessEqual(abs(s-1), d+1e-12)
        self.assertLessEqual(d, s+1+1e-12)
        self.assertAlmostEqual(d*d, s*s-2*p+1)

    def test_pqd_matrix_can_have_rank_three_and_distance_moves(self):
        p = np.array([1.5, 0.8, 1.2, 0.6])
        q = np.array([0.2, 0.7, -0.4, 0.3])
        d = np.hypot(p-1, q)
        matrix = np.column_stack((p,q,d))
        self.assertEqual(np.linalg.matrix_rank(matrix), 3)
        self.assertTrue(np.any(np.abs(np.diff(d)) > 0))


if __name__ == "__main__": unittest.main()
