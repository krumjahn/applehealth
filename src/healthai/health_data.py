"""Canonical parsing and aggregation for Apple Health XML exports."""
from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence
import math
import xml.etree.ElementTree as ET

import pandas as pd


APPLE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S %z"

STEP_COUNT = "HKQuantityTypeIdentifierStepCount"
DISTANCE_WALKING_RUNNING = "HKQuantityTypeIdentifierDistanceWalkingRunning"
HEART_RATE = "HKQuantityTypeIdentifierHeartRate"
RESTING_HEART_RATE = "HKQuantityTypeIdentifierRestingHeartRate"
HEART_RATE_VARIABILITY = "HKQuantityTypeIdentifierHeartRateVariabilitySDNN"
BODY_MASS = "HKQuantityTypeIdentifierBodyMass"
SLEEP_ANALYSIS = "HKCategoryTypeIdentifierSleepAnalysis"

TARGET_UNITS = {
    STEP_COUNT: "count",
    DISTANCE_WALKING_RUNNING: "km",
    HEART_RATE: "count/min",
    RESTING_HEART_RATE: "count/min",
    HEART_RATE_VARIABILITY: "ms",
    BODY_MASS: "kg",
}

KM_PER_MILE = 1.609344
KG_PER_POUND = 0.45359237

DISPLAY_UNITS = {
    "metric": {"distance": ("km", 1.0), "weight": ("kg", 1.0)},
    "imperial": {
        "distance": ("mi", 1.0 / KM_PER_MILE),
        "weight": ("lb", 1.0 / KG_PER_POUND),
    },
}


def display_unit(kind: str, unit_system: str) -> tuple[str, float]:
    """Return (label, factor-from-canonical) for showing a metric to the user."""
    system = DISPLAY_UNITS.get(unit_system) or DISPLAY_UNITS["metric"]
    return system[kind]

METRIC_EXPORTS = {
    STEP_COUNT: ("steps_data.csv", "cumulative"),
    DISTANCE_WALKING_RUNNING: ("distance_data.csv", "cumulative"),
    HEART_RATE: ("heart_rate_data.csv", "average"),
    BODY_MASS: ("weight_data.csv", "latest"),
}


def parse_apple_datetime(value: str) -> datetime:
    try:
        return datetime.strptime(value, APPLE_DATE_FORMAT)
    except ValueError:
        return datetime.fromisoformat(value)


def _normalized_unit(unit: str) -> str:
    return (unit or "").strip().replace(" ", "").lower()


def convert_unit(value: float, unit: str, target_unit: str) -> float:
    """Convert common HealthKit XML units into a canonical output unit."""
    source = _normalized_unit(unit)
    target = _normalized_unit(target_unit)
    if source == target:
        return float(value)

    if target == "count" and source in {"", "count", "counts"}:
        return float(value)
    if target == "count/min" and source in {
        "count/min",
        "count/minute",
        "bpm",
    }:
        return float(value)

    if target == "km":
        factors = {
            "m": 0.001,
            "meter": 0.001,
            "meters": 0.001,
            "mi": 1.609344,
            "mile": 1.609344,
            "miles": 1.609344,
            "ft": 0.0003048,
            "foot": 0.0003048,
            "feet": 0.0003048,
            "yd": 0.0009144,
            "yard": 0.0009144,
            "yards": 0.0009144,
            "cm": 0.00001,
        }
        if source in factors:
            return float(value) * factors[source]

    if target == "ms":
        if source in {"millisecond", "milliseconds"}:
            return float(value)
        if source in {"s", "sec", "second", "seconds"}:
            return float(value) * 1000

    if target == "kg":
        factors = {
            "g": 0.001,
            "gram": 0.001,
            "grams": 0.001,
            "lb": 0.45359237,
            "lbs": 0.45359237,
            "pound": 0.45359237,
            "pounds": 0.45359237,
            "oz": 0.028349523125,
            "stone": 6.35029318,
            "st": 6.35029318,
        }
        if source in factors:
            return float(value) * factors[source]

    if target == "kcal":
        if unit == "Cal" or source == "kcal":
            return float(value)
        factors = {
            "cal": 0.001,
            "kj": 0.239005736,
            "j": 0.000239005736,
        }
        if source in factors:
            return float(value) * factors[source]

    if target == "min":
        factors = {
            "sec": 1 / 60,
            "s": 1 / 60,
            "second": 1 / 60,
            "seconds": 1 / 60,
            "h": 60,
            "hr": 60,
            "hour": 60,
            "hours": 60,
        }
        if source in {"min", "minute", "minutes"}:
            return float(value)
        if source in factors:
            return float(value) * factors[source]

    raise ValueError(f"Unsupported unit conversion: {unit or '(blank)'} -> {target_unit}")


def _source_rank(source: str, priority: Sequence[str] | None) -> tuple[int, str]:
    normalized = (source or "Unknown").casefold()
    if priority:
        for index, preferred in enumerate(priority):
            if normalized == preferred.casefold():
                return index, normalized
        explicit_offset = len(priority)
    else:
        explicit_offset = 0

    if normalized in {"health", "apple health"}:
        automatic = 0
    elif "apple watch" in normalized or normalized.endswith(" watch"):
        automatic = 1
    elif "iphone" in normalized or "ipad" in normalized:
        automatic = 2
    else:
        automatic = 3
    return explicit_offset + automatic, normalized


def _empty_quantity_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "start",
            "end",
            "start_utc",
            "end_utc",
            "date",
            "value",
            "unit",
            "original_unit",
            "source",
            "device",
        ]
    )


class HealthDataSet:
    """A single parsed Apple Health export with metric-aware aggregations."""

    def __init__(
        self,
        export_path: str | Path,
        root: ET.Element | None = None,
        source_filter: Sequence[str] | None = None,
    ):
        self.export_path = Path(export_path).expanduser().resolve()
        self.root = root if root is not None else ET.parse(self.export_path).getroot()
        self.issues: list[str] = []
        cleaned = [source.strip() for source in (source_filter or []) if source.strip()]
        self.source_filter: set[str] | None = (
            {source.casefold() for source in cleaned} if cleaned else None
        )

    def _source_allowed(self, source: str | None) -> bool:
        if self.source_filter is None:
            return True
        return (source or "Unknown").casefold() in self.source_filter

    def quantity_records(self, record_type: str) -> pd.DataFrame:
        target_unit = TARGET_UNITS.get(record_type)
        rows: list[dict[str, Any]] = []
        for record in self.root.findall(".//Record"):
            if record.get("type") != record_type:
                continue
            if not self._source_allowed(record.get("sourceName")):
                continue
            try:
                start = parse_apple_datetime(record.get("startDate") or "")
                end = parse_apple_datetime(record.get("endDate") or "")
                if end.timestamp() < start.timestamp():
                    raise ValueError("endDate is before startDate")
                original_unit = record.get("unit") or ""
                value = float(record.get("value"))
                if target_unit:
                    value = convert_unit(value, original_unit, target_unit)
                rows.append(
                    {
                        "start": start,
                        "end": end,
                        "start_utc": start.timestamp(),
                        "end_utc": end.timestamp(),
                        "date": end.date(),
                        "value": value,
                        "unit": target_unit or original_unit,
                        "original_unit": original_unit,
                        "source": record.get("sourceName") or "Unknown",
                        "device": record.get("device") or "",
                    }
                )
            except (TypeError, ValueError) as error:
                self.issues.append(f"{record_type}: skipped record ({error})")

        if not rows:
            return _empty_quantity_frame()
        frame = pd.DataFrame(rows)
        return frame.drop_duplicates(
            subset=["start_utc", "end_utc", "value", "unit", "source"]
        ).sort_values(["start_utc", "end_utc"])

    @staticmethod
    def _reconcile_discrete(
        records: pd.DataFrame,
        source_priority: Sequence[str] | None,
    ) -> pd.DataFrame:
        if records.empty:
            return records
        reconciled = records.copy()
        reconciled["_source_rank"] = reconciled["source"].map(
            lambda source: _source_rank(source, source_priority)
        )
        reconciled = reconciled.sort_values(
            ["start_utc", "end_utc", "_source_rank"]
        )
        reconciled = reconciled.drop_duplicates(
            subset=["start_utc", "end_utc"], keep="first"
        )
        return reconciled.drop(columns=["_source_rank"])

    @staticmethod
    def _reconcile_cumulative_day(
        records: pd.DataFrame,
        source_priority: Sequence[str] | None,
    ) -> float:
        if records.empty:
            return 0.0

        timed = records[records["end_utc"] > records["start_utc"]]
        total = 0.0
        if not timed.empty:
            boundaries = sorted(
                set(timed["start_utc"].tolist() + timed["end_utc"].tolist())
            )
            active_by_segment: list[list[int]] = [
                [] for _ in range(max(0, len(boundaries) - 1))
            ]
            indexed = timed.reset_index(drop=True)
            for row_index, row in indexed.iterrows():
                start_index = bisect_left(boundaries, row["start_utc"])
                end_index = bisect_left(boundaries, row["end_utc"])
                for segment_index in range(start_index, end_index):
                    active_by_segment[segment_index].append(row_index)

            for segment_index, active_indices in enumerate(active_by_segment):
                if not active_indices:
                    continue
                active = indexed.iloc[active_indices]
                best_source = min(
                    active["source"].unique(),
                    key=lambda source: _source_rank(source, source_priority),
                )
                selected = active[active["source"] == best_source]
                duration = boundaries[segment_index + 1] - boundaries[segment_index]
                rates = selected["value"] / (
                    selected["end_utc"] - selected["start_utc"]
                )
                total += float(rates.sum()) * duration

        instantaneous = records[records["end_utc"] <= records["start_utc"]]
        if not instantaneous.empty:
            for _, group in instantaneous.groupby("start_utc"):
                best_source = min(
                    group["source"].unique(),
                    key=lambda source: _source_rank(source, source_priority),
                )
                total += float(group[group["source"] == best_source]["value"].sum())
        return total

    def daily_quantity(
        self,
        record_type: str,
        aggregation: str,
        source_priority: Sequence[str] | None = None,
        source_mode: str = "reconcile",
    ) -> pd.Series:
        records = self.quantity_records(record_type)
        if records.empty:
            empty = pd.Series(dtype=float, name="value")
            empty.index.name = "date"
            return empty

        if aggregation == "cumulative":
            if source_mode == "all":
                daily = records.groupby("date")["value"].sum()
            else:
                daily = pd.Series(
                    {
                        date: self._reconcile_cumulative_day(
                            group,
                            source_priority,
                        )
                        for date, group in records.groupby("date", sort=True)
                    },
                    dtype=float,
                )
        elif aggregation == "average":
            selected = (
                records
                if source_mode == "all"
                else self._reconcile_discrete(records, source_priority)
            )
            daily = selected.groupby("date")["value"].mean()
        elif aggregation == "latest":
            selected = (
                records
                if source_mode == "all"
                else self._reconcile_discrete(records, source_priority)
            )
            daily = (
                selected.sort_values(["date", "end_utc"])
                .groupby("date")["value"]
                .last()
            )
        else:
            raise ValueError(f"Unknown aggregation: {aggregation}")

        daily.index.name = "date"
        daily.name = "value"
        return daily.sort_index()

    def sleep_records(self) -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        for record in self.root.findall(".//Record"):
            if record.get("type") != SLEEP_ANALYSIS:
                continue
            if not self._source_allowed(record.get("sourceName")):
                continue
            try:
                start = parse_apple_datetime(record.get("startDate") or "")
                end = parse_apple_datetime(record.get("endDate") or "")
                if end.timestamp() < start.timestamp():
                    raise ValueError("endDate is before startDate")
                raw_value = record.get("value") or ""
                if "InBed" in raw_value:
                    sleep_type = "In Bed"
                elif "AsleepREM" in raw_value:
                    sleep_type = "REM Sleep"
                elif "AsleepCore" in raw_value:
                    sleep_type = "Core Sleep"
                elif "AsleepDeep" in raw_value:
                    sleep_type = "Deep Sleep"
                elif "AsleepUnspecified" in raw_value:
                    sleep_type = "Asleep"
                elif "Awake" in raw_value:
                    sleep_type = "Awake"
                else:
                    sleep_type = "Unknown"
                duration_hours = max(0.0, (end.timestamp() - start.timestamp()) / 3600)
                rows.append(
                    {
                        "start": start,
                        "end": end,
                        "start_utc": start.timestamp(),
                        "end_utc": end.timestamp(),
                        "night_date": end.date(),
                        "duration_hours": duration_hours,
                        "sleep_type": sleep_type,
                        "sleep_value": raw_value,
                        "source": record.get("sourceName") or "Unknown",
                    }
                )
            except (TypeError, ValueError) as error:
                self.issues.append(f"{SLEEP_ANALYSIS}: skipped record ({error})")

        if not rows:
            return pd.DataFrame(
                columns=[
                    "start",
                    "end",
                    "start_utc",
                    "end_utc",
                    "night_date",
                    "duration_hours",
                    "sleep_type",
                    "sleep_value",
                    "source",
                ]
            )
        return pd.DataFrame(rows).drop_duplicates(
            subset=[
                "start_utc",
                "end_utc",
                "sleep_type",
                "source",
            ]
        )

    @staticmethod
    def _sleep_segments(
        records: pd.DataFrame,
        source_priority: Sequence[str] | None,
        in_bed: bool,
    ) -> dict[str, float]:
        if records.empty:
            return {}
        selected = records[
            records["sleep_type"].eq("In Bed")
            if in_bed
            else ~records["sleep_type"].eq("In Bed")
        ].reset_index(drop=True)
        if selected.empty:
            return {}

        boundaries = sorted(
            set(selected["start_utc"].tolist() + selected["end_utc"].tolist())
        )
        stage_hours: dict[str, float] = defaultdict(float)
        stage_rank = {
            "Awake": 0,
            "REM Sleep": 1,
            "Core Sleep": 1,
            "Deep Sleep": 1,
            "Asleep": 2,
            "Unknown": 3,
            "In Bed": 0,
        }
        for index in range(len(boundaries) - 1):
            segment_start = boundaries[index]
            segment_end = boundaries[index + 1]
            if segment_end <= segment_start:
                continue
            active = selected[
                (selected["start_utc"] < segment_end)
                & (selected["end_utc"] > segment_start)
            ]
            if active.empty:
                continue
            best_source = min(
                active["source"].unique(),
                key=lambda source: _source_rank(source, source_priority),
            )
            source_records = active[active["source"] == best_source]
            sleep_type = min(
                source_records["sleep_type"],
                key=lambda stage: stage_rank.get(stage, 99),
            )
            stage_hours[sleep_type] += (segment_end - segment_start) / 3600
        return dict(stage_hours)

    def sleep_summary(
        self,
        source_priority: Sequence[str] | None = None,
    ) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
        records = self.sleep_records()
        if records.empty:
            daily_sleep = pd.Series(dtype=float, name="value")
            daily_sleep.index.name = "date"
            stages = pd.DataFrame()
            stages.index.name = "date"
            daily_in_bed = pd.Series(dtype=float, name="in_bed_hours")
            daily_in_bed.index.name = "date"
            return daily_sleep, stages, daily_in_bed

        stage_rows: dict[Any, dict[str, float]] = {}
        in_bed_rows: dict[Any, float] = {}
        for night_date, group in records.groupby("night_date", sort=True):
            stages = self._sleep_segments(group, source_priority, in_bed=False)
            in_bed = self._sleep_segments(group, source_priority, in_bed=True)
            stage_rows[night_date] = stages
            in_bed_rows[night_date] = in_bed.get("In Bed", math.nan)

        stage_daily = pd.DataFrame.from_dict(stage_rows, orient="index").fillna(0.0)
        stage_daily.index.name = "date"
        asleep_columns = [
            column
            for column in ("Asleep", "REM Sleep", "Core Sleep", "Deep Sleep")
            if column in stage_daily
        ]
        if asleep_columns:
            daily_sleep = stage_daily[asleep_columns].sum(axis=1)
        else:
            daily_sleep = pd.Series(0.0, index=stage_daily.index)
        daily_sleep.name = "value"
        daily_in_bed = pd.Series(in_bed_rows, name="in_bed_hours").sort_index()
        daily_in_bed.index.name = "date"
        return daily_sleep.sort_index(), stage_daily.sort_index(), daily_in_bed

    def workouts(
        self,
        source_priority: Sequence[str] | None = None,
        max_heart_rate: float | None = None,
    ) -> pd.DataFrame:
        heart_rate = self._reconcile_discrete(
            self.quantity_records(HEART_RATE),
            source_priority,
        )
        rows: list[dict[str, Any]] = []
        for workout in self.root.findall(".//Workout"):
            if not self._source_allowed(workout.get("sourceName")):
                continue
            try:
                start = parse_apple_datetime(workout.get("startDate") or "")
                end = parse_apple_datetime(workout.get("endDate") or "")
                if end.timestamp() < start.timestamp():
                    raise ValueError("endDate is before startDate")
                duration_value = workout.get("duration")
                if duration_value:
                    duration_minutes = convert_unit(
                        float(duration_value),
                        workout.get("durationUnit") or "min",
                        "min",
                    )
                else:
                    duration_minutes = max(
                        0.0,
                        (end.timestamp() - start.timestamp()) / 60,
                    )

                calories = 0.0
                distance_km = 0.0
                statistic_average_hr: float | None = None
                for statistic in workout.findall(".//WorkoutStatistics"):
                    statistic_type = statistic.get("type") or ""
                    unit = statistic.get("unit") or ""
                    sum_value = statistic.get("sum")
                    average_value = statistic.get("average")
                    if sum_value and "ActiveEnergyBurned" in statistic_type:
                        calories += convert_unit(float(sum_value), unit, "kcal")
                    elif sum_value and "Distance" in statistic_type:
                        distance_km += convert_unit(float(sum_value), unit, "km")
                    if average_value and "HeartRate" in statistic_type:
                        statistic_average_hr = convert_unit(
                            float(average_value),
                            unit,
                            "count/min",
                        )

                if calories == 0 and workout.get("totalEnergyBurned"):
                    calories = convert_unit(
                        float(workout.get("totalEnergyBurned")),
                        workout.get("totalEnergyBurnedUnit") or "kcal",
                        "kcal",
                    )
                if distance_km == 0 and workout.get("totalDistance"):
                    distance_km = convert_unit(
                        float(workout.get("totalDistance")),
                        workout.get("totalDistanceUnit") or "km",
                        "km",
                    )

                workout_hr = heart_rate[
                    (heart_rate["start_utc"] >= start.timestamp())
                    & (heart_rate["start_utc"] <= end.timestamp())
                ]
                if not workout_hr.empty:
                    average_hr = float(workout_hr["value"].mean())
                    minimum_hr = float(workout_hr["value"].min())
                    maximum_hr = float(workout_hr["value"].max())
                    measurements = int(len(workout_hr))
                else:
                    average_hr = statistic_average_hr
                    minimum_hr = math.nan
                    maximum_hr = math.nan
                    measurements = 0

                intensity_percent = (
                    average_hr / max_heart_rate * 100
                    if average_hr is not None and max_heart_rate
                    else math.nan
                )
                if math.isnan(intensity_percent):
                    intensity_label = ""
                elif intensity_percent < 60:
                    intensity_label = "Very Light"
                elif intensity_percent < 70:
                    intensity_label = "Light"
                elif intensity_percent < 80:
                    intensity_label = "Moderate"
                elif intensity_percent < 90:
                    intensity_label = "Hard"
                else:
                    intensity_label = "Maximum"

                rows.append(
                    {
                        "date": start.date(),
                        "start_time": start.isoformat(),
                        "end_time": end.isoformat(),
                        "activity_type": (
                            workout.get("workoutActivityType") or "Unknown"
                        ).replace("HKWorkoutActivityType", ""),
                        "duration_minutes": round(duration_minutes, 2),
                        "duration_hours": round(duration_minutes / 60, 4),
                        "calories": round(calories, 3),
                        "distance_km": round(distance_km, 6),
                        "source": workout.get("sourceName") or "Unknown",
                        "avg_heart_rate": (
                            round(average_hr, 2)
                            if average_hr is not None
                            else math.nan
                        ),
                        "min_heart_rate": (
                            round(minimum_hr, 2)
                            if not math.isnan(minimum_hr)
                            else math.nan
                        ),
                        "max_heart_rate": (
                            round(maximum_hr, 2)
                            if not math.isnan(maximum_hr)
                            else math.nan
                        ),
                        "hr_measurements": measurements,
                        "intensity_percent_max": (
                            round(intensity_percent, 2)
                            if not math.isnan(intensity_percent)
                            else math.nan
                        ),
                        "intensity": intensity_label,
                    }
                )
            except (TypeError, ValueError) as error:
                self.issues.append(f"Workout: skipped record ({error})")

        if not rows:
            return pd.DataFrame(
                columns=[
                    "date",
                    "start_time",
                    "end_time",
                    "activity_type",
                    "duration_minutes",
                    "duration_hours",
                    "calories",
                    "distance_km",
                    "source",
                    "avg_heart_rate",
                    "min_heart_rate",
                    "max_heart_rate",
                    "hr_measurements",
                    "intensity_percent_max",
                    "intensity",
                ]
            )
        return pd.DataFrame(rows).sort_values("start_time")

    def available_sources(self, record_type: str) -> list[str]:
        """All sources present for a record type, ignoring any active filter."""
        sources = {
            record.get("sourceName") or "Unknown"
            for record in self.root.findall(".//Record")
            if record.get("type") == record_type
        }
        return sorted(sources)

    def all_sources(self) -> list[str]:
        """Every distinct source across records and workouts, ignoring filters."""
        sources = {
            element.get("sourceName") or "Unknown"
            for element in self.root.iter()
            if element.tag in {"Record", "Workout"}
        }
        return sorted(sources)

    def write_metric_exports(
        self,
        output_dir: str | Path,
        source_priorities: dict[str, list[str]] | None = None,
        source_mode: str = "reconcile",
        max_heart_rate: float | None = None,
        unit_system: str = "metric",
    ) -> dict[str, Path]:
        output = Path(output_dir).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        priorities = source_priorities or {}
        written: dict[str, Path] = {}
        _, distance_factor = display_unit("distance", unit_system)
        _, weight_factor = display_unit("weight", unit_system)

        for record_type, (filename, aggregation) in METRIC_EXPORTS.items():
            daily = self.daily_quantity(
                record_type,
                aggregation,
                priorities.get(record_type),
                source_mode,
            )
            if record_type == DISTANCE_WALKING_RUNNING:
                daily = daily * distance_factor
            elif record_type == BODY_MASS:
                daily = daily * weight_factor
            path = output / filename
            daily.to_csv(path, header=True)
            written[filename] = path
            if record_type == STEP_COUNT:
                compatibility_path = output / "stepsdata.csv"
                daily.to_csv(compatibility_path, header=True)
                written["stepsdata.csv"] = compatibility_path

        sleep = self.sleep_records().copy()
        sleep_path = output / "sleep_data.csv"
        if sleep.empty:
            pd.DataFrame(
                columns=[
                    "date",
                    "start_time",
                    "end_time",
                    "duration_minutes",
                    "duration_hours",
                    "sleep_type",
                    "sleep_value",
                    "source",
                ]
            ).to_csv(sleep_path, index=False)
        else:
            sleep_export = pd.DataFrame(
                {
                    "date": sleep["night_date"],
                    "start_time": sleep["start"].map(lambda value: value.isoformat()),
                    "end_time": sleep["end"].map(lambda value: value.isoformat()),
                    "duration_minutes": sleep["duration_hours"] * 60,
                    "duration_hours": sleep["duration_hours"],
                    "sleep_type": sleep["sleep_type"],
                    "sleep_value": sleep["sleep_value"],
                    "source": sleep["source"],
                }
            )
            sleep_export.to_csv(sleep_path, index=False)
        written["sleep_data.csv"] = sleep_path

        daily_sleep, stages, in_bed = self.sleep_summary(
            priorities.get(SLEEP_ANALYSIS)
        )
        sleep_daily = daily_sleep.to_frame()
        sleep_daily["in_bed_hours"] = in_bed
        sleep_daily = sleep_daily.join(stages, how="outer").fillna(0.0)
        sleep_daily_path = output / "sleep_daily.csv"
        sleep_daily.to_csv(sleep_daily_path)
        written["sleep_daily.csv"] = sleep_daily_path

        workouts = self.workouts(
            priorities.get(HEART_RATE),
            max_heart_rate=max_heart_rate,
        )
        if distance_factor != 1.0 and "distance_km" in workouts:
            workouts = workouts.rename(columns={"distance_km": "distance_mi"})
            workouts["distance_mi"] = (workouts["distance_mi"] * distance_factor).round(6)
        workout_path = output / "workout_data.csv"
        workouts.to_csv(workout_path, index=False)
        written["workout_data.csv"] = workout_path
        return written
