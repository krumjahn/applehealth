import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from unittest.mock import patch

from healthai.dashboard import TEMPLATES, build_dashboard_data, demo_data, write_dashboard
from healthai.health_data import convert_unit


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "export.xml"

    def export(self, records=(), workouts=()):
        root = ET.Element("HealthData")
        for attrs in records:
            ET.SubElement(root, "Record", attrs)
        for attrs in workouts:
            ET.SubElement(root, "Workout", attrs)
        ET.ElementTree(root).write(self.path, encoding="utf-8", xml_declaration=True)
        return self.path

    def record(self, kind="StepCount", value="1000", unit="count", day="2026-10-10", source="Apple Watch", **extra):
        return {
            "type": "HKQuantityTypeIdentifier" + kind,
            "sourceName": source, "value": str(value), "unit": unit,
            "startDate": day + " 09:00:00 +0800",
            "endDate": day + " 10:00:00 +0800", **extra,
        }

    def workout(self, **extra):
        return {"sourceName": "Apple Watch", "workoutActivityType": "HKWorkoutActivityTypeRunning",
                "startDate": "2026-10-10 09:00:00 +0800", "endDate": "2026-10-10 11:00:00 +0800",
                "duration": "2700", "durationUnit": "s", **extra}

    def test_steps_use_existing_source_reconciliation_and_filter(self):
        self.export([self.record(value=1000), self.record(value=800, source="iPhone")])
        report = build_dashboard_data(self.path)
        self.assertEqual(report["series"]["steps"], {"2026-10-10": 1000})
        filtered = build_dashboard_data(self.path, sources=["iPhone"])
        self.assertEqual(filtered["summary"]["steps"]["value"], 800)

    def test_missing_days_are_not_zero_filled_and_prior_period_is_matched(self):
        self.export([self.record(value=1000, day="2026-10-01"), self.record(value=2000, day="2026-10-10"),
                     self.record(value=500, day="2026-09-01"), self.record(value=9999, day="2026-09-11")])
        report = build_dashboard_data(self.path)
        summary = report["summary"]["steps"]
        self.assertEqual(summary["value"], 1500)
        self.assertEqual(summary["previous"], 500)
        self.assertEqual(summary["days"], 2)
        self.assertEqual(report["previous_end"], "2026-09-10")
        self.assertIsNone(report["summary"]["hrv"]["value"])

    def test_selected_month_and_window_exclude_other_records(self):
        self.export([self.record(day="2020-01-01"), self.record(day="2026-09-01"), self.record(day="2026-10-10")])
        report = build_dashboard_data(self.path, "2026-09")
        self.assertEqual(report["month"], "September 2026")
        self.assertEqual(report["through"], "2026-09-01")
        self.assertEqual(report["series"]["steps"], {"2026-09-01": 1000})

    def test_hrv_seconds_and_resting_hr_bpm_are_normalized(self):
        self.export([self.record("HeartRateVariabilitySDNN", .05, "s"), self.record("RestingHeartRate", 60, "bpm")])
        report = build_dashboard_data(self.path)
        self.assertEqual(report["summary"]["hrv"]["value"], 50)
        self.assertEqual(report["summary"]["resting_hr"]["value"], 60)
        self.assertEqual(convert_unit(0.04, "s", "ms"), 40)

    def test_unsupported_units_and_nonfinite_values_are_reported(self):
        self.export([self.record(), self.record("RestingHeartRate", 20, "wrong"),
                     self.record("HeartRateVariabilitySDNN", "NaN", "ms"), self.record(value=-10)])
        report = build_dashboard_data(self.path)
        self.assertIsNone(report["summary"]["hrv"]["value"])
        self.assertIsNone(report["summary"]["resting_hr"]["value"])
        self.assertGreaterEqual(len(report["warnings"]), 2)
        json.dumps(report, allow_nan=False)

    def test_sleep_overlaps_stages_and_in_bed_are_not_double_counted(self):
        common = {"type": "HKCategoryTypeIdentifierSleepAnalysis", "startDate": "2026-10-09 23:00:00 +0800", "endDate": "2026-10-10 07:00:00 +0800"}
        self.export([
            {**common, "sourceName": "Apple Watch", "value": "HKCategoryValueSleepAnalysisAsleepCore"},
            {**common, "sourceName": "Other tracker", "value": "HKCategoryValueSleepAnalysisAsleepUnspecified"},
            {**common, "sourceName": "Apple Watch", "value": "HKCategoryValueSleepAnalysisInBed"},
        ])
        self.assertEqual(build_dashboard_data(self.path)["series"]["sleep"], {"2026-10-10": 8})

    def test_in_bed_only_is_missing_sleep(self):
        record = self.record(type="HKCategoryTypeIdentifierSleepAnalysis", value="HKCategoryValueSleepAnalysisInBed")
        self.export([self.record(), record])
        self.assertEqual(build_dashboard_data(self.path)["series"]["sleep"], {})

    def test_paused_workout_active_duration_and_duplicates(self):
        self.export(workouts=[self.workout(), self.workout(sourceName="Other tracker")])
        data = build_dashboard_data(self.path)
        self.assertEqual(data["summary"]["workouts"]["value"], 45)
        self.assertEqual(len(data["workouts"]), 1)

    def test_duplicate_workouts_with_different_offsets_count_once(self):
        self.export(workouts=[self.workout(), self.workout(
            sourceName="Other tracker", startDate="2026-10-10 01:00:00 +0000",
            endDate="2026-10-10 03:00:00 +0000")])
        self.assertEqual(build_dashboard_data(self.path)["summary"]["workouts"]["value"], 45)

    def test_partial_month_still_contains_ninety_days_of_trends(self):
        self.export([self.record(day="2026-07-15"), self.record(day="2026-10-01")])
        data = build_dashboard_data(self.path)
        self.assertEqual(data["window_start"], "2026-07-04")
        self.assertIn("2026-07-15", data["series"]["steps"])

    def test_real_data_generation_never_opens_a_network_connection(self):
        self.export([self.record()])
        with patch("socket.socket.connect", side_effect=AssertionError("Unexpected network access")):
            data = build_dashboard_data(self.path)
            write_dashboard(data, self.root / "offline.html")

    def test_input_changed_between_scans_is_rejected(self):
        from healthai.exporter import _open_xml
        from contextlib import contextmanager
        self.export([self.record()])
        calls = 0

        @contextmanager
        def changing_input(path):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.export([self.record(value=2000)])
            with _open_xml(path) as stream:
                yield stream

        with patch("healthai.dashboard._open_xml", changing_input):
            with self.assertRaisesRegex(ValueError, "Input changed"):
                build_dashboard_data(self.path)

    def test_invalid_workout_duration_falls_back_with_warning(self):
        for value in ("-1", "NaN", "999999", "not a number"):
            with self.subTest(value=value):
                self.export(workouts=[self.workout(duration=value)])
                report = build_dashboard_data(self.path)
                self.assertEqual(report["summary"]["workouts"]["value"], 120)
                self.assertTrue(report["warnings"])

    def test_zip_and_directory_match_xml_without_extracting(self):
        self.export([self.record()])
        archive = self.root / "export.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.write(self.path, "apple_health_export/export.xml")
            z.writestr("../../never-extracted.txt", "no")
        expected = build_dashboard_data(self.path)["series"]
        self.assertEqual(build_dashboard_data(archive)["series"], expected)
        self.assertEqual(build_dashboard_data(self.root)["series"], expected)
        self.assertFalse((self.root / "apple_health_export").exists())

    def test_empty_wrong_root_missing_source_and_missing_month_fail(self):
        self.export()
        with self.assertRaisesRegex(ValueError, "No supported"):
            build_dashboard_data(self.path)
        self.export([self.record()])
        with self.assertRaisesRegex(ValueError, "No supported"):
            build_dashboard_data(self.path, sources=["Missing tracker"])
        with self.assertRaisesRegex(ValueError, "No supported records in"):
            build_dashboard_data(self.path, "2025-01")
        self.path.write_text("<Other/>")
        with self.assertRaisesRegex(ValueError, "HealthData"):
            build_dashboard_data(self.path)

    def test_unknown_month_invalid_month_and_all_invalid_data_fail(self):
        self.export([self.record(value="NaN")])
        with self.assertRaisesRegex(ValueError, "No usable"):
            build_dashboard_data(self.path)
        for month in ("2026-13", "2026-1", "bad", "0001-01"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                demo_data(month)

    def test_output_escapes_user_strings_and_never_overwrites(self):
        report = demo_data()
        malicious = '</script><script>alert("x")</script>'
        report["sources"] = [malicious]
        output = self.root / "report.html"
        write_dashboard(report, output)
        html = output.read_text()
        self.assertNotIn(malicious, html)
        payload = re.search(r'<script id="health-data" type="application/json">(.*?)</script>', html, re.S).group(1)
        self.assertEqual(json.loads(payload)["sources"], [malicious])
        self.assertIn("connect-src 'none'", html)
        with self.assertRaises(FileExistsError):
            write_dashboard(report, output)
        self.assertEqual(output.read_text(), html)

    def test_templates_preserve_the_same_data_and_embed_their_assets(self):
        data = demo_data()
        for template in TEMPLATES:
            with self.subTest(template=template):
                output = self.root / (template + ".html")
                write_dashboard(data, output, template)
                html = output.read_text()
                payload = re.search(r'<script id="health-data" type="application/json">(.*?)</script>', html, re.S).group(1)
                embedded = json.loads(payload)
                self.assertEqual(embedded.pop("template"), template)
                self.assertEqual(embedded, data)
                self.assertNotIn("__DASHBOARD_", html)
                self.assertNotRegex(html, r'<script\s+src=|<link\s+[^>]*href=')
        self.assertNotIn("template", data)

    def test_unknown_template_fails_before_creating_output(self):
        output = self.root / "unknown.html"
        with self.assertRaisesRegex(ValueError, "Unknown template"):
            write_dashboard(demo_data(), output, "not-a-template")
        self.assertFalse(output.exists())

    def test_cli_template_selection_and_validation(self):
        output = self.root / "observatory.html"
        result = self.run_cli("--demo", "--template", "observatory", "--out", str(output), no_site=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"template": "observatory"', output.read_text())
        self.assertEqual(self.run_cli("--demo", "--template", "unknown").returncode, 2)

    def run_cli(self, *args, no_site=False):
        env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"), "APPLEHEALTH_PREFS": str(self.root / "must-not-exist.json")}
        return subprocess.run([sys.executable, *(["-S"] if no_site else []), "-m", "healthai", "dashboard", *args], capture_output=True, text=True, env=env)

    def test_demo_runs_without_site_packages_or_preferences(self):
        output = self.root / "demo.html"
        result = self.run_cli("--demo", "--out", str(output), no_site=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(output.exists())
        self.assertFalse((self.root / "must-not-exist.json").exists())
        self.assertIn('"demo": true', output.read_text())

    def test_cli_rejects_conflicting_arguments_and_existing_output(self):
        self.assertEqual(self.run_cli().returncode, 2)
        self.assertEqual(self.run_cli("export.xml", "--demo").returncode, 2)
        self.assertEqual(self.run_cli("--demo", "--source", "Watch").returncode, 2)
        output = self.root / "existing.html"
        output.write_text("Keep this")
        result = self.run_cli("--demo", "--out", str(output))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(output.read_text(), "Keep this")

    def test_malformed_xml_fails_without_publishing(self):
        self.path.write_text('<HealthData><Record type="broken">')
        output = self.root / "bad.html"
        result = self.run_cli(str(self.path), "--out", str(output))
        self.assertEqual(result.returncode, 1)
        self.assertIn("Dashboard failed", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
