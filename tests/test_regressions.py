"""Post-initial failures, kept as independently runnable portable probes too."""
import importlib.util
from pathlib import Path
import unittest


def probe(name):
    path = Path(__file__).resolve().parents[1] / "tools" / "probes" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()


class ReviewRegressions(unittest.TestCase):
    def test_input_boundary(self):
        probe("input_boundary")
