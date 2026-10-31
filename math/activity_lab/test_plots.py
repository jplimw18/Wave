import tempfile
import unittest
from pathlib import Path

from plots import generate_plots


def sample_records():
    records=[]
    vals=[(0.4,0.8,0.2),(0.6,0.7,0.5),(0.7,0.6,0.7),(0.8,0.5,0.9)]
    for i,(p,q0,v) in enumerate(vals):
        qv=v*q0
        records.append(dict(service="api-a",window_index=i,source_kind="synthetic",P=p,Q0=q0,Qv=qv,
                            S0=1.0,Sv=(p*p+qv*qv)**.5,V=v,D=((p-1)**2+qv*qv)**.5,status="ok"))
    records.insert(1,dict(service="api-a",window_index=1.5,source_kind="synthetic",P=None,Q0=None,Qv=None,
                          S0=1.0,Sv=None,V=None,D=None,status="missing"))
    return records


class ActivityPlotTests(unittest.TestCase):
    def test_generates_valid_labeled_svgs_and_breaks_missing_path(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            paths=generate_plots(sample_records(),tmp,"SINTÉTICO")
            self.assertEqual([p.name for p in paths], ["activity.svg","trajectory.svg","waves.svg"])
            docs={p.name:p.read_text(encoding="utf-8") for p in paths}
            self.assertTrue(all(doc.startswith("<svg") and doc.endswith("</svg>") for doc in docs.values()))
            self.assertTrue(all("SINTÉTICO" in doc for doc in docs.values()))
            self.assertIn("Qv",docs["trajectory.svg"])
            self.assertIn("S0 ref=1",docs["waves.svg"])
            self.assertIn("Sv efetiva=",docs["waves.svg"])
            # A amostra ausente separa os dois segmentos da trajetória.
            self.assertEqual(docs["trajectory.svg"].count("<polyline"),2)
            self.assertEqual(docs["waves.svg"].count("portadora sintética 1 Hz"),3)

    def test_empty_records_still_make_valid_files(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            paths=generate_plots([],tmp,"MEDIÇÕES DO LAB + TRANSFORMAÇÃO EXPERIMENTAL")
            self.assertTrue(all(p.exists() for p in paths))
            self.assertIn("Não há três janelas válidas",paths[2].read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
