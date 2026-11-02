import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile

from healthai.exporter import convert_export


EXPORT = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData [<!ELEMENT HealthData ANY>]>
<HealthData locale="en_HK">
  <ExportDate value="2026-11-02"/>
  <Me HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexNotSet"/>
  <Record type="steps" value="12" unit="count" sourceName="Watch"/>
  <Record type="distance" value="1.5" unit="mi" sourceName="手錶, Watch" extra="late column">
    <MetadataEntry key="note" value="first"/>
    <MetadataEntry key="note" value="second &amp; last"/>
  </Record>
  <Workout workoutActivityType="Walking" duration="20">
    <WorkoutStatistics type="distance" sum="1.5" unit="mi"/>
    <WorkoutRoute><FileReference path="workout-routes/route.gpx"/></WorkoutRoute>
  </Workout>
  <ActivitySummary dateComponents="2026-11-02" activeEnergyBurned="100"/>
  <ClinicalRecord type="example"/>
</HealthData>'''


class ExporterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "export.xml"
        self.source.write_text(EXPORT, encoding="utf-8")
        self.output = self.root / "output"

    def test_csv_json_preserve_raw_values_late_columns_and_nested_children(self):
        report = convert_export(self.source, self.output, "both")
        records = json.loads((self.output / "records.json").read_text())
        with (self.output / "records.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["extra"], "")
        self.assertEqual(rows[1]["extra"], "late column")
        self.assertEqual(rows[1]["value"], "1.5")
        self.assertEqual(rows[1]["unit"], "mi")
        self.assertEqual(rows[1]["sourceName"], "手錶, Watch")
        self.assertEqual(rows[1]["metadata:note"], "second & last")
        self.assertEqual(json.loads(rows[1]["children"]), records[1]["children"])
        self.assertEqual(len(records[1]["children"]), 2)
        workout = json.loads((self.output / "workouts.json").read_text())[0]
        self.assertEqual(workout["children"][0]["attributes"]["sum"], "1.5")
        self.assertEqual(workout["children"][1]["children"][0]["attributes"]["path"], "workout-routes/route.gpx")
        self.assertEqual(report["counts"], {"Record": 2, "Workout": 1, "ActivitySummary": 1})
        self.assertEqual(report["unsupported_top_level_elements"], {"ClinicalRecord": 1})
        self.assertEqual(report["omitted_document_metadata"], {"ExportDate": 1, "Me": 1})
        self.assertEqual(report["xml_sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(json.loads((self.output / "export_report.json").read_text()), report)

    def test_zip_is_read_without_extracting_paths(self):
        archive = self.root / "export.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            handle.writestr("apple_health_export/export.xml", EXPORT)
            handle.writestr("../../should-not-extract.txt", "unrelated")
            handle.writestr("apple_health_export/export_cda.xml", "unrelated")
        report = convert_export(archive, self.output, "both")
        self.assertEqual(report["counts"]["Record"], 2)
        self.assertEqual(set(p.name for p in self.root.iterdir()), {"export.xml", "export.zip", "output"})

    def test_json_only_produces_valid_arrays_without_csv_files(self):
        report = convert_export(self.source, self.output, "json")
        for tag, filename in [("Record", "records"), ("Workout", "workouts"), ("ActivitySummary", "activity_summary")]:
            rows = json.loads((self.output / f"{filename}.json").read_text())
            self.assertEqual(len(rows), report["counts"][tag])
        self.assertEqual(list(self.output.glob("*.csv")), [])

    def test_directory_input_and_empty_tables(self):
        self.source.write_text('<HealthData><Record value="0"/></HealthData>')
        convert_export(self.root, self.output, "both")
        self.assertEqual(json.loads((self.output / "workouts.json").read_text()), [])
        with (self.output / "workouts.csv").open(newline="") as handle:
            reader = csv.DictReader(handle)
            self.assertIn("workoutActivityType", reader.fieldnames)
            self.assertEqual(list(reader), [])

    def test_malformed_xml_publishes_nothing_and_removes_staging_files(self):
        self.source.write_text('<HealthData><Record value="1"/><Record>')
        with self.assertRaises(ET.ParseError):
            convert_export(self.source, self.output, "both")
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_existing_destination_is_never_overwritten(self):
        self.output.mkdir()
        marker = self.output / "keep.txt"
        marker.write_text("user work")
        with self.assertRaises(FileExistsError):
            convert_export(self.source, self.output)
        self.assertEqual(marker.read_text(), "user work")

    def test_input_changed_between_passes_is_rejected_even_with_same_counts(self):
        def mutate(message):
            if message == "Writing CSV files…":
                self.source.write_text(EXPORT.replace('value="12"', 'value="13"'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Input changed"):
            convert_export(self.source, self.output, "both", mutate)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_zip_with_missing_or_ambiguous_xml_is_rejected(self):
        for names in [("export_cda.xml",), ("a/export.xml", "b/export.xml")]:
            with self.subTest(names=names):
                archive = self.root / "export.zip"
                with zipfile.ZipFile(archive, "w") as handle:
                    for name in names:
                        handle.writestr(name, EXPORT)
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    convert_export(archive, self.output)
                self.assertFalse(self.output.exists())

    def test_invalid_root_empty_document_and_reserved_columns_are_rejected(self):
        for xml in [
            "<Other><Record/></Other>",
            "<HealthData/>",
            '<HealthData><Record children="collision"/></HealthData>',
        ]:
            with self.subTest(xml=xml):
                self.source.write_text(xml)
                with self.assertRaises(ValueError):
                    convert_export(self.source, self.output)
                self.assertFalse(self.output.exists())

    def test_write_failure_or_cancel_does_not_publish_partial_results(self):
        with patch("healthai.exporter.csv.DictWriter.writerow", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                convert_export(self.source, self.output, "both")
        self.assertEqual(list(self.root.iterdir()), [self.source])
        def cancel(message):
            raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            convert_export(self.source, self.output, progress=cancel)
        self.assertEqual(list(self.root.iterdir()), [self.source])

    def test_cli_runs_without_site_packages_network_or_preferences(self):
        # -S excludes installed AI/dataframe packages. The audit hook rejects
        # any socket operation, including DNS, even on localhost.
        script = '''import runpy, sys
def deny_network(event, args):
    if event.startswith("socket."):
        raise AssertionError("Network access attempted: " + event)
sys.addaudithook(deny_network)
sys.argv = ["healthai", "convert", *sys.argv[1:]]
runpy.run_module("healthai", run_name="__main__")
'''
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"),
                   APPLEHEALTH_PREFS=str(self.root / "must-not-create.json"))
        command = [sys.executable, "-S", "-c", script, str(self.source), "--out", str(self.output), "--quiet"]
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Saved 4 rows", result.stdout)
        self.assertIn("ClinicalRecord: 1", result.stderr)
        self.assertFalse((self.root / "must-not-create.json").exists())
        result = subprocess.run(command, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Output already exists", result.stderr)


if __name__ == "__main__":
    unittest.main()
