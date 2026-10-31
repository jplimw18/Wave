import math
import unittest
from experiment import triangle, from_ratio, wave


class HypotenuseTests(unittest.TestCase):
    def test_normalized_grid_and_phase_identity(self):
        for s in (0,.25,.5,.75,1):
            for i in range(101):
                point=from_ratio(s,i/100)
                self.assertGreaterEqual(point['Q'],0)
                self.assertLessEqual(point['Q'],s+1e-15)
                self.assertAlmostEqual(point['P']**2+point['Q']**2,s*s,places=14)
                if s:
                    for t in (0,.13,.25,.62,1):
                        self.assertAlmostEqual(wave(point,t),s*math.sin(2*math.pi*t+point['theta']),places=14)

    def test_endpoints_zero_and_balance(self):
        self.assertEqual(triangle(0,0)['theta'],None)
        self.assertEqual(triangle(.8,.8)['Q'],0)
        self.assertAlmostEqual(triangle(.8,0)['Q'],.8)
        point=from_ratio(.8,1/math.sqrt(2))
        self.assertAlmostEqual(point['P'],point['Q'])
        self.assertAlmostEqual(point['theta'],math.pi/4)

    def test_invalid_inputs_are_rejected(self):
        for s,p in ((.2,.3),(-1,0),(1.1,1),(1,-.1),(True,0),(math.nan,0),(1,math.inf),(None,0)):
            with self.assertRaises(ValueError): triangle(s,p)
        for a in (-.1,1.1,math.nan,True):
            with self.assertRaises(ValueError): from_ratio(.8,a)

    def test_near_boundary_and_distance(self):
        p=math.nextafter(1,0); point=triangle(1,p)
        self.assertGreater(point['Q'],0)
        self.assertAlmostEqual(point['D']**2,1-2*p+1,places=14)


if __name__=='__main__': unittest.main()
