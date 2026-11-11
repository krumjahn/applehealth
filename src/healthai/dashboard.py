"""Portable, offline health dashboard. AI dependencies are never imported here."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import calendar
import json
import math
from pathlib import Path
import random
import re

from healthai.exporter import _elements, _HashedReader, _open_xml


METRICS = {
    "steps": {"label": "Daily steps", "unit": "steps", "decimals": 0},
    "sleep": {"label": "Time asleep", "unit": "hours", "decimals": 1},
    "resting_hr": {"label": "Resting heart rate", "unit": "bpm", "decimals": 1},
    "hrv": {"label": "Heart rate variability", "unit": "ms", "decimals": 1},
    "workouts": {"label": "Workout time", "unit": "min", "decimals": 0},
}
QUANTITY_TYPES = {
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_hr",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "hrv",
}
SLEEP_TYPE = "HKCategoryTypeIdentifierSleepAnalysis"
TEMPLATES = ("report", "recap", "observatory", "field-notes")


def parse_month(value):
    if not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError("Month must use YYYY-MM, for example 2026-10")
    result = date.fromisoformat(value + "-01")
    if result.year < 2:
        raise ValueError("Month must be in year 0002 or later")
    return result


def _month_end(month):
    return month.replace(day=calendar.monthrange(month.year, month.month)[1])


def _element_date(element):
    # Workouts belong to the start day; quantities and sleep to the end/wake day,
    # matching the existing analysis engine's calendar-day policy.
    field = "startDate" if element.tag == "Workout" else "endDate"
    return date.fromisoformat((element.get(field) or "")[:10])


def _supported(element, sources):
    if element.tag != "Workout" and not (
        element.tag == "Record" and element.get("type") in {*QUANTITY_TYPES, SLEEP_TYPE}
    ):
        return False
    return not sources or (element.get("sourceName") or "Unknown").casefold() in sources


def _series(values):
    return {str(day): round(float(value), 4) for day, value in values.items()
            if math.isfinite(float(value)) and value >= 0}


def _summaries(series, month, through):
    previous = (month - timedelta(days=1)).replace(day=1)
    previous_end = previous.replace(day=min(through.day, _month_end(previous).day))
    summaries = {}
    for key, points in series.items():
        current = [v for d, v in points.items() if str(month) <= d <= str(through)]
        prior = [v for d, v in points.items() if str(previous) <= d <= str(previous_end)]
        # Workouts are event totals. Other metrics are means of recorded days,
        # with their own coverage counts, never zero-filled missing days.
        value = (sum(current) if key == "workouts" else sum(current) / len(current)) if current else None
        old = (sum(prior) if key == "workouts" else sum(prior) / len(prior)) if prior else None
        summaries[key] = {
            "value": value, "previous": old, "days": len(current),
            "previous_days": len(prior),
            "change": (value - old) / old * 100 if value is not None and old else None,
        }
    return summaries, str(previous), str(previous_end)


def _payload(series, workouts, month, through, latest, sources, warnings, demo=False):
    summary, previous_start, previous_end = _summaries(series, month, through)
    return {
        "schema_version": 1, "demo": demo,
        "month": month.strftime("%B %Y"), "month_start": str(month),
        "through": str(through), "latest": str(latest),
        "window_start": str(through - timedelta(days=89)),
        "previous_start": previous_start, "previous_end": previous_end,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "metrics": METRICS, "series": series, "summary": summary,
        "workouts": workouts, "sources": sorted(sources), "warnings": warnings,
    }


def build_dashboard_data(source, month=None, sources=(), progress=None):
    """Scan XML/ZIP, retain only supported records in a 90-day window.

    Canonical source reconciliation is shared with the interactive analyzer.
    The two scans are hashed so a changed input cannot silently mix snapshots.
    """
    import xml.etree.ElementTree as ET
    from healthai.health_data import HealthDataSet, convert_unit, parse_apple_datetime, _source_rank

    path = Path(source).expanduser()
    chosen_month = parse_month(month) if month else None
    allowed = {s.strip().casefold() for s in sources if s.strip()}
    latest = None
    last_in_month = None
    counts = Counter()
    if progress:
        progress("Scanning export dates…")
    with _open_xml(path) as stream:
        reader = _HashedReader(stream)
        for element in _elements(reader):
            if not _supported(element, allowed):
                continue
            try:
                day = _element_date(element)
            except ValueError:
                counts["Records with missing or invalid dates skipped"] += 1
                continue
            latest = max(latest, day) if latest else day
            if chosen_month and day.replace(day=1) == chosen_month:
                last_in_month = max(last_in_month, day) if last_in_month else day
        first_digest = reader.digest.hexdigest()
    if latest is None:
        raise ValueError("No supported health records found. Check the export and any --source filter.")
    if chosen_month is None:
        chosen_month = parse_month(latest.strftime("%Y-%m"))
        last_in_month = latest
    if last_in_month is None:
        raise ValueError(f"No supported records in {month}. Choose another --month.")
    end = _month_end(chosen_month)
    start = last_in_month - timedelta(days=89)
    root = ET.Element("HealthData")
    included_sources = set()
    if progress:
        progress("Reading the selected month and its 90-day trend window…")
    with _open_xml(path) as stream:
        reader = _HashedReader(stream)
        for element in _elements(reader):
            if not _supported(element, allowed):
                continue
            try:
                day = _element_date(element)
            except ValueError:
                continue
            if not start <= day <= end:
                continue
            try:
                begins = parse_apple_datetime(element.get("startDate") or "")
                ends = parse_apple_datetime(element.get("endDate") or "")
                elapsed = (ends.timestamp() - begins.timestamp()) / 60
                if elapsed < 0:
                    raise ValueError("reversed interval")
                if element.tag == "Record" and element.get("type") in QUANTITY_TYPES:
                    value = float(element.get("value"))
                    if not math.isfinite(value) or value < 0:
                        raise ValueError("invalid quantity")
                if element.tag == "Workout":
                    # Keep valid active duration; elapsed time is only a fallback.
                    try:
                        duration = convert_unit(float(element.get("duration")), element.get("durationUnit") or "min", "min")
                    except (ValueError, TypeError):
                        duration = math.nan
                    if not math.isfinite(duration) or duration < 0 or duration > elapsed:
                        element.set("duration", str(elapsed))
                        element.set("durationUnit", "min")
                        counts["Workouts using elapsed time because active duration was invalid or absent"] += 1
                root.append(deepcopy(element))
                included_sources.add(element.get("sourceName") or "Unknown")
            except (TypeError, ValueError, OverflowError):
                counts["Records with invalid values or intervals skipped"] += 1
        if reader.digest.hexdigest() != first_digest:
            raise ValueError("Input changed while reading. Run again with a stable export.")
    if progress:
        progress("Reconciling sources and calculating daily summaries…")
    dataset = HealthDataSet(path, root=root)
    series = {key: {} for key in METRICS}
    for record_type, key in QUANTITY_TYPES.items():
        series[key] = _series(dataset.daily_quantity(record_type, "cumulative" if key == "steps" else "average"))
    sleep, _, _ = dataset.sleep_summary()
    # In-bed or awake-only rows do not establish zero hours of measured sleep.
    series["sleep"] = {d: v for d, v in _series(sleep).items() if v > 0}
    workouts = dataset.workouts()
    workout_rows = []
    if not workouts.empty:
        workouts = workouts.copy()
        workouts["rank"] = workouts["source"].map(lambda s: _source_rank(s, None))
        workouts["start_utc"] = workouts["start_time"].map(lambda t: datetime.fromisoformat(t).timestamp())
        workouts["end_utc"] = workouts["end_time"].map(lambda t: datetime.fromisoformat(t).timestamp())
        workouts = workouts.sort_values("rank").drop_duplicates(
            subset=["start_utc", "end_utc", "activity_type"]
        ).sort_values("start_time")
        series["workouts"] = _series(workouts.groupby("date")["duration_minutes"].sum())
        workout_rows = [
            {"date": str(row["date"]), "activity": row["activity_type"], "minutes": row["duration_minutes"]}
            for _, row in workouts.iterrows()
        ]
    for issue, count in Counter(dataset.issues).items():
        counts[issue] += count
    if not any(str(chosen_month) <= d <= str(last_in_month) for points in series.values() for d in points):
        raise ValueError("No usable measurements in the selected month after validation. Check units and record values.")
    warnings = [f"{message}: {count}" for message, count in sorted(counts.items())]
    return _payload(series, workout_rows, chosen_month, last_in_month, latest, included_sources, warnings)


def demo_data(month=None):
    """Deterministic fictional daily data; no file, preferences or AI access."""
    selected = parse_month(month or "2026-10")
    end = _month_end(selected)
    start = end - timedelta(days=89)
    rng = random.Random(42)
    series = {key: {} for key in METRICS}
    workouts = []
    for offset in range(90):
        day = start + timedelta(days=offset)
        key = str(day)
        recent = day.month == selected.month
        series["steps"][key] = int(7100 + (1100 if recent else 0) + 2100 * math.sin(offset * .7) + rng.randint(-1500, 1500))
        if offset % 23 != 9:
            series["sleep"][key] = round(7.1 + (.35 if recent else 0) + rng.uniform(-.8, .8), 2)
        series["resting_hr"][key] = round(60 - (2 if recent else 0) + rng.uniform(-3, 3), 1)
        if offset % 17 != 5:
            series["hrv"][key] = round(43 + (4 if recent else 0) + rng.uniform(-9, 9), 1)
        if day.weekday() in (0, 2, 5):
            minutes = rng.choice([30, 35, 45, 50, 60])
            series["workouts"][key] = minutes
            workouts.append({"date": key, "activity": "Running" if day.weekday() == 5 else "TraditionalStrengthTraining", "minutes": minutes})
    return _payload(series, workouts, selected, end, end, ["Demo Apple Watch", "Demo iPhone"], [], demo=True)


def write_dashboard(data, output, template="report"):
    """Create a standalone file exclusively; never replace an existing report."""
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template: {template}. Choose {', '.join(TEMPLATES)}")
    destination = Path(output).expanduser().absolute()
    assets = Path(__file__).parent
    document = (assets / "dashboard.html").read_text(encoding="utf-8")
    # An XML attribute may contain HTML. Keep embedded JSON from closing its
    # script tag; all user-controlled strings in the UI use textContent.
    payload = json.dumps({**data, "template": template}, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    html = document.replace("__DASHBOARD_CSS__", (assets / "dashboard.css").read_text(encoding="utf-8"))
    scripts = "\n".join((assets / name).read_text(encoding="utf-8")
                        for name in ("dashboard_coverage.js", "dashboard.js"))
    html = html.replace("__DASHBOARD_JS__", scripts)
    html = html.replace("__HEALTH_DATA__", payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        with destination.open("x", encoding="utf-8") as handle:
            created = True
            handle.write(html)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    return destination
