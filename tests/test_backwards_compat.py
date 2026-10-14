"""Regression tests for the backwards-compatibility shim (src/applehealth.py).

The v1.10 refactor reduced src/applehealth.py to ``from healthai.cli import main``,
which silently broke integrations that expect the full CLI namespace (e.g. the
OpenClaw skill scripts under skills/apple-health-export-analyzer/scripts/).
These tests pin the shim's behaviour: importing ``applehealth`` must yield the
``healthai.cli`` module itself, with module state setting intact.
"""
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class ApplehealthShimTests(unittest.TestCase):
    def test_shim_is_the_cli_module(self):
        import applehealth
        from healthai import cli

        self.assertIs(applehealth, cli)

    def test_shim_exposes_namespace_used_by_skill_scripts(self):
        import applehealth

        for name in (
            "main",
            "analyze_steps",
            "analyze_distance",
            "analyze_heart_rate",
            "analyze_weight",
            "analyze_sleep",
            "analyze_workouts",
            "get_output_dir",
            "get_output_path",
            "resolve_export_xml",
            "scan_export_types",
            "plt",
            "_set_saved_pref",
            "_get_saved_pref",
        ):
            self.assertTrue(hasattr(applehealth, name), f"missing attribute: {name}")

    def test_shim_module_state_is_settable(self):
        import applehealth

        sentinel = object()
        original = applehealth.__dict__.get("_output_dir", sentinel)
        applehealth._output_dir = "/tmp/shim-test"
        try:
            self.assertEqual(applehealth.get_output_path("x.csv"), "/tmp/shim-test/x.csv")
        finally:
            if original is sentinel:
                applehealth.__dict__.pop("_output_dir", None)
            else:
                applehealth._output_dir = original


if __name__ == "__main__":
    unittest.main()
