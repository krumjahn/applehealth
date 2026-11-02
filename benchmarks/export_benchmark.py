"""Reproducible local benchmark using generated data, never personal health data.

PYTHONPATH=src .venv/bin/python benchmarks/export_benchmark.py --records 10000 100000 1000000
Use --streaming-only for multi-gigabyte runs that would exhaust the legacy parser.
Each measurement runs in a fresh process; temporary inputs/outputs are removed.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time


RECORD = ('<Record type="HKQuantityTypeIdentifierStepCount" sourceName="Synthetic Watch" '
          'sourceVersion="1" unit="count" creationDate="2026-01-01 10:00:00 +0800" '
          'startDate="2026-01-01 09:00:00 +0800" endDate="2026-01-01 10:00:00 +0800" '
          'value="100"/>\n')


def worker(mode, source, output):
    started = time.perf_counter()
    if mode == "streaming":
        from healthai.exporter import convert_export
        report = convert_export(source, output)
        expected = report["counts"]["Record"]
    else:
        # The previous raw CSV algorithm: retain XML tree, a list of dicts,
        # and a DataFrame. Excludes its subsequent processed-metric work.
        import xml.etree.ElementTree as ET
        import pandas as pd
        root = ET.parse(source).getroot()
        rows = [dict(element.attrib) for element in root.findall(".//Record")]
        expected = len(rows)
        Path(output).mkdir()
        pd.DataFrame(rows).to_csv(Path(output) / "records.csv", index=False)
    elapsed = time.perf_counter() - started
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = peak / (1024 ** 2 if sys.platform == "darwin" else 1024)
    # Independently read the output and validate count and raw values.
    with (Path(output) / "records.csv").open(newline="") as handle:
        count = 0
        for row in csv.DictReader(handle):
            if row["value"] != "100" or row["unit"] != "count":
                raise ValueError("Output values changed")
            count += 1
    if count != expected:
        raise ValueError(f"Expected {expected} rows, got {count}")
    print(json.dumps({"mode": mode, "records": count, "seconds": round(elapsed, 3),
                      "peak_rss_mib": round(peak_mb, 2)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, nargs="+", default=[10000, 100000, 1000000])
    parser.add_argument("--streaming-only", action="store_true")
    parser.add_argument("--save", type=Path, help="Save results locally as JSON")
    parser.add_argument("--worker", choices=["legacy_raw", "streaming"])
    parser.add_argument("--source")
    parser.add_argument("--out")
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.source, args.out)
        return
    if any(count <= 0 for count in args.records):
        parser.error("--records values must be positive")
    results = {"python": platform.python_version(), "platform": platform.platform(),
               "fixture": "Synthetic flat step records; raw CSV only; one run per size/mode; warm filesystem cache",
               "measurements": []}
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    for count in args.records:
        with tempfile.TemporaryDirectory(prefix="healthai-benchmark-") as directory:
            source = Path(directory) / "export.xml"
            with source.open("w") as handle:
                handle.write("<HealthData>\n")
                batch = RECORD * 10000
                for _ in range(count // 10000):
                    handle.write(batch)
                handle.write(RECORD * (count % 10000))
                handle.write("</HealthData>\n")
            modes = ["streaming"] if args.streaming_only else ["legacy_raw", "streaming"]
            for mode in modes:
                print(f"Benchmarking {mode}: {count:,} rows, {source.stat().st_size / 1_000_000:.1f} MB XML…", file=sys.stderr, flush=True)
                completed = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--worker", mode,
                     "--source", str(source), "--out", str(Path(directory) / mode)],
                    env=env, check=True, capture_output=True, text=True,
                )
                measurement = json.loads(completed.stdout)
                measurement["xml_bytes"] = source.stat().st_size
                results["measurements"].append(measurement)
                print(json.dumps(measurement), file=sys.stderr, flush=True)
    rendered = json.dumps(results, indent=2) + "\n"
    if args.save:
        args.save.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
