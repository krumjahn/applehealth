#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

from openclaw_common import (
    choose_source,
    configure_analyzer,
    discover_repo_root,
    ensure_required_csvs,
    fetch_mac_app_openclaw_status,
    load_analyzer,
    to_json,
    try_fetch_mac_app_openclaw_status,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify applehealth OpenClaw setup.")
    parser.add_argument("--source", choices=["auto", "mac-app", "export"], default="auto", help="Preferred data source")
    parser.add_argument("--repo", help="Path to the cloned applehealth repo")
    parser.add_argument("--export", help="Path to Apple Health export.xml")
    parser.add_argument("--out", help="Output directory for generated CSV files")
    args = parser.parse_args()

    try:
        selected_source = choose_source(args.source)
        payload = {
            "success": True,
            "selected_source": selected_source,
            "mac_app": None,
            "export_workflow": None,
        }

        mac_status = try_fetch_mac_app_openclaw_status()
        if mac_status:
            payload["mac_app"] = {
                "reachable": True,
                "status": mac_status,
            }
        elif args.source in {"auto", "mac-app"}:
            payload["mac_app"] = {"reachable": False}

        if selected_source == "mac-app":
            payload["data"] = {"mode": "mac-app", "summary": (fetch_mac_app_openclaw_status().get("summary"))}
            print(to_json(payload))
            return 0

        repo_root = discover_repo_root(args.repo)
        analyzer = load_analyzer(repo_root)
        config = configure_analyzer(analyzer, args.export, args.out)
        csvs = ensure_required_csvs(analyzer, ["steps_data.csv", "sleep_data.csv", "workout_data.csv", "heart_rate_data.csv"])

        payload["export_workflow"] = {
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
