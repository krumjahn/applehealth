from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd

MAC_APP_BASE_URL = os.environ.get("HEALTH_ANALYZER_API_BASE_URL", "http://127.0.0.1:8765")
MAC_APP_TOKEN_HEADER = "X-Health-Analyzer-Token"


def discover_repo_root(explicit_repo: Optional[str] = None) -> Path:
    candidates = []
    if explicit_repo:
        candidates.append(Path(explicit_repo).expanduser())
    env_repo = os.environ.get("APPLEHEALTH_REPO")
    if env_repo:
        candidates.append(Path(env_repo).expanduser())
    cwd = Path.cwd()
    candidates.extend([cwd, cwd / "applehealth", Path(__file__).resolve().parents[3]])
    for candidate in candidates:
        root = candidate.resolve()
        if (root / "src" / "applehealth.py").exists():
            return root
    raise FileNotFoundError("Could not find the applehealth repo. Set APPLEHEALTH_REPO or pass --repo.")


def load_analyzer(repo_root: Path):
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    import applehealth  # type: ignore

    return applehealth


def _fetch_json(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_mac_app_openclaw_status() -> Dict[str, Any]:
    return _fetch_json(f"{MAC_APP_BASE_URL}/openclaw/status")


def try_fetch_mac_app_openclaw_status() -> Optional[Dict[str, Any]]:
    try:
        return fetch_mac_app_openclaw_status()
    except Exception:
        return None


def fetch_mac_app_status() -> Dict[str, Any]:
    return _fetch_json(f"{MAC_APP_BASE_URL}/status")


def read_mac_app_token() -> str:
    status = fetch_mac_app_status()
    token_path = ((status.get("data") or {}).get("token_path")) or ""
    if not token_path:
        raise ValueError("Mac app status did not include a token path.")
    token = Path(token_path).expanduser().read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError("Mac app token file is empty.")
    return token


def fetch_mac_app_private_json(path: str) -> Dict[str, Any]:
    token = read_mac_app_token()
    headers = {MAC_APP_TOKEN_HEADER: token}
    return _fetch_json(f"{MAC_APP_BASE_URL}{path}", headers=headers)


def fetch_mac_app_daily_brief(target_date: Optional[str] = None) -> Dict[str, Any]:
    path = "/openclaw/daily-brief"
    if target_date:
        path += f"?date={urllib.parse.quote(target_date)}"
    payload = _fetch_json(f"{MAC_APP_BASE_URL}{path}")
    data = payload.get("data")
    if not data:
        raise ValueError("Mac app daily brief returned no data.")
    return data


def fetch_mac_app_recent_trends(days: int = 7) -> Dict[str, Any]:
    brief = fetch_mac_app_daily_brief()
    target_date = pd.to_datetime(brief["date"]).date()
    start_date = target_date - pd.Timedelta(days=days - 1)
    steps_payload = fetch_mac_app_private_json(f"/steps/daily?start={start_date.isoformat()}&end={target_date.isoformat()}")
    sleep_payload = fetch_mac_app_private_json(f"/sleep/summary?start={start_date.isoformat()}&end={target_date.isoformat()}")
    step_days = ((steps_payload.get("data") or {}).get("days")) or []
    sleep_days = ((sleep_payload.get("data") or {}).get("days")) or []
    return {
        "days": days,
        "steps": {
            "average": _average([day.get("value") for day in step_days]),
            "best": _max_value([day.get("value") for day in step_days]),
            "latest": _safe_float(step_days[-1].get("value")) if step_days else None,
            "series": [{"date": day.get("date"), "value": _safe_float(day.get("value"))} for day in step_days],
        },
        "sleep": {
            "average": _average([day.get("hours") for day in sleep_days]),
            "best": _max_value([day.get("hours") for day in sleep_days]),
            "latest": _safe_float(sleep_days[-1].get("hours")) if sleep_days else None,
            "series": [{"date": day.get("date"), "value": _safe_float(day.get("hours"))} for day in sleep_days],
        },
    }


def fetch_mac_app_weekly_summary(days: int = 7) -> Dict[str, Any]:
    brief = fetch_mac_app_daily_brief()
    target_date = pd.to_datetime(brief["date"]).date()
    start_date = target_date - pd.Timedelta(days=days - 1)
    trends = fetch_mac_app_recent_trends(days=days)
    try:
        workouts_payload = fetch_mac_app_private_json(f"/workouts/summary?start={start_date.isoformat()}&end={target_date.isoformat()}")
    except Exception:
        workouts_payload = {"data": {}}
    heart_rate_payload = fetch_mac_app_private_json(f"/heart-rate/trends?start={start_date.isoformat()}&end={target_date.isoformat()}")
    workout_data = workouts_payload.get("data") or {}
    hr_data = heart_rate_payload.get("data") or {}
    average_heart_rate = hr_data.get("average_heart_rate") or []
    total_minutes = workout_data.get("total_minutes")
    total_count = workout_data.get("total_workouts")
    return {
        "days": days,
        "steps_average": trends["steps"]["average"],
        "sleep_average": trends["sleep"]["average"],
        "workout_minutes_total": _safe_float(total_minutes) or 0.0,
        "workout_count_total": int(total_count) if total_count is not None else 0,
        "heart_rate_average": _average([day.get("value") for day in average_heart_rate]),
        "steps_series": trends["steps"]["series"],
        "sleep_series": trends["sleep"]["series"],
    }


def configure_analyzer(analyzer, export_path: Optional[str], out_dir: Optional[str]) -> Dict[str, str]:
    repo_root = Path(analyzer.__file__).resolve().parents[1]
    resolved_out = Path(out_dir).expanduser().resolve() if out_dir else Path(analyzer.get_output_dir()).expanduser().resolve()
    resolved_out.mkdir(parents=True, exist_ok=True)
    analyzer._output_dir = str(resolved_out)
    analyzer._set_saved_pref("output_dir", str(resolved_out))
    resolved_export = None
    if export_path:
        resolved_export = Path(export_path).expanduser().resolve()
        analyzer._export_xml_path = str(resolved_export)
        analyzer._set_saved_pref("export_xml", str(resolved_export))
    return {
        "repo_root": str(repo_root),
        "out_dir": str(resolved_out),
        "export_path": str(resolved_export) if resolved_export else analyzer._get_saved_pref("export_xml", ""),
    }


@contextmanager
def headless_plots(analyzer):
    original_show = analyzer.plt.show
    analyzer.plt.show = lambda *args, **kwargs: None
    try:
        yield
    finally:
        analyzer.plt.show = original_show


def ensure_required_csvs(analyzer, required_files: Iterable[str]) -> Dict[str, str]:
    generators = {
        "steps_data.csv": analyzer.analyze_steps,
        "heart_rate_data.csv": analyzer.analyze_heart_rate,
        "sleep_data.csv": analyzer.analyze_sleep,
        "workout_data.csv": analyzer.analyze_workouts,
        "weight_data.csv": analyzer.analyze_weight,
        "distance_data.csv": analyzer.analyze_distance,
    }
    resolved_paths: Dict[str, str] = {}
    with headless_plots(analyzer):
        for filename in required_files:
            path = analyzer.get_output_path(filename)
            if not os.path.exists(path):
                generator = generators.get(filename)
                if generator is None:
                    raise KeyError(f"No generator for required file: {filename}")
                generator()
            resolved_paths[filename] = path
    return resolved_paths


def _read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


def load_steps(path: str) -> pd.Series:
    df = _read_csv(path)
    if df.empty:
        return pd.Series(dtype=float)
    first_col = df.columns[0]
    value_col = "value" if "value" in df.columns else df.columns[-1]
    series = pd.Series(df[value_col].astype(float).values, index=pd.to_datetime(df[first_col]).dt.date)
    series.name = "steps"
    return series.sort_index()


def load_heart_rate(path: str) -> pd.Series:
    df = _read_csv(path)
    if df.empty:
        return pd.Series(dtype=float)
    first_col = df.columns[0]
    value_col = "value" if "value" in df.columns else df.columns[-1]
    series = pd.Series(df[value_col].astype(float).values, index=pd.to_datetime(df[first_col]).dt.date)
    series.name = "heart_rate"
    return series.sort_index()


def load_sleep(path: str) -> pd.Series:
    df = _read_csv(path)
    if df.empty or "date" not in df.columns or "duration_hours" not in df.columns:
        return pd.Series(dtype=float)
    filtered = df[~df["sleep_type"].isin(["Awake", "In Bed"])] if "sleep_type" in df.columns else df
    if filtered.empty:
        return pd.Series(dtype=float)
    grouped = filtered.groupby(pd.to_datetime(filtered["date"]).dt.date)["duration_hours"].sum().astype(float)
    grouped.name = "sleep"
    return grouped.sort_index()


def load_workouts(path: str) -> pd.DataFrame:
    df = _read_csv(path)
    if df.empty or "date" not in df.columns:
        return pd.DataFrame(columns=["count", "total_minutes"])
    if "duration_minutes" not in df.columns and "duration_hours" in df.columns:
        df["duration_minutes"] = df["duration_hours"].astype(float) * 60.0
    grouped = df.groupby(pd.to_datetime(df["date"]).dt.date).agg(count=("date", "size"), total_minutes=("duration_minutes", "sum"))
    return grouped.sort_index()


def series_value(series: pd.Series, date_value) -> Optional[float]:
    if series.empty or date_value not in series.index:
        return None
    return float(series.loc[date_value])


def baseline_before(series: pd.Series, date_value, days: int = 7) -> Optional[float]:
    if series.empty:
        return None
    history = series[series.index < date_value].tail(days)
    if history.empty:
        return None
    return float(history.mean())


def latest_available_date(*objects: Any):
    latest = None
    for obj in objects:
        if obj is None:
            continue
        index = getattr(obj, "index", None)
        if index is None or len(index) == 0:
            continue
        candidate = max(index)
        latest = candidate if latest is None or candidate > latest else latest
    return latest


def compute_daily_brief(steps: pd.Series, sleep: pd.Series, heart_rate: pd.Series, workouts: pd.DataFrame, date_value=None) -> Dict[str, Any]:
    target_date = date_value or latest_available_date(steps, sleep, heart_rate, workouts)
    if target_date is None:
        raise ValueError("No analyzed data found. Run the export analysis first.")
    steps_value = series_value(steps, target_date)
    steps_baseline = baseline_before(steps, target_date)
    sleep_value = series_value(sleep, target_date)
    sleep_baseline = baseline_before(sleep, target_date)
    hr_value = series_value(heart_rate, target_date)
    hr_baseline = baseline_before(heart_rate, target_date)
    workout_count = None
    workout_minutes = None
    if not workouts.empty and target_date in workouts.index:
        workout_count = int(workouts.loc[target_date, "count"])
        workout_minutes = float(workouts.loc[target_date, "total_minutes"])
    signals = []
    if steps_value is not None and steps_baseline is not None and steps_value < steps_baseline * 0.7:
        signals.append("activity_below_baseline")
    if sleep_value is not None and sleep_baseline is not None and sleep_value < sleep_baseline * 0.85:
        signals.append("sleep_below_baseline")
    if workout_count == 0 and (steps_value or 0) < 5000:
        signals.append("low_training_load")
    return {
        "date": str(target_date),
        "context_summary": f"Daily brief for {target_date}, steps {int(steps_value) if steps_value is not None else 'n/a'}",
        "signals": signals,
        "steps": {"value": int(steps_value) if steps_value is not None else None, "baseline_7d": steps_baseline, "delta_vs_baseline": (steps_value - steps_baseline) if steps_value is not None and steps_baseline is not None else None},
        "sleep": {"hours": round(sleep_value, 2) if sleep_value is not None else None, "baseline_7d": sleep_baseline, "delta_vs_baseline": (sleep_value - sleep_baseline) if sleep_value is not None and sleep_baseline is not None else None},
        "heart_rate": {"average": round(hr_value, 2) if hr_value is not None else None, "baseline_7d": hr_baseline, "delta_vs_baseline": (hr_value - hr_baseline) if hr_value is not None and hr_baseline is not None else None},
        "workouts": {"count": workout_count if workout_count is not None else 0, "total_minutes": round(workout_minutes, 1) if workout_minutes is not None else 0},
    }


def compute_recent_trends(steps: pd.Series, sleep: pd.Series, days: int = 7) -> Dict[str, Any]:
    steps_recent = steps.tail(days)
    sleep_recent = sleep.tail(days)
    return {
        "days": days,
        "steps": {
            "average": float(steps_recent.mean()) if not steps_recent.empty else None,
            "best": float(steps_recent.max()) if not steps_recent.empty else None,
            "latest": float(steps_recent.iloc[-1]) if not steps_recent.empty else None,
            "series": [{"date": str(idx), "value": float(value)} for idx, value in steps_recent.items()],
        },
        "sleep": {
            "average": float(sleep_recent.mean()) if not sleep_recent.empty else None,
            "best": float(sleep_recent.max()) if not sleep_recent.empty else None,
            "latest": float(sleep_recent.iloc[-1]) if not sleep_recent.empty else None,
            "series": [{"date": str(idx), "value": float(value)} for idx, value in sleep_recent.items()],
        },
    }


def compute_weekly_summary(steps: pd.Series, sleep: pd.Series, workouts: pd.DataFrame, heart_rate: pd.Series, days: int = 7) -> Dict[str, Any]:
    trends = compute_recent_trends(steps, sleep, days=days)
    workouts_recent = workouts.tail(days) if not workouts.empty else pd.DataFrame(columns=["count", "total_minutes"])
    hr_recent = heart_rate.tail(days)
    return {
        "days": days,
        "steps_average": trends["steps"]["average"],
        "sleep_average": trends["sleep"]["average"],
        "workout_minutes_total": float(workouts_recent["total_minutes"].sum()) if not workouts_recent.empty else 0.0,
        "workout_count_total": int(workouts_recent["count"].sum()) if not workouts_recent.empty else 0,
        "heart_rate_average": float(hr_recent.mean()) if not hr_recent.empty else None,
        "steps_series": trends["steps"]["series"],
        "sleep_series": trends["sleep"]["series"],
    }


def choose_source(requested_source: str) -> str:
    if requested_source == "auto":
        return "mac-app" if try_fetch_mac_app_openclaw_status() else "export"
    return requested_source


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _average(values: Iterable[Any]) -> Optional[float]:
    cleaned = [_safe_float(value) for value in values]
    cleaned = [value for value in cleaned if value is not None]
    if not cleaned:
        return None
    return float(sum(cleaned) / len(cleaned))


def _max_value(values: Iterable[Any]) -> Optional[float]:
    cleaned = [_safe_float(value) for value in values]
    cleaned = [value for value in cleaned if value is not None]
    if not cleaned:
        return None
    return float(max(cleaned))


def to_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
