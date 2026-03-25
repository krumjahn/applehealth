#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import sys

from openclaw_common import (
    compute_daily_brief,
    configure_analyzer,
    discover_repo_root,
    ensure_required_csvs,
    load_analyzer,
    load_heart_rate,
    load_sleep,
    load_steps,
    load_workouts,
    to_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a daily Apple Health brief for OpenClaw.")
    parser.add_argument("--repo", help="Path to the cloned applehealth repo")
    parser.add_argument("--export", help="Path to Apple Health export.xml")
    parser.add_argument("--out", help="Output directory for generated CSV files")
    parser.add_argument("--date", help="Date in YYYY-MM-DD format. Defaults to the latest available date.")
    args = parser.parse_args()

    try:
        repo_root = discover_repo_root(args.repo)
        analyzer = load_analyzer(repo_root)
        configure_analyzer(analyzer, args.export, args.out)
        csvs = ensure_required_csvs(
            analyzer,
            [
                "steps_data.csv",
                "sleep_data.csv",
                "workout_data.csv",
                "heart_rate_data.csv",
            ],
        )

        target_date = dt.date.fromisoformat(args.date) if args.date else None
        brief = compute_daily_brief(
            load_steps(csvs["steps_data.csv"]),
            load_sleep(csvs["sleep_data.csv"]),
            load_heart_rate(csvs["heart_rate_data.csv"]),
            load_workouts(csvs["workout_data.csv"]),
            date_value=target_date,
        )
        print(to_json({"success": True, "data": brief}))
        return 0
    except Exception as exc:
        print(to_json({"success": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
