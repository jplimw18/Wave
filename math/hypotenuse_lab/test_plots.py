import tempfile
import unittest
from pathlib import Path

from plots import generate_plots


class PlotGenerationTests(unittest.TestCase):
    def test_outputs_provenance_and_missing_gaps(self):
        records = [
            dict(service="API A", window_index=0, source_kind="synthetic", P=.6, Q=.8, S=1., D=.5, alpha=.6, status="ok"),
            dict(service="API A", window_index=1, source_kind="synthetic", P=.65, Q=.76, S=1., D=.45, alpha=.65, status="ok"),
            dict(service="API A", window_index=2, source_kind="synthetic", P=None, Q=None, S=None, D=None, alpha=None, status="missing"),
            dict(service="API A", window_index=3, source_kind="synthetic", P=.75, Q=.66, S=1., D=.35, alpha=.75, status="ok"),
            dict(service="API A", window_index=4, source_kind="synthetic", P=.8, Q=.6, S=1., D=.3, alpha=.8, status="ok"),
        ]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            paths = generate_plots(records, tmp, "SINTÉTICO")
            self.assertEqual([p.name for p in paths], ["temporal.svg", "trajectory.svg", "waves.svg"])
            contents = {p.name: p.read_text(encoding="utf-8") for p in paths}
            self.assertTrue(all("SINTÉTICO" in text for text in contents.values()))
            self.assertIn("B45", contents["trajectory.svg"])
            self.assertIn("A=(1,0)", contents["trajectory.svg"])
            # The missing center sample leaves two separate trajectory polylines.
            self.assertEqual(contents["trajectory.svg"].count("<polyline"), 2)
            self.assertIn("1 Hz", contents["waves.svg"])

    def test_no_data_is_still_valid_svg(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            paths = generate_plots([], tmp, "SEM DADOS")
            self.assertTrue(all(p.exists() and p.read_text(encoding="utf-8").startswith("<svg") for p in paths))


if __name__ == "__main__":
    unittest.main()
