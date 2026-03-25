---
name: apple-health-export-analyzer
description: Use when a user wants OpenClaw to analyze Apple Health data either from the Health Data AI Analyzer Mac app or from an Apple Health or HealthKit export.xml with the open-source applehealth repo, verify setup, generate a daily brief, compare recent step and sleep trends, produce a weekly summary, or set up a recurring daily health message.
---

# Apple Health Export Analyzer

This skill gives OpenClaw two ways to read Apple Health data:

- preferred: use the `Health Data AI Analyzer` Mac app if its local API is running
- fallback: use the open-source `applehealth` repo with an `export.xml`

Use it when the user wants one of these outcomes:
- verify the local setup
- generate a daily brief from recent Apple Health data
- compare steps and sleep over the last 7 days
- produce a weekly summary with workouts and heart rate context
- set up a recurring daily health message with OpenClaw heartbeat or automation

## Quick workflow

1. First try `--source auto`.
2. If the Mac app local API is reachable, use that.
3. Otherwise use the `applehealth` repo plus `export.xml`.
4. Verify setup with `scripts/check_setup.py`.
5. For a daily brief, use `scripts/daily_brief.py`.
6. For a 7-day comparison, use `scripts/compare_recent_trends.py`.
7. For a weekly summary, use `scripts/weekly_summary.py`.

If the repo is not in the current workspace, ask the user to clone:

```bash
git clone https://github.com/krumjahn/applehealth.git
```

If needed, read:
- [workflow](references/workflow.md) for exact commands and expected outputs
- [troubleshooting](references/troubleshooting.md) when setup fails
- [heartbeat](references/heartbeat.md) for recurring daily messages

## Sources

### Option 1: Health Data AI Analyzer Mac app

- local API running on the Mac
- app has a saved integration dataset
- no `export.xml` needed

### Option 2: applehealth repo

- a cloned `applehealth` repo
- an Apple Health `export.xml`

Optional:
- `APPLEHEALTH_REPO` environment variable pointing to the repo root
- `--repo`, `--export`, and `--out` flags for the bundled scripts
- `--source auto|mac-app|export`

## Core commands

### Verify setup

```bash
python skills/apple-health-export-analyzer/scripts/check_setup.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis
```

### Daily brief

```bash
python skills/apple-health-export-analyzer/scripts/daily_brief.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis --date 2026-03-19
```

### Compare recent trends

```bash
python skills/apple-health-export-analyzer/scripts/compare_recent_trends.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis --days 7
```

### Weekly summary

```bash
python skills/apple-health-export-analyzer/scripts/weekly_summary.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis --days 7
```

## Response style

When the scripts return JSON:
- summarize it into a concise health brief
- call out missing data explicitly
- give practical suggestions, not medical advice
- do not invent metrics that are absent

For daily brief responses, prefer this structure:
- Status
- What changed
- 3 suggestions
- Missing data

## Example output

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
