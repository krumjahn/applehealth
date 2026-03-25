# Workflow

## Repo setup

```bash
git clone https://github.com/krumjahn/applehealth.git
cd applehealth
./run
```

The OpenClaw scripts work best when you already know:
- the repo root
- the path to `export.xml`
- the output directory for generated CSV files

## Mac app mode

If the `Health Data AI Analyzer` Mac app is running locally and has a saved integration dataset, the scripts can read that first.

For OpenClaw sessions that do not expose local file or shell tools, install the companion plugin from the `krumjahn/applehealth` repo:

```bash
git clone https://github.com/krumjahn/applehealth.git
cd applehealth
python skills/apple-health-export-analyzer/scripts/install_mac_app_companion.py --restart
```

Then use the companion skill in OpenClaw:

```text
Use the health-analyzer-mac-local skill. Give me my daily health brief for today and 3 suggestions.
```

Use:

```bash
python skills/apple-health-export-analyzer/scripts/check_setup.py --source mac-app
python skills/apple-health-export-analyzer/scripts/daily_brief.py --source mac-app
```

Or let the scripts choose automatically:

```bash
python skills/apple-health-export-analyzer/scripts/check_setup.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis
```

## Common commands

### Verify setup

```bash
python skills/apple-health-export-analyzer/scripts/check_setup.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis
```

### Generate a daily brief

```bash
python skills/apple-health-export-analyzer/scripts/daily_brief.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis
```

### Compare steps and sleep over the last 7 days

```bash
python skills/apple-health-export-analyzer/scripts/compare_recent_trends.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis --days 7
```

### Generate a weekly summary

```bash
python skills/apple-health-export-analyzer/scripts/weekly_summary.py --source auto --repo /path/to/applehealth --export /path/to/export.xml --out /path/to/analysis --days 7
```

## Expected outputs

- `check_setup.py` returns JSON with repo path, export path, output dir, and CSV readiness.
- `daily_brief.py` returns JSON with daily brief fields for steps, sleep, heart rate, workouts, and signals.
- `compare_recent_trends.py` returns trailing step and sleep series plus averages.
- `weekly_summary.py` returns trailing averages and totals for steps, sleep, workouts, and heart rate.
