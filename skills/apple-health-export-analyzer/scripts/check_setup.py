#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

from openclaw_common import configure_analyzer, discover_repo_root, ensure_required_csvs, load_analyzer, to_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify applehealth OpenClaw setup.")
    parser.add_argument("--repo", help="Path to the cloned applehealth repo")
    parser.add_argument("--export", help="Path to Apple Health export.xml")
    parser.add_argument("--out", help="Output directory for generated CSV files")
    args = parser.parse_args()

    try:
        repo_root = discover_repo_root(args.repo)
        analyzer = load_analyzer(repo_root)
        config = configure_analyzer(analyzer, args.export, args.out)
        csvs = ensure_required_csvs(
            analyzer,
            [
                "steps_data.csv",
                "sleep_data.csv",
                "workout_data.csv",
                "heart_rate_data.csv",
            ],
        )

        payload = {
            "success": True,
            "repo_root": str(repo_root),
            "output_dir": config["out_dir"],
            "export_path": config["export_path"],
            "checks": {
                "export_exists": bool(config["export_path"] and os.path.exists(config["export_path"])),
                "steps_csv": os.path.exists(csvs["steps_data.csv"]),
                "sleep_csv": os.path.exists(csvs["sleep_data.csv"]),
                "workout_csv": os.path.exists(csvs["workout_data.csv"]),
                "heart_rate_csv": os.path.exists(csvs["heart_rate_data.csv"]),
            },
        }
        print(to_json(payload))
        return 0
    except Exception as exc:
        print(to_json({"success": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
