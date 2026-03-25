# Apple Health / HealthKit Export Analyzer for OpenClaw

This skill packages the open-source [`krumjahn/applehealth`](https://github.com/krumjahn/applehealth) workflow for OpenClaw.

It gives OpenClaw concrete scripts for:
- setup verification
- daily Apple Health briefs
- recent step and sleep comparisons
- weekly summaries
- recurring daily-message workflows

It is designed to show up for searches around:
- Apple Health
- HealthKit
- Apple Health export.xml
- sleep and steps analysis
- daily health brief

## Example

```text
Status
- Activity was below your recent baseline.

What changed
- Steps: 2,444 vs 7-day baseline 10,005
- Workouts: 0 minutes, 0 workouts
- Sleep: insufficient data

Suggestions
1. Add one easy walk instead of trying to catch up with a hard workout.
2. Use one fixed movement anchor like a walk after lunch.
3. Keep effort moderate when recovery data is missing.
```

## Requirements

- a clone of `https://github.com/krumjahn/applehealth`
- an Apple Health `export.xml`
- Python dependencies installed for that repo

## Start here

Run the setup verifier first:

```bash
python skills/apple-health-export-analyzer/scripts/check_setup.py --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis
```
