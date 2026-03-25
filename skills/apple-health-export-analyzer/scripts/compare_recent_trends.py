#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from openclaw_common import (
    choose_source,
    compute_recent_trends,
    configure_analyzer,
    discover_repo_root,
    ensure_required_csvs,
    fetch_mac_app_recent_trends,
    load_analyzer,
    load_sleep,
    load_steps,
    to_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare recent Apple Health step and sleep trends.")
    parser.add_argument("--source", choices=["auto", "mac-app", "export"], default="auto", help="Preferred data source")
    parser.add_argument("--repo", help="Path to the cloned applehealth repo")
    parser.add_argument("--export", help="Path to Apple Health export.xml")
    parser.add_argument("--out", help="Output directory for generated CSV files")
    parser.add_argument("--days", type=int, default=7, help="Number of days to compare")
    args = parser.parse_args()

    try:
        selected_source = choose_source(args.source)
        if selected_source == "mac-app":
            trends = fetch_mac_app_recent_trends(days=args.days)
            print(to_json({"success": True, "source": "mac-app", "data": trends}))
            return 0

        repo_root = discover_repo_root(args.repo)
        analyzer = load_analyzer(repo_root)
        configure_analyzer(analyzer, args.export, args.out)
        csvs = ensure_required_csvs(analyzer, ["steps_data.csv", "sleep_data.csv"])

        trends = compute_recent_trends(load_steps(csvs["steps_data.csv"]), load_sleep(csvs["sleep_data.csv"]), days=args.days)
        print(to_json({"success": True, "source": "export", "data": trends}))
        return 0
    except Exception as exc:
        print(to_json({"success": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
