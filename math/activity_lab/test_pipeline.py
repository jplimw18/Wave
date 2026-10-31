"""Testes da geometria atenuada, sinais de atividade e decomposições."""
import copy
import math
import unittest
import numpy as np
from pipeline import REFERENCES,activity,analyze,attenuate,derive,synthetic_input


class ActivityTests(unittest.TestCase):
    def row(self,**changes):
        row=synthetic_input()["rows"][2].copy();row.update(changes);return row

    def test_identity_bounds_and_endpoints(self):
        for s0 in (0,.2,.6,1):
            for alpha in np.linspace(0,1,11):
                for v in (0,.1,.5,1):
                    p=float(s0*alpha);r=attenuate(s0,p,v)
                    self.assertAlmostEqual(r["Sv"]**2,p*p+v*v*(s0*s0-p*p))
                    self.assertGreaterEqual(r["Sv"],0)
                    self.assertLessEqual(r["Sv"],s0+1e-15)
                    if v==0:self.assertAlmostEqual(r["Sv"],p)
                    if v==1:self.assertAlmostEqual(r["Sv"],s0)
        self.assertIsNone(attenuate(0,0,1)["theta"])

    def test_invalid_and_missing(self):
        for args in ((.5,.6,.5),(1,.2,-.1),(1,.2,1.1),(1,.2,float("nan"))):
            with self.assertRaises(ValueError):attenuate(*args)
        missing=attenuate(1,.2,None)
        self.assertIsNone(missing["Qv"])
        self.assertIsNotNone(missing["Q0"])

    def test_idle_requires_observed_ingress_pending_and_availability(self):
        idle=self.row(received=0,completed=0,failed=0,mean_latency_seconds=None)
        r=derive(idle,"synthetic")
        self.assertEqual(r["operational_state"],"ocioso_no_handler")
        self.assertEqual((r["P"],r["Q0"],r["V"],r["Qv"],r["Sv"]),(0,1,0,0,0))
        self.assertIsNone(r["quality_factor"])
        for change in (dict(available_end=False),dict(scrape_valid=None),dict(queued_start=None),dict(queue_provenance=None)):
            r=derive({**idle,**change},"synthetic")
            self.assertEqual(r["operational_state"],"indeterminado")
            self.assertIsNone(r["Qv"])

    def test_pending_without_new_arrivals_is_not_idle(self):
        r=derive(self.row(received=0,completed=0,failed=0,mean_latency_seconds=None,active_start=1,active_end=1),"synthetic")
        self.assertEqual(r["operational_state"],"pendente_no_handler")
        self.assertAlmostEqual(r["lambda_effective"],.2)
        self.assertAlmostEqual(r["V"],.2/5.2)
        self.assertGreater(r["Qv"],0)

    def test_contradictory_zero_activity_does_not_attenuate_to_zero(self):
        r=derive(self.row(received=0,completed=10,failed=0),"synthetic")
        self.assertEqual(r["operational_state"],"indeterminado")
        self.assertIsNone(r["V"])
        self.assertIsNone(r["Qv"])
        self.assertEqual(r["status"],"partial")

    def test_received_not_successes_controls_activity(self):
        raw=self.row(received=40,completed=40,failed=40)
        r=derive(raw,"synthetic")
        self.assertEqual(r["P"],0)
        self.assertAlmostEqual(r["V"],8/13)
        self.assertGreater(r["Qv"],0)

    def test_clipping_quality_and_source_are_preserved(self):
        r=derive(self.row(received=300,completed=300,failed=0),"synthetic")
        self.assertEqual(r["P_raw"],1.5)
        self.assertEqual(r["P"],1)
        self.assertTrue(r["clipping_applied"])
        self.assertEqual(r["raw"]["received"],300)
        r=derive(self.row(mean_latency_seconds=.2),"synthetic")
        self.assertAlmostEqual(r["quality_factor"],.5)

    def test_nonidentifiability_without_s0_metadata(self):
        a=attenuate(.5,.3,1)
        b=attenuate(math.hypot(.3,.8),.3,.5)
        self.assertAlmostEqual(a["Qv"],b["Qv"])
        self.assertNotEqual(a["Q0"],b["Q0"])
        self.assertNotEqual(a["V"],b["V"])
        self.assertAlmostEqual(a["Sv"],b["Sv"])

    def test_matrix_tensor_orthogonality_and_waves(self):
        rows=[derive(row,"synthetic") for row in synthetic_input()["rows"]]
        result=analyze(rows)["decomposition"]
        self.assertEqual(result["shape"],[2,2,10])
        self.assertEqual(result["wave_tensor_shape"],[2,10,64])
        self.assertLessEqual(result["wave_matrix_rank"],2)
        for name in ("hosvd_full_relative_error","core_norm_error","max_factor_orthogonality_error","max_cycle_energy_error"):
            self.assertLess(result[name],1e-12)
        for matrix in result["matrices"]:
            self.assertEqual(len(matrix["values"][0]),2)
            self.assertLess(matrix["right_factor_orthogonality_error"],1e-12)

    def test_missing_is_masked_and_duplicate_rejected(self):
        rows=[derive(row,"synthetic") for row in synthetic_input()["rows"]]
        rows[0]=derive(self.row(window=0,received=None),"synthetic")
        result=analyze(rows)
        self.assertEqual(result["omitted_window_indices"],[0])
        self.assertIsNone(result["tensor"][0][1][0])
        with self.assertRaises(ValueError):analyze(rows+[copy.deepcopy(rows[0])])


if __name__=="__main__":unittest.main()
