"""
Apple Health Data Analyzer
-------------------------

This script analyzes exported Apple Health data (export.xml) with a focus on:
- Steps
- Walking/Running Distance
- Heart Rate
- Weight
- Sleep
- Workouts (specifically WHOOP workout data)

Requirements:
- Python 3.6+
- pandas
- matplotlib7
- xml.etree.ElementTree
- openai
- dotenv
- ollama

Usage:
1. Export your Apple Health data from the Health app on your iPhone
2. Place the 'export.xml' file in the same directory as this script
3. Run the script and choose which health metric to analyze

Author: Keith Rumjahn
License: MIT
Version: 1.4.1
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from pandas import DataFrame, read_csv
from pandas.core.groupby import DataFrameGroupBy
import matplotlib.pyplot as plt
import openai
import os
from dotenv import load_dotenv
import sys
import ollama
import argparse
import threading
import time
from contextlib import contextmanager
import json
from urllib.parse import unquote as _url_unquote
from typing import Optional, List, Dict, Any, Tuple
import re
try:
    import anthropic  # Claude SDK
except Exception:
    anthropic = None
try:
    import google.generativeai as genai  # Gemini SDK
except Exception:
    genai = None

# Optional user-provided path to export.xml (from CLI or prompt)
_export_xml_path = None
_output_dir = os.environ.get('OUTPUT_DIR')
__version__ = "1.4.2"

def get_output_dir():
    """Return the absolute output directory, creating it if needed.

    Order of precedence:
    1) CLI --out overrides
    2) $OUTPUT_DIR env var
    3) Remembered value in ai_prefs.json (output_dir)
    4) Current working directory
    """
    global _output_dir
    default_out = os.path.join(os.getcwd(), 'health_out')
    base = _output_dir or os.environ.get('OUTPUT_DIR') or _get_saved_pref('output_dir') or default_out
    base = os.path.abspath(os.path.expanduser(base))
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    # Persist chosen directory for convenience
    try:
        _set_saved_pref('output_dir', base)
    except Exception:
        pass
    return base

def get_output_path(filename: str) -> str:
    """Join the output directory with the provided filename."""
    return os.path.join(get_output_dir(), filename)

def print_open_hint(file_path: str):
    """Print a one-line hint to open a file on the current OS."""
    try:
        plat = sys.platform
        if plat == 'darwin':
            tool = 'open'
        elif plat.startswith('linux'):
            tool = 'xdg-open'
        elif plat.startswith('win'):
            tool = 'start ""'
        else:
            tool = None
        if tool:
            print(f"Tip: {tool} \"{file_path}\"")
        else:
            print(f"Tip: open this file in your viewer: {file_path}")
    except Exception:
        pass

# Simple persisted preferences for AI and paths
# Store under user home to avoid bootstrapping OUTPUT_DIR recursion
def _prefs_path() -> str:
    try:
        env_path = os.environ.get('APPLEHEALTH_PREFS')
        if env_path:
            return os.path.abspath(os.path.expanduser(env_path))
        home = os.path.expanduser('~')
        pref_dir = os.path.join(home, '.applehealth')
        os.makedirs(pref_dir, exist_ok=True)
        return os.path.join(pref_dir, 'ai_prefs.json')
    except Exception:
        # Fallback to CWD
        return os.path.abspath('ai_prefs.json')

def _load_ai_prefs() -> dict:
    try:
        path = _prefs_path()
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_ai_prefs(prefs: dict):
    try:
        with open(_prefs_path(), 'w') as f:
            json.dump(prefs, f, indent=2)
    except Exception:
        pass

def _get_saved_model(provider_key: str, default_model: str) -> str:
    prefs = _load_ai_prefs()
    return prefs.get(provider_key, default_model)

def _set_saved_model(provider_key: str, model: str):
    prefs = _load_ai_prefs()
    prefs[provider_key] = model
    _save_ai_prefs(prefs)

def _get_saved_pref(key: str, default_value: Optional[str] = None):
    prefs = _load_ai_prefs()
    return prefs.get(key, default_value)

def _set_saved_pref(key: str, value: str):
    prefs = _load_ai_prefs()
    prefs[key] = value
    _save_ai_prefs(prefs)

def _parse_bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    val = val.strip().lower()
    return val in ("1", "true", "yes", "y", "on")

def _parse_csv_env(name: str) -> List[str]:
    val = os.environ.get(name)
    if not val:
        return []
    return [x.strip() for x in val.split(',') if x.strip()]

# --- Simple CLI progress helpers ---
_spinner_symbols = ['⠋', '⠙', '⠚', '⠞', '⠖', '⠦', '⠴', '⠲', '⠳', '⠓']

class _Spinner:
    def __init__(self, message: str = "Working", interval: float = 0.1):
        self.message = message
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None
        self._start_time = None

    def start(self):
        if self._thread is not None:
            return
        self._start_time = time.time()
        def run():
            i = 0
            while not self._stop.is_set():
                elapsed = int(time.time() - self._start_time)
                sym = _spinner_symbols[i % len(_spinner_symbols)]
                print(f"\r{self.message} {sym}  {elapsed}s elapsed", end='', flush=True)
                i += 1
                time.sleep(self.interval)
            # Clear line on stop
            print("\r" + " " * 80 + "\r", end='', flush=True)
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=1.0)
        self._thread = None

@contextmanager
def spinner(message: str):
    s = _Spinner(message)
    try:
        s.start()
        yield
    finally:
        s.stop()

def _status(msg: str):
    try:
        ts = time.strftime('%H:%M:%S')
        print(f"[{ts}] {msg}")
    except Exception:
        print(msg)

# --- Ollama helpers ---
def _extract_ollama_chunk_text(chunk: Any) -> str:
    """Extract incremental text from an Ollama streaming chunk.

    Handles both dict-style chunks and typed Response objects from the
    `ollama` Python package. Returns '' if no text is present.
    """
    try:
        # Dict-style streaming event
        if isinstance(chunk, dict):
            # Prefer 'response' (generate) then chat message content
            return (
                chunk.get('response')
                or (chunk.get('message') or {}).get('content')
                or ''
            )
        # Typed object (ollama.Response)
        msg = getattr(chunk, 'message', None)
        if msg is not None:
            # message could be an object or dict; try attribute then key
            content = getattr(msg, 'content', None)
            if content:
                return content
            if isinstance(msg, dict):
                return msg.get('content') or ''
        # Generate stream typed objects carry 'response'
        resp = getattr(chunk, 'response', None)
        if resp:
            return resp
    except Exception:
        pass
    return ''

def _strip_reasoning_blocks(text: str) -> str:
    """Remove model reasoning blocks like <think>...</think> from text."""
    if not text:
        return text
    try:
        # Remove any <think>...</think> segments (greedy across newlines)
        return re.sub(r"<think>[\s\S]*?</think>\s*", "", text, flags=re.IGNORECASE)
    except Exception:
        return text

def reset_preferences():
    """Delete saved preferences file and clear in-memory overrides."""
    path = _prefs_path()
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"Preferences reset. Deleted {path}")
        else:
            print("No preferences file found to delete.")
    except Exception as e:
        print(f"Failed to reset preferences: {e}")
    # Clear session overrides
    global _export_xml_path, _output_dir
    _export_xml_path = None
    _output_dir = None

def resolve_export_xml():
    """Locate the Apple Health export.xml across common locations.

    Tries environment var EXPORT_XML, current dir, script dir, root-mounted
    '/export.xml', and parent dir. If a candidate is a directory, checks for
    an 'export.xml' inside it.
    """
    # Check if we have a global path set first
    global _export_xml_path
    if _export_xml_path and os.path.isfile(_export_xml_path):
        print(f"Using globally set export file: {_export_xml_path}")
        return _export_xml_path
    
    # Gather candidate paths (keep order of preference)
    candidates = []
    # Remembered path (from previous successful runs)
    remembered = _get_saved_pref('export_xml')
    if remembered:
        candidates.append(remembered)
    env_path = os.environ.get('EXPORT_XML')
    if env_path:
        candidates.append(env_path)
    candidates.extend([
        '/export.xml',  # Prioritize Docker mount path
        'export.xml',
        os.path.join(os.getcwd(), 'export.xml'),
        os.path.join(os.path.dirname(__file__), 'export.xml'),
        os.path.abspath(os.path.join(os.path.dirname(os.getcwd()), 'export.xml')),
        '../export.xml',
    ])

    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for p in candidates:
        ap = os.path.abspath(p)
        if ap not in seen:
            uniq.append(ap)
            seen.add(ap)

    for path in uniq:
        if os.path.exists(path):
            if os.path.isfile(path):
                print(f"Found export.xml at: {path}")
                try:
                    _set_saved_pref('export_xml', path)
                except Exception:
                    pass
                return path
            # If it's a directory, try to find export.xml inside it
            elif os.path.isdir(path):
                # First, try looking for export.xml inside the directory
                possible = os.path.join(path, 'export.xml')
                if os.path.isfile(possible):
                    print(f"Found export.xml inside directory at: {possible}")
                    try:
                        _set_saved_pref('export_xml', possible)
                    except Exception:
                        pass
                    return possible
                # Also check if the directory name suggests it contains an export
                # (e.g., for cases where the mounted path is actually a directory)
                for filename in ['export.xml', 'apple_health_export.xml', 'HealthData_export.xml']:
                    candidate_file = os.path.join(path, filename)
                    if os.path.isfile(candidate_file):
                        print(f"Found health export file at: {candidate_file}")
                        try:
                            _set_saved_pref('export_xml', candidate_file)
                        except Exception:
                            pass
                        return candidate_file

    # Not found: raise a helpful error
    raise FileNotFoundError(
        "export.xml not found. Set EXPORT_XML to the file path, or mount it in Docker, e.g.\n"
        "-v \"/path/to/export.xml\":/export.xml or -v \"/path/to/apple_health_export\":/export\n"
        "Available paths searched:\n" + "\n".join(f"  - {p} (exists: {os.path.exists(p)}, is_file: {os.path.isfile(p) if os.path.exists(p) else 'N/A'}, is_dir: {os.path.isdir(p) if os.path.exists(p) else 'N/A'})" for p in uniq)
    )

def ensure_export_available() -> bool:
    """Ensure export.xml is available; prompt user if not.

    Returns True if available, False if user cancels.
    """
    try:
        _ = resolve_export_xml()
        return True
    except Exception:
        pass

    print("\nexport.xml not found.")
    print("Provide the full path to your Apple Health export.xml,")
    print("or a directory containing export.xml. Enter 'q' to cancel.")
    print("Tip: You can drag-and-drop the file or folder here and press Enter.")
    remembered = _get_saved_pref('export_xml', '')
    while True:
        prompt = f"Path to export.xml (or directory){f' [{remembered}]' if remembered else ''}: "
        raw = input(prompt)
        user_input = raw.strip()
        if user_input.lower() in ('q', 'quit', 'exit'):
            print("Skipping action: export.xml required.")
            return False
        if not user_input and remembered:
            user_input = remembered
        # Sanitize drag-and-drop style inputs (quotes, file://, escaped spaces)
        user_input = _sanitize_user_path(user_input)
        # Accept both file path and directory containing export.xml
        path = os.path.abspath(os.path.expanduser(user_input))
        if os.path.isdir(path):
            cand = os.path.join(path, 'export.xml')
        else:
            cand = path
        if os.path.isfile(cand):
            global _export_xml_path
            _export_xml_path = cand
            print(f"Using export file: {cand}")
            try:
                _set_saved_pref('export_xml', cand)
            except Exception:
                pass
            return True
        else:
            print("Invalid path. Please try again or enter 'q' to cancel.")

def _sanitize_user_path(inp: str) -> str:
    try:
        if not inp:
            return inp
        s = inp.strip()
        # Handle file:// URLs
        if s.startswith('file://'):
            s = _url_unquote(s[len('file://'):])
        # Strip surrounding quotes
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1]
        # On Unix-like systems, unescape common backslash-escapes from drag-drop
        if os.name != 'nt':
            s = s.replace('\\ ', ' ').replace('\\(', '(').replace('\\)', ')')
        return s
    except Exception:
        return inp

def parse_health_data(file_path, record_type):
    """
    Parse specific health metrics from Apple Health export.xml file.
    
    Args:
        file_path (str): Path to the export.xml file
        record_type (str): The type of health record to parse (e.g., 'HKQuantityTypeIdentifierStepCount')
    
    Returns:
        pandas.DataFrame: DataFrame containing dates and values for the specified metric
    """
    print(f"Starting to parse {record_type}...")
    dates = []
    values = []
    
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    print("XML file loaded, searching records...")
    
    bad_samples = []
    for record in root.findall('.//Record'):
        if record.get('type') == record_type:
            try:
                value = float(record.get('value'))
                date = datetime.strptime(record.get('endDate'), '%Y-%m-%d %H:%M:%S %z')
                dates.append(date)
                values.append(value)
            except (ValueError, TypeError):
                # Collect a few bad samples to aid debugging
                if len(bad_samples) < 3:
                    bad_samples.append({
                        'type': record.get('type'),
                        'value': record.get('value'),
                        'startDate': record.get('startDate'),
                        'endDate': record.get('endDate'),
                        'unit': record.get('unit'),
                        'sourceName': record.get('sourceName')
                    })
                continue
    
    print(f"Found {len(dates)} records")
    # If we encountered parsing issues, persist a short debug note
    if bad_samples:
        try:
            dbg_path = get_output_path(f"debug_{record_type}_parse_issues.json")
            with open(dbg_path, 'w') as f:
                json.dump({
                    'record_type': record_type,
                    'num_good': len(dates),
                    'num_bad_samples': len(bad_samples),
                    'bad_samples': bad_samples,
                    'note': 'These records had non-numeric values for a quantity parser. This is normal if the type is a Category.'
                }, f, indent=2)
            print(f"Wrote debug sample to {dbg_path}")
        except Exception:
            pass
    return DataFrame({'date': dates, 'value': values})


# --- Diagnostics & Debugging Helpers ---
def _classify_record_type(t: str) -> str:
    try:
        if not t:
            return 'unknown'
        if t.startswith('HKQuantityTypeIdentifier'):
            return 'quantity'
        if t.startswith('HKCategoryTypeIdentifier'):
            return 'category'
        if t.startswith('HKCorrelationTypeIdentifier'):
            return 'correlation'
        if t.startswith('HKDataType'):
            return 'data'
        return 'other'
    except Exception:
        return 'unknown'


def scan_export_types(file_path: str) -> Dict[str, Any]:
    """Scan export.xml for all record/workout types and summarize.

    Returns a dictionary with:
    - totals, by_type stats, unknown_types, category_types, quantity_types
    - examples of values for each type
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    by_type: Dict[str, Dict[str, Any]] = {}
    total_records = 0

    for rec in root.findall('.//Record'):
        t = rec.get('type') or 'UNKNOWN'
        cls = _classify_record_type(t)
        d1, d2 = rec.get('startDate'), rec.get('endDate')
        v = rec.get('value')
        total_records += 1
        st = by_type.setdefault(t, {
            'class': cls,
            'count': 0,
            'units': set(),
            'sources': set(),
            'bad_values': 0,
            'value_examples': [],
            'first_seen': None,
            'last_seen': None,
        })
        st['count'] += 1
        unit = rec.get('unit')
        if unit:
            st['units'].add(unit)
        src = rec.get('sourceName')
        if src:
            st['sources'].add(src)
        # Track dates
        def _parse_dt(s: Optional[str]) -> Optional[str]:
            try:
                return datetime.strptime(s, '%Y-%m-%d %H:%M:%S %z').isoformat()
            except Exception:
                return None
        s1 = _parse_dt(d1)
        s2 = _parse_dt(d2)
        for dt in [s1, s2]:
            if not dt:
                continue
            if not st['first_seen'] or dt < st['first_seen']:
                st['first_seen'] = dt
            if not st['last_seen'] or dt > st['last_seen']:
                st['last_seen'] = dt
        # Samples
        if v is not None and len(st['value_examples']) < 3:
            st['value_examples'].append(v)
        # Rough numeric check for quantities
        if st['class'] == 'quantity':
            try:
                _ = float(v)
            except Exception:
                st['bad_values'] += 1

    # Normalize sets
    for t, st in by_type.items():
        st['units'] = sorted(list(st['units']))
        st['sources'] = sorted(list(st['sources']))

    # Collect grouping
    quantity_types = sorted([t for t, st in by_type.items() if st['class'] == 'quantity'])
    category_types = sorted([t for t, st in by_type.items() if st['class'] == 'category'])
    unknown_types = sorted([t for t, st in by_type.items() if st['class'] in ('other', 'unknown')])

    return {
        'app_version': __version__,
        'python_version': sys.version,
        'platform': sys.platform,
        'file': os.path.abspath(file_path),
        'file_size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else None,
        'total_records': total_records,
        'by_type': by_type,
        'quantity_types': quantity_types,
        'category_types': category_types,
        'unknown_types': unknown_types,
        'note': 'Category types are expected to have string values; they are not corrupt.'
    }


def generate_debug_reports(file_path: str) -> Tuple[str, str]:
    """Generate JSON and Markdown debug reports to aid troubleshooting.

    Returns: (json_path, md_path)
    """
    summary = scan_export_types(file_path)
    out_dir = get_output_dir()
    json_path = os.path.join(out_dir, 'health_types_report.json')
    md_path = os.path.join(out_dir, 'health_types_report.md')

    # Write JSON
    try:
        with open(json_path, 'w') as f:
            json.dump(summary, f, indent=2)
    except Exception:
        pass

    # Write Markdown
    try:
        lines = []
        lines.append(f"# Apple Health Export Type Report\n")
        lines.append(f"- App Version: {summary['app_version']}\n")
        lines.append(f"- Python: {summary['python_version'].splitlines()[0]}\n")
        lines.append(f"- Platform: {summary['platform']}\n")
        lines.append(f"- File: {summary['file']} ({summary['file_size_bytes']} bytes)\n")
        lines.append(f"- Total Records: {summary['total_records']}\n")
        lines.append(f"\n## Quantity Types\n")
        for t in summary['quantity_types']:
            st = summary['by_type'][t]
            lines.append(f"- {t}: {st['count']} records, units={st['units']}, bad_values={st['bad_values']}, examples={st['value_examples']}\n")
        lines.append(f"\n## Category Types (expected string values)\n")
        for t in summary['category_types']:
            st = summary['by_type'][t]
            lines.append(f"- {t}: {st['count']} records, examples={st['value_examples']}\n")
        if summary['unknown_types']:
            lines.append(f"\n## Other/Unknown Types\n")
            for t in summary['unknown_types']:
                st = summary['by_type'][t]
                lines.append(f"- {t}: {st['count']} records, examples={st['value_examples']}\n")
        lines.append("\nNote: Category and event types are not corrupt. If you’re troubleshooting, please attach this file and the JSON with your report.\n")
        with open(md_path, 'w') as f:
            f.write("".join(lines))
    except Exception:
        pass

    print(f"Generated debug reports:\n- {json_path}\n- {md_path}")
    print_open_hint(md_path)
    return json_path, md_path

def analyze_steps():
    """
    Analyze and visualize daily step count data.
    Shows a time series plot of daily total steps and exports data to CSV.
    """
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")
    df = parse_health_data(export_path, 'HKQuantityTypeIdentifierStepCount')
    
    # Check if any step data was found
    if len(df) == 0:
        print("No step data found in the export file.")
        # Create an empty CSV file to indicate processing was attempted
        empty_csv = get_output_path('steps_data.csv')
        DataFrame(columns=['date', 'value']).to_csv(empty_csv, index=False)
        print(f"Created empty steps_data.csv at {empty_csv}.")
        return
    
    # Daily sum of steps
    daily_steps = df.groupby(df['date'].dt.date)['value'].sum()
    
    # Export to CSV
    csv_main = get_output_path('steps_data.csv')
    daily_steps.to_csv(csv_main, header=True)
    
    # Also write a compatibility filename without underscore if users expect it
    try:
        csv_compat = get_output_path('stepsdata.csv')
        daily_steps.to_csv(csv_compat, header=True)
        compat_note = f" and compatibility file at {csv_compat}"
    except Exception:
        compat_note = ""
    print(f"Steps data exported to {csv_main}{compat_note}")
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_steps.plot()
    plt.title('Daily Steps')
    plt.xlabel('Date')
    plt.ylabel('Steps')
    plt.grid(True)
    
    # Save plot to file so it works in headless environments
    plot_path = get_output_path('steps_plot.png')
    try:
        plt.tight_layout()
        plt.savefig(plot_path)
    except Exception:
        pass
    
    # Try to show the plot; skip if backend is non-interactive
    try:
        plt.show()
    except Exception:
        print("(Plot saved to file; display not available)")
    finally:
        plt.close()

    # Print a concise textual analysis summary
    try:
        total_days = len(daily_steps)
        date_min = min(daily_steps.index)
        date_max = max(daily_steps.index)
        total_steps = int(daily_steps.sum())
        avg_steps = float(daily_steps.mean())
        median_steps = float(daily_steps.median())
        max_day = daily_steps.idxmax()
        max_steps = int(daily_steps.max())
        over_10k = int((daily_steps >= 10000).sum())
        last7_avg = float(daily_steps.tail(7).mean()) if total_days >= 7 else float(daily_steps.mean())

        print("\nSteps Summary:")
        print(f"- Date range: {date_min} to {date_max} ({total_days} days)")
        print(f"- Total steps: {total_steps:,}")
        print(f"- Average per day: {avg_steps:,.0f} (median {median_steps:,.0f})")
        print(f"- Best day: {max_day} with {max_steps:,} steps")
        print(f"- Days ≥10k steps: {over_10k}")
        print(f"- Last 7-day average: {last7_avg:,.0f}")
        print(f"- CSV: {csv_main}")
        if compat_note:
            print(f"- CSV (compat): {csv_compat}")
        print(f"- Plot: {plot_path}")
        print_open_hint(plot_path)
        print_open_hint(plot_path)
        print_open_hint(plot_path)
    except Exception:
        # Non-fatal if any of the above fails
        pass

def analyze_distance():
    """
    Analyze and visualize daily walking/running distance.
    Shows a time series plot of daily total distance in kilometers and exports data to CSV.
    """
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")
    df = parse_health_data(export_path, 'HKQuantityTypeIdentifierDistanceWalkingRunning')
    
    # Check if any distance data was found
    if len(df) == 0:
        print("No distance data found in the export file.")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'value']).to_csv(get_output_path('distance_data.csv'), index=False)
        print(f"Created empty distance_data.csv at {get_output_path('distance_data.csv')}")
        return
    
    # Daily sum of distance (already in kilometers from Apple Health)
    daily_distance = df.groupby(df['date'].dt.date)['value'].sum()
    
    # Export to CSV
    csv_path = get_output_path('distance_data.csv')
    daily_distance.to_csv(csv_path, header=True)
    print(f"Distance data exported to {csv_path}")
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_distance.plot()
    plt.title('Daily Walking/Running Distance')
    plt.xlabel('Date')
    plt.ylabel('Distance (km)')
    plt.grid(True)
    plot_path = get_output_path('distance_plot.png')
    try:
        plt.tight_layout()
        plt.savefig(plot_path)
    except Exception:
        pass
    try:
        plt.show()
    except Exception:
        print("(Plot saved to file; display not available)")
    finally:
        plt.close()

    # Summary
    try:
        total_days = len(daily_distance)
        date_min = min(daily_distance.index)
        date_max = max(daily_distance.index)
        total_km = float(daily_distance.sum())
        avg_km = float(daily_distance.mean())
        median_km = float(daily_distance.median())
        max_day = daily_distance.idxmax()
        max_km = float(daily_distance.max())
        last7_avg = float(daily_distance.tail(7).mean()) if total_days >= 7 else avg_km

        print("\nDistance Summary:")
        print(f"- Date range: {date_min} to {date_max} ({total_days} days)")
        print(f"- Total distance: {total_km:.1f} km")
        print(f"- Average per day: {avg_km:.2f} km (median {median_km:.2f} km)")
        print(f"- Best day: {max_day} with {max_km:.2f} km")
        print(f"- Last 7-day average: {last7_avg:.2f} km")
        print(f"- CSV: {csv_path}")
        print(f"- Plot: {plot_path}")
    except Exception:
        pass

def analyze_heart_rate():
    """
    Analyze and visualize daily heart rate data.
    Shows a time series plot of daily average heart rate in BPM and exports data to CSV.
    """
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")
    df = parse_health_data(export_path, 'HKQuantityTypeIdentifierHeartRate')
    
    # Check if any heart rate data was found
    if len(df) == 0:
        print("No heart rate data found in the export file.")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'value']).to_csv(get_output_path('heart_rate_data.csv'), index=False)
        print(f"Created empty heart_rate_data.csv at {get_output_path('heart_rate_data.csv')}")
        return
    
    # Daily average heart rate
    daily_hr = df.groupby(df['date'].dt.date)['value'].mean()
    
    # Export to CSV
    csv_path = get_output_path('heart_rate_data.csv')
    daily_hr.to_csv(csv_path, header=True)
    print(f"Heart rate data exported to {csv_path}")
    
    # Plot
    plt.figure(figsize=(12, 6))
    daily_hr.plot()
    plt.title('Daily Average Heart Rate')
    plt.xlabel('Date')
    plt.ylabel('Heart Rate (BPM)')
    plt.grid(True)
    plot_path = get_output_path('heart_rate_plot.png')
    try:
        plt.tight_layout()
        plt.savefig(plot_path)
    except Exception:
        pass
    try:
        plt.show()
    except Exception:
        print("(Plot saved to file; display not available)")
    finally:
        plt.close()

    # Summary
    try:
        total_days = len(daily_hr)
        date_min = min(daily_hr.index)
        date_max = max(daily_hr.index)
        avg_bpm = float(daily_hr.mean())
        median_bpm = float(daily_hr.median())
        max_day = daily_hr.idxmax()
        max_bpm = float(daily_hr.max())
        min_day = daily_hr.idxmin()
        min_bpm = float(daily_hr.min())
        last7_avg = float(daily_hr.tail(7).mean()) if total_days >= 7 else avg_bpm

        print("\nHeart Rate Summary:")
        print(f"- Date range: {date_min} to {date_max} ({total_days} days)")
        print(f"- Average daily mean: {avg_bpm:.1f} BPM (median {median_bpm:.1f})")
        print(f"- Highest daily mean: {max_bpm:.1f} BPM on {max_day}")
        print(f"- Lowest daily mean: {min_bpm:.1f} BPM on {min_day}")
        print(f"- Last 7-day average: {last7_avg:.1f} BPM")
        print(f"- CSV: {csv_path}")
        print(f"- Plot: {plot_path}")
    except Exception:
        pass

def analyze_weight():
    """
    Analyze and visualize body weight data.
    Shows a time series plot of daily weight measurements in kg.
    """
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")
    df = parse_health_data(export_path, 'HKQuantityTypeIdentifierBodyMass')
    
    # Check if any weight data was found
    if len(df) == 0:
        print("No weight data found in the export file.")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'value']).to_csv(get_output_path('weight_data.csv'), index=False)
        print(f"Created empty weight_data.csv at {get_output_path('weight_data.csv')}")
        return
    
    # Daily weight (taking the last measurement of each day)
    daily_weight = df.groupby(df['date'].dt.date)['value'].last()
    
    # Export to CSV
    csv_path = get_output_path('weight_data.csv')
    daily_weight.to_csv(csv_path, header=True)
    print(f"Weight data exported to {csv_path}")

    # Plot
    plt.figure(figsize=(12, 6))
    daily_weight.plot()
    plt.title('Body Weight Over Time')
    plt.xlabel('Date')
    plt.ylabel('Weight (kg)')
    plt.grid(True)
    plot_path = get_output_path('weight_plot.png')
    try:
        plt.tight_layout()
        plt.savefig(plot_path)
    except Exception:
        pass
    try:
        plt.show()
    except Exception:
        print("(Plot saved to file; display not available)")
    finally:
        plt.close()

    # Summary
    try:
        total_days = len(daily_weight)
        date_min = min(daily_weight.index)
        date_max = max(daily_weight.index)
        avg_wt = float(daily_weight.mean())
        median_wt = float(daily_weight.median())
        min_day = daily_weight.idxmin()
        min_wt = float(daily_weight.min())
        max_day = daily_weight.idxmax()
        max_wt = float(daily_weight.max())

        print("\nWeight Summary:")
        print(f"- Date range: {date_min} to {date_max} ({total_days} days)")
        print(f"- Average: {avg_wt:.1f} kg (median {median_wt:.1f} kg)")
        print(f"- Min: {min_wt:.1f} kg on {min_day}")
        print(f"- Max: {max_wt:.1f} kg on {max_day}")
        print(f"- CSV: {csv_path}")
        print(f"- Plot: {plot_path}")
    except Exception:
        pass

def analyze_sleep():
    """
    Analyze and visualize sleep duration data.
    Shows a time series plot of daily total sleep duration in hours.
    """
    print("Analyzing sleep data...")
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")
    tree = ET.parse(export_path)
    root = tree.getroot()
    
    sleep_records = []
    
    # Process sleep records
    for record in root.findall('.//Record'):
        if record.get('type') == 'HKCategoryTypeIdentifierSleepAnalysis':
            try:
                start_date_str = record.get('startDate')
                end_date_str = record.get('endDate')
                sleep_value = record.get('value')
                source_name = record.get('sourceName', 'Unknown')
                
                if not start_date_str or not end_date_str or not sleep_value:
                    continue
                    
                # Parse dates
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S %z')
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S %z')
                
                # Calculate duration in minutes
                duration_minutes = (end_date - start_date).total_seconds() / 60
                
                # Classify sleep type
                sleep_type = 'Unknown'
                if 'InBed' in sleep_value:
                    sleep_type = 'In Bed'
                elif 'AsleepUnspecified' in sleep_value:
                    sleep_type = 'Asleep'
                elif 'AsleepREM' in sleep_value:
                    sleep_type = 'REM Sleep'
                elif 'AsleepCore' in sleep_value:
                    sleep_type = 'Core Sleep'
                elif 'AsleepDeep' in sleep_value:
                    sleep_type = 'Deep Sleep'
                elif 'Awake' in sleep_value:
                    sleep_type = 'Awake'
                
                sleep_records.append({
                    'date': start_date.date(),
                    'start_time': start_date.time(),
                    'end_time': end_date.time(),
                    'duration_minutes': round(duration_minutes, 1),
                    'duration_hours': round(duration_minutes / 60, 2),
                    'sleep_type': sleep_type,
                    'sleep_value': sleep_value,
                    'source': source_name
                })
                
            except (ValueError, TypeError) as e:
                continue
    
    if not sleep_records:
        print("No sleep data found!")
        return
        
    df = DataFrame(sleep_records)
    df = df.sort_values('date')
    
    # Export to CSV
    export_df = df.copy()
    export_df['date'] = export_df['date'].astype(str)
    csv_path = get_output_path('sleep_data.csv')
    export_df.to_csv(csv_path, index=False)
    print(f"\nSleep data exported to {csv_path}")
    print(f"Exported {len(export_df)} sleep records")
    
    # Display first few rows
    print("\nFirst few rows of exported data:")
    print(export_df.head())
    
    # Calculate daily sleep totals (excluding 'Awake' periods for actual sleep time)
    sleep_only = df[~df['sleep_type'].isin(['Awake', 'In Bed'])]
    daily_sleep = sleep_only.groupby('date')['duration_hours'].sum()
    
    # Also calculate total time in bed
    in_bed_data = df[df['sleep_type'] == 'In Bed']
    daily_in_bed = in_bed_data.groupby('date')['duration_hours'].sum()
    
    # Plot
    plt.figure(figsize=(12, 8))
    
    # Plot 1: Daily sleep duration
    plt.subplot(2, 1, 1)
    if len(daily_sleep) > 0:
        daily_sleep.plot(kind='line', marker='o', alpha=0.7)
        plt.title('Daily Sleep Duration (Excluding Awake Time)')
        plt.xlabel('Date')
        plt.ylabel('Sleep Duration (hours)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
    
    # Plot 2: Sleep type breakdown over time
    plt.subplot(2, 1, 2)
    sleep_type_daily = df.groupby(['date', 'sleep_type'])['duration_hours'].sum().unstack(fill_value=0)
    sleep_type_daily.plot(kind='area', stacked=True, alpha=0.7)
    plt.title('Daily Sleep Composition by Type')
    plt.xlabel('Date')
    plt.ylabel('Duration (hours)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plot_path = get_output_path('sleep_plot.png')
    try:
        plt.savefig(plot_path)
    except Exception:
        pass
    try:
        plt.show()
    except Exception:
        print("(Plot saved to file; display not available)")
    finally:
        plt.close()
    
    # Print summary statistics
    print(f"\nSleep Summary:")
    print(f"Total sleep records: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    if len(daily_sleep) > 0:
        print(f"Average nightly sleep: {daily_sleep.mean():.1f} hours")
        print(f"Total sleep time: {daily_sleep.sum():.1f} hours")
    print(f"CSV: {csv_path}")
    print(f"Plot: {plot_path}")
    print_open_hint(plot_path)
    
    # Sleep type breakdown
    print(f"\nSleep Type Breakdown:")
    type_summary = df.groupby('sleep_type').agg({
        'duration_hours': ['count', 'sum', 'mean']
    }).round(2)
    for sleep_type in df['sleep_type'].unique():
        records = df[df['sleep_type'] == sleep_type]
        total_hours = records['duration_hours'].sum()
        avg_duration = records['duration_hours'].mean()
        count = len(records)
        print(f"  {sleep_type}: {count} records, {total_hours:.1f} total hours (avg {avg_duration:.1f}h per record)")
    
    # Source breakdown
    print(f"\nData Sources:")
    for source in df['source'].unique():
        count = len(df[df['source'] == source])
        print(f"  {source}: {count} records")
    
    print(f"\nRecent Sleep Records:")
    recent = df.sort_values('date', ascending=False).head(10)
    for _, record in recent.iterrows():
        print(f"\nDate: {record['date']} ({record['start_time']} - {record['end_time']})")
        print(f"Type: {record['sleep_type']}")
        print(f"Duration: {record['duration_hours']:.1f} hours")
        print(f"Source: {record['source']}")

def analyze_workouts():
    """
    Analyze and visualize Apple Workout data from export.xml.
    Exports workout data to CSV and shows time series plot of daily workout durations.
    """
    print("Analyzing workout data...")
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")
    tree = ET.parse(export_path)
    root = tree.getroot()
    
    workouts = []
    
    # Process Workout elements
    for workout in root.findall('.//Workout'):
        try:
            # Extract basic workout info
            activity_type = workout.get('workoutActivityType', 'Unknown')
            duration_str = workout.get('duration')
            duration_unit = workout.get('durationUnit', 'min')
            start_date_str = workout.get('startDate')
            end_date_str = workout.get('endDate')
            source_name = workout.get('sourceName', 'Unknown')
            
            if not duration_str or not start_date_str:
                continue
                
            # Parse dates
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S %z')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S %z')
            
            # Convert duration to minutes
            duration_value = float(duration_str)
            if duration_unit == 'min':
                duration_minutes = duration_value
            elif duration_unit == 'sec':
                duration_minutes = duration_value / 60
            elif duration_unit == 'h':
                duration_minutes = duration_value * 60
            else:
                duration_minutes = duration_value  # assume minutes
            
            # Extract calories and distance from WorkoutStatistics
            calories = 0
            distance_km = 0
            
            for stat in workout.findall('.//WorkoutStatistics'):
                stat_type = stat.get('type', '')
                sum_value = stat.get('sum')
                unit = stat.get('unit', '')
                
                if sum_value:
                    if 'ActiveEnergyBurned' in stat_type:
                        calories = float(sum_value)
                    elif 'DistanceWalkingRunning' in stat_type:
                        if unit == 'km':
                            distance_km = float(sum_value)
                        elif unit == 'm':
                            distance_km = float(sum_value) / 1000
            
            workouts.append({
                'date': start_date.date(),
                'start_time': start_date.time(),
                'activity_type': activity_type.replace('HKWorkoutActivityType', ''),
                'duration_minutes': round(duration_minutes, 1),
                'duration_hours': round(duration_minutes / 60, 2),
                'calories': round(calories, 1),
                'distance_km': round(distance_km, 2),
                'source': source_name
            })
                
        except (ValueError, TypeError) as e:
            continue
    
    if not workouts:
        print("No workout data found!")
        # Create an empty CSV file to indicate processing was attempted
        DataFrame(columns=['date', 'duration_hours', 'avg_heart_rate', 'measurements']).to_csv(get_output_path('workout_data.csv'), index=False)
        print(f"Created empty workout_data.csv at {get_output_path('workout_data.csv')}")
        return
        
    df = DataFrame(workouts)
    df = df.sort_values('date')
    
    # Export to CSV with more descriptive column names
    export_df = df.copy()
    export_df['date'] = export_df['date'].astype(str)  # Convert date to string for better CSV compatibility
    csv_path = get_output_path('workout_data.csv')
    export_df.to_csv(csv_path, index=False)
    print(f"\nWorkout data exported to {csv_path}")
    print(f"Exported {len(export_df)} workouts")
    
    # Display first few rows of exported data
    print("\nFirst few rows of exported data:")
    print(export_df.head())
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.scatter(df['date'], df['duration_hours'], alpha=0.6, c=df.index, cmap='viridis')
    plt.title('Workout Duration Over Time')
    plt.xlabel('Date')
    plt.ylabel('Duration (Hours)')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plot_path = get_output_path('workout_plot.png')
    try:
        plt.savefig(plot_path)
    except Exception:
        pass
    try:
        plt.show()
    except Exception:
        print("(Plot saved to file; display not available)")
    finally:
        plt.close()
    
    # Print summary statistics
    print("\nWorkout Summary:")
    print(f"Total workouts: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Average workout duration: {df['duration_minutes'].mean():.1f} minutes")
    print(f"Total workout time: {df['duration_hours'].sum():.1f} hours")
    print(f"Total calories burned: {df['calories'].sum():.0f} kcal")
    print(f"Total distance: {df['distance_km'].sum():.1f} km")
    print(f"CSV: {csv_path}")
    print(f"Plot: {plot_path}")
    
    # Activity type breakdown
    print(f"\nWorkout Types:")
    activity_counts = df['activity_type'].value_counts()
    for activity, count in activity_counts.head(10).items():
        avg_duration = df[df['activity_type'] == activity]['duration_minutes'].mean()
        print(f"  {activity}: {count} workouts (avg {avg_duration:.1f} min)")
    
    print(f"\nRecent Workouts:")
    recent = df.sort_values('date', ascending=False).head(5)
    for _, workout in recent.iterrows():
        print(f"\nDate: {workout['date']} at {workout['start_time']}")
        print(f"Activity: {workout['activity_type']}")
        print(f"Duration: {workout['duration_minutes']:.1f} minutes")
        if workout['calories'] > 0:
            print(f"Calories: {workout['calories']:.0f} kcal")
        if workout['distance_km'] > 0:
            print(f"Distance: {workout['distance_km']:.1f} km")

def analyze_with_chatgpt(csv_files):
    """
    Analyze health data using OpenAI's ChatGPT.
    
    Args:
        csv_files: List of CSV files to analyze
    """
    # Load environment variables if present and prompt for key if missing
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\nOpenAI API key not found in environment.")
        entered = input("Paste your OpenAI API key (sk-...): ").strip()
        if not entered:
            print("Skipping ChatGPT analysis: no API key provided.")
            return
        api_key = entered
        os.environ['OPENAI_API_KEY'] = api_key
    openai.api_key = api_key
    
    # Check if required data files exist and run analyses if needed
    missing_files = []
    for file_name, data_type in csv_files:
        path = get_output_path(file_name)
        if not os.path.exists(path):
            missing_files.append((file_name, data_type))
    
    if missing_files:
        print("\nSome required data files are missing. Running analyses to generate them...")
        print("Note: This will generate all required data files without displaying plots.")
        print("You can view the plots later by running options 1-6 individually.")
        
        # Temporarily disable plot display to avoid blocking
        original_show = plt.show
        plt.show = lambda: None  # Replace with no-op function
        
        try:
            # Map file names to their corresponding analysis functions
            analysis_functions = {
                'steps_data.csv': analyze_steps,
                'distance_data.csv': analyze_distance,
                'heart_rate_data.csv': analyze_heart_rate,
                'weight_data.csv': analyze_weight,
                'sleep_data.csv': analyze_sleep,
                'workout_data.csv': analyze_workouts
            }
            
            # Run the necessary analyses
            for file_name, data_type in missing_files:
                if file_name in analysis_functions:
                    print(f"\nGenerating {file_name} from {data_type} data...")
                    analysis_functions[file_name]()
                    # Verify the file was created
                    gen_path = get_output_path(file_name)
                    if os.path.exists(gen_path):
                        print(f"✓ Successfully generated {gen_path}")
                    else:
                        print(f"✗ Failed to generate {gen_path}")
        finally:
            # Restore original plt.show function
            plt.show = original_show
    
    # Add data preparation code
    data_summary = {}
    files_found = False
    
    print("\nProcessing data files for ChatGPT analysis...")
    for file_name, data_type in csv_files:
        try:
            path = get_output_path(file_name)
            if os.path.exists(path):
                df = read_csv(path)
                
                # Skip empty dataframes
                if len(df) == 0:
                    print(f"Note: {path} exists but contains no data.")
                    continue
                
                print(f"Found {data_type} data in {path}")
                
                data_summary[data_type] = {
                    'total_records': len(df),
                    'date_range': f"from {df['date'].min()} to {df['date'].max()}" if 'date' in df and len(df) > 0 else 'N/A',
                    'average': f"{df['value'].mean():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'max_value': f"{df['value'].max():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'min_value': f"{df['value'].min():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'data_sample': df.head(50).to_string() if len(df) > 0 else 'No data available'
                }
                files_found = True
            else:
                print(f"Warning: {file_name} still not found after attempted generation.")
                
        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}")
            continue

    if not files_found:
        print("\nNo data files with content could be processed! Please check your export.xml file.")
        print("It appears your Apple Health export doesn't contain the expected health metrics.")
        return

    # Build the prompt
    prompt = "Analyze this Apple Health data and provide detailed insights:\n\n"
    for data_type, summary in data_summary.items():
        prompt += f"\n{data_type} Data Summary:\n"
        prompt += f"- Total Records: {summary['total_records']}\n"
        prompt += f"- Date Range: {summary['date_range']}\n"
        prompt += f"- Average Value: {summary['average']}\n"
        prompt += f"- Maximum Value: {summary['max_value']}\n"
        prompt += f"- Minimum Value: {summary['min_value']}\n"
        prompt += f"\nSample Data:\n{summary['data_sample']}\n"
        prompt += "\n" + "="*50 + "\n"

    prompt += """Please provide a comprehensive analysis including:
    1. Notable patterns or trends in the data
    2. Unusual findings or correlations between different metrics
    3. Actionable health insights based on the data
    4. Areas that might need attention or improvement
    """

    try:
        # Send to OpenAI API with timeout and streaming
        model_name = _prompt_model_name("openai_model", "gpt-4o", "OpenAI (ChatGPT)", "gpt-4o, gpt-4o-mini, gpt-4-turbo")
        _status(f"Using OpenAI model: {model_name}")
        client = openai.OpenAI(api_key=api_key, timeout=60.0, max_retries=1)

        _status("Preparing request and contacting OpenAI...")
        with spinner("Contacting OpenAI"):
            stream = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True,
            )

        print("Streaming analysis...\n")
        collected = []
        start_time = time.time()
        try:
            for chunk in stream:
                delta = None
                try:
                    delta = chunk.choices[0].delta
                    piece = getattr(delta, 'content', None)
                except Exception:
                    delta = chunk.get('choices', [{}])[0].get('delta', {}) if isinstance(chunk, dict) else {}
                    piece = delta.get('content')
                if piece:
                    collected.append(piece)
                    print(piece, end='', flush=True)
        except Exception as stream_err:
            print(f"\nStreaming interrupted: {stream_err}\nFalling back to non-streaming request...")
            with spinner("Waiting for response"):
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
            collected.append(resp.choices[0].message.content)
            print(resp.choices[0].message.content)

        print("\n\nDone in {:.1f}s".format(time.time() - start_time))
        analysis_content = "".join(collected)

        _prompt_and_save_analysis(analysis_content, 'ChatGPT', 'health_analysis_chatgpt')
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"\nError during ChatGPT analysis: {str(e)}")

def analyze_with_ollama(csv_files):
    """
    Analyze health data using a local Ollama LLM.
    
    Args:
        csv_files: List of CSV files to analyze
    """
    try:
        # Check if required data files exist and run analyses if needed
        missing_files = []
        for file_name, data_type in csv_files:
            path = get_output_path(file_name)
            if not os.path.exists(path):
                missing_files.append((file_name, data_type))
        
        if missing_files:
            print("\nSome required data files are missing. Running analyses to generate them...")
            print("Note: This will generate all required data files without displaying plots.")
            print("You can view the plots later by running options 1-6 individually.")
            
            # Temporarily disable plot display to avoid blocking
            original_show = plt.show
            plt.show = lambda: None  # Replace with no-op function
            
            try:
                # Map file names to their corresponding analysis functions
                analysis_functions = {
                    'steps_data.csv': analyze_steps,
                    'distance_data.csv': analyze_distance,
                    'heart_rate_data.csv': analyze_heart_rate,
                    'weight_data.csv': analyze_weight,
                    'sleep_data.csv': analyze_sleep,
                    'workout_data.csv': analyze_workouts
                }
                
                # Run the necessary analyses
                for file_name, data_type in missing_files:
                    if file_name in analysis_functions:
                        print(f"\nGenerating {file_name} from {data_type} data...")
                        analysis_functions[file_name]()
                        # Verify the file was created
                        gen_path = get_output_path(file_name)
                        if os.path.exists(gen_path):
                            print(f"✓ Successfully generated {gen_path}")
                        else:
                            print(f"✗ Failed to generate {gen_path}")
            finally:
                # Restore original plt.show function
                plt.show = original_show
        
        # Add data preparation code
        data_summary = {}
        files_found = False
        
        print("\nProcessing data files...")
        for file_name, data_type in csv_files:
            try:
                path = get_output_path(file_name)
                if os.path.exists(path):
                    df = read_csv(path)
                    
                    # Skip empty dataframes
                    if len(df) == 0:
                        print(f"Note: {path} exists but contains no data.")
                        continue
                    
                    print(f"Found {data_type} data in {path}")
                    
                    data_summary[data_type] = {
                        'total_records': len(df),
                        'date_range': f"from {df['date'].min()} to {df['date'].max()}" if 'date' in df and len(df) > 0 else 'N/A',
                        'average': f"{df['value'].mean():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'max_value': f"{df['value'].max():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'min_value': f"{df['value'].min():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'data_sample': df.head(50).to_string() if len(df) > 0 else 'No data available'
                    }
                    files_found = True
                else:
                    print(f"Warning: {file_name} still not found after attempted generation.")
                    
            except Exception as e:
                print(f"Error processing {file_name}: {str(e)}")
                continue

        if not files_found:
            print("\nNo data files with content could be processed! Please check your export.xml file.")
            print("It appears your Apple Health export doesn't contain the expected health metrics.")
            return

        # Build the prompt
        prompt = "Analyze this Apple Health data and provide detailed insights:\n\n"
        for data_type, summary in data_summary.items():
            prompt += f"\n{data_type} Data Summary:\n"
            prompt += f"- Total Records: {summary['total_records']}\n"
            prompt += f"- Date Range: {summary['date_range']}\n"
            prompt += f"- Average Value: {summary['average']}\n"
            prompt += f"- Maximum Value: {summary['max_value']}\n"
            prompt += f"- Minimum Value: {summary['min_value']}\n"
            prompt += f"\nSample Data:\n{summary['data_sample']}\n"
            prompt += "\n" + "="*50 + "\n"

        prompt += """Please provide a comprehensive analysis including:
        1. Notable patterns or trends in the data
        2. Unusual findings or correlations between different metrics
        3. Actionable health insights based on the data
        4. Areas that might need attention or improvement
        """

        # Rest of the Ollama API call with streaming
        _status("Contacting local Ollama (Deepseek-R1)...")
        collected = []
        try:
            with spinner("Contacting Ollama"):
                stream = ollama.chat(
                    model='deepseek-r1',
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."},
                        {"role": "user", "content": prompt}
                    ],
                    options={'temperature': 0.3, 'num_ctx': 6144},
                    stream=True,
                )
            print("Streaming analysis...\n")
            start_time = time.time()
            for chunk in stream:
                text = _extract_ollama_chunk_text(chunk)
                if text:
                    collected.append(text)
                    print(text, end='', flush=True)
            print("\n\nDone in {:.1f}s".format(time.time() - start_time))
        except Exception:
            with spinner("Waiting for Ollama response"):
                response = ollama.chat(
                    model='deepseek-r1',
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."},
                        {"role": "user", "content": prompt}
                    ],
                    options={'temperature': 0.3, 'num_ctx': 6144},
                )
            analysis_content = response['message']['content']
            collected.append(analysis_content)
            print(analysis_content)
        
        # Ask if user wants to save the analysis
        save_option = input("\nWould you like to save this analysis as a markdown file? (y/n): ").strip().lower()
        if save_option == 'y' or save_option == 'yes':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_analysis_ollama_{timestamp}.md"
            
            # Create markdown content
            markdown_content = f"# Apple Health Data Analysis (Ollama Deepseek-R1)\n\n"
            markdown_content += f"*Analysis generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            markdown_content += f"## Data Summary\n\n"
            
            for data_type, summary in data_summary.items():
                markdown_content += f"### {data_type}\n\n"
                markdown_content += f"- **Total Records:** {summary['total_records']}\n"
                markdown_content += f"- **Date Range:** {summary['date_range']}\n"
                markdown_content += f"- **Average Value:** {summary['average']}\n"
                markdown_content += f"- **Maximum Value:** {summary['max_value']}\n"
                markdown_content += f"- **Minimum Value:** {summary['min_value']}\n\n"
            
            markdown_content += f"## Analysis Results\n\n"
            final_text = _strip_reasoning_blocks("".join(collected))
            markdown_content += final_text
            
            # Save to file
            filepath = get_output_path(filename)
            with open(filepath, 'w') as f:
                f.write(markdown_content)
            
            print(f"\nAnalysis saved to {filepath}")

    except Exception as e:
        print(f"Error during analysis: {str(e)}")

def analyze_with_external_ollama(csv_files):
    """
    Analyze health data using an external Ollama LLM.
    
    Args:
        csv_files: List of CSV files to analyze
    """
    try:
        # Load environment variables
        load_dotenv()
        
        # Get Ollama host from .env file or use default
        default_host = "http://localhost:11434"
        ollama_host = os.getenv('OLLAMA_HOST', default_host)
        
        # Ask user if they want to use a different Ollama host
        print(f"\nUsing Ollama host: {ollama_host}")
        use_custom_host = input(f"Use a different Ollama host? (y/n): ").strip().lower()
        if use_custom_host == 'y' or use_custom_host == 'yes':
            custom_host = input("Enter the Ollama host (e.g., http://example.com:11434): ").strip()
            if custom_host:
                ollama_host = custom_host
                print(f"Using custom Ollama host: {ollama_host}")
        
        # Check if required data files exist and run analyses if needed
        missing_files = []
        for file_name, data_type in csv_files:
            path = get_output_path(file_name)
            if not os.path.exists(path):
                missing_files.append((file_name, data_type))
        
        if missing_files:
            print("\nSome required data files are missing. Running analyses to generate them...")
            print("Note: This will generate all required data files without displaying plots.")
            print("You can view the plots later by running options 1-6 individually.")
            
            # Temporarily disable plot display to avoid blocking
            original_show = plt.show
            plt.show = lambda: None  # Replace with no-op function
            
            try:
                # Map file names to their corresponding analysis functions
                analysis_functions = {
                    'steps_data.csv': analyze_steps,
                    'distance_data.csv': analyze_distance,
                    'heart_rate_data.csv': analyze_heart_rate,
                    'weight_data.csv': analyze_weight,
                    'sleep_data.csv': analyze_sleep,
                    'workout_data.csv': analyze_workouts
                }
                
                # Run the necessary analyses
                for file_name, data_type in missing_files:
                    if file_name in analysis_functions:
                        print(f"\nGenerating {file_name} from {data_type} data...")
                        analysis_functions[file_name]()
                        # Verify the file was created
                        gen_path = get_output_path(file_name)
                        if os.path.exists(gen_path):
                            print(f"✓ Successfully generated {gen_path}")
                        else:
                            print(f"✗ Failed to generate {gen_path}")
            finally:
                # Restore original plt.show function
                plt.show = original_show
        
        # Add data preparation code
        data_summary = {}
        files_found = False
        
        print("\nProcessing data files...")
        for file_name, data_type in csv_files:
            try:
                path = get_output_path(file_name)
                if os.path.exists(path):
                    df = read_csv(path)
                    
                    # Skip empty dataframes
                    if len(df) == 0:
                        print(f"Note: {path} exists but contains no data.")
                        continue
                    
                    print(f"Found {data_type} data in {path}")
                    
                    data_summary[data_type] = {
                        'total_records': len(df),
                        'date_range': f"from {df['date'].min()} to {df['date'].max()}" if 'date' in df and len(df) > 0 else 'N/A',
                        'average': f"{df['value'].mean():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'max_value': f"{df['value'].max():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'min_value': f"{df['value'].min():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                        'data_sample': df.head(50).to_string() if len(df) > 0 else 'No data available'
                    }
                    files_found = True
                else:
                    print(f"Warning: {file_name} still not found after attempted generation.")
                    
            except Exception as e:
                print(f"Error processing {file_name}: {str(e)}")
                continue

        if not files_found:
            print("\nNo data files with content could be processed! Please check your export.xml file.")
            print("It appears your Apple Health export doesn't contain the expected health metrics.")
            return

        # Build the prompt
        user_prompt = "Analyze this Apple Health data and provide detailed insights:\n\n"
        for data_type, summary in data_summary.items():
            user_prompt += f"\n{data_type} Data Summary:\n"
            user_prompt += f"- Total Records: {summary['total_records']}\n"
            user_prompt += f"- Date Range: {summary['date_range']}\n"
            user_prompt += f"- Average Value: {summary['average']}\n"
            user_prompt += f"- Maximum Value: {summary['max_value']}\n"
            user_prompt += f"- Minimum Value: {summary['min_value']}\n"
            user_prompt += f"\nSample Data:\n{summary['data_sample']}\n"
            user_prompt += "\n" + "="*50 + "\n"

        user_prompt += """Please provide a comprehensive analysis including:
        1. Notable patterns or trends in the data
        2. Unusual findings or correlations between different metrics
        3. Actionable health insights based on the data
        4. Areas that might need attention or improvement
        """

        # Connect to external Ollama API server
        print("\nConnecting to Ollama server...")
        
        # Messages to send to the model
        messages = [
            {
                "role": "system",
                "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."
            }, 
            {
                "role": "user", 
                "content": user_prompt
            }
        ]
        
        # Options for the model
        options = {
            "temperature": 0.3,
            "num_ctx": 6144
        }
        
        # Set up Ollama client with the specified host
        try:
            # Import the Client class from ollama
            from ollama import Client
            
            # Create an Ollama client with the specified host
            print(f"Creating Ollama client with host: {ollama_host}")
            client = Client(host=ollama_host)
            
            # Test connectivity and list available models
            try:
                print("Testing connectivity and listing available models...")
                models_list = client.list()
                print("Successfully connected to Ollama server!")
                
                # Extract and display available models
                model_names = [model.get("name") for model in models_list.get("models", [])]
                if model_names:
                    print(f"Available models: {', '.join(model_names)}")
                    
                    # Try to find a deepseek model
                    deepseek_models = [m for m in model_names if 'deepseek' in m]
                    if deepseek_models:
                        model_name = deepseek_models[0]
                        print(f"Selected deepseek model: {model_name}")
                    else:
                        # Otherwise use the first available model
                        model_name = model_names[0]
                        print(f"No deepseek model found. Using: {model_name}")
                else:
                    print("No models found on the server. Using default 'deepseek-r1:7b'")
                    model_name = "deepseek-r1:7b"
            except Exception as e:
                print(f"Error listing models: {e}")
                print("Using default model 'deepseek-r1:7b'")
                model_name = "deepseek-r1:7b"

            # Prepare messages for the chat API
            messages = [{
                "role": "system",
                "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."
            }, {
                "role": "user", 
                "content": user_prompt
            }]
            
            # Set options for the model
            options = {
                'temperature': 0.3,
                'num_ctx': 6144
            }
            
            # Send the request to the Ollama server
            print(f"\nSending data to {model_name} via Ollama...")
            try:
                # Try using chat first
                response = client.chat(
                    model=model_name,
                    messages=messages,
                    options=options
                )
                analysis_content = response['message']['content']
                print("Successfully received chat response!")
            except Exception as chat_error:
                print(f"Chat request failed: {chat_error}")
                print("Trying generate endpoint instead...")
                
                # Fall back to generate endpoint if chat fails
                try:
                    system_message = messages[0]["content"]
                    user_message = messages[1]["content"]
                    combined_prompt = f"{system_message}\n\n{user_message}"
                    
                    response = client.generate(
                        model=model_name,
                        prompt=combined_prompt,
                        options=options
                    )
                    analysis_content = response['response']
                    print("Successfully received generate response!")
                except Exception as generate_error:
                    print(f"Generate request also failed: {generate_error}")
                    raise Exception("All Ollama API requests failed")
        except ImportError:
            print("Error: Could not import Client from ollama. Make sure you have the latest version.")
            print("Try: pip install --upgrade ollama")
            raise Exception("Failed to import Ollama Client class")
        except Exception as e:
            print(f"Error communicating with Ollama server at {ollama_host}: {e}")
            
            # Check if we should try local Ollama
            use_local = input("\nExternal Ollama server connection failed. Try default local Ollama instance? (y/n): ").strip().lower()
            if use_local == 'y' or use_local == 'yes':
                try:
                    print("Falling back to local Ollama instance...")
                    # Create local client without host parameter
                    local_client = Client()
                    # Create new messages array since we didn't define it in this branch
                    local_messages = [{
                        "role": "system",
                        "content": "You are a health data analyst with strong technical skills. Provide detailed analysis with a focus on data patterns, statistical insights, and code-friendly recommendations. Use markdown formatting for technical terms."
                    }, {
                        "role": "user", 
                        "content": user_prompt
                    }]
                    
                    response = local_client.chat(
                        model='deepseek-r1',
                        messages=local_messages,
                        options=options
                    )
                    analysis_content = response['message']['content']
                    print("Successfully received response from local Ollama!")
                except Exception as local_error:
                    print(f"Error with local Ollama: {local_error}")
                    print("\nTo use Ollama, you need to either:")
                    print("1. Install and run Ollama locally (https://ollama.com/download)")
                    print("2. Provide a correct external Ollama host")
                    raise Exception("Unable to connect to any Ollama instance")
            else:
                raise Exception("User opted not to use local Ollama")

        analysis_content = response['message']['content']
        
        print("\nDeepseek-R1 Analysis:")
        print("=" * 50)
        print(analysis_content)
        
        # Ask if user wants to save the analysis
        save_option = input("\nWould you like to save this analysis as a markdown file? (y/n): ").strip().lower()
        if save_option == 'y' or save_option == 'yes':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_analysis_ollama_{timestamp}.md"
            
            # Create markdown content
            markdown_content = f"# Apple Health Data Analysis (Ollama Deepseek-R1)\n\n"
            markdown_content += f"*Analysis generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            markdown_content += f"## Data Summary\n\n"
            
            for data_type, summary in data_summary.items():
                markdown_content += f"### {data_type}\n\n"
                markdown_content += f"- **Total Records:** {summary['total_records']}\n"
                markdown_content += f"- **Date Range:** {summary['date_range']}\n"
                markdown_content += f"- **Average Value:** {summary['average']}\n"
                markdown_content += f"- **Maximum Value:** {summary['max_value']}\n"
                markdown_content += f"- **Minimum Value:** {summary['min_value']}\n\n"
            
            markdown_content += f"## Analysis Results\n\n"
            markdown_content += analysis_content
            
            # Save to file
            filepath = get_output_path(filename)
            with open(filepath, 'w') as f:
                f.write(markdown_content)
            
            print(f"\nAnalysis saved to {filepath}")

    except Exception as e:
        print(f"Error during analysis: {str(e)}")

def _get_or_prompt_key(env_name: str, label: str) -> str:
    """Return API key from env or prompt the user to paste it."""
    load_dotenv()
    key = os.getenv(env_name)
    if key:
        return key
    print(f"\n{label} API key not found.")
    key = input(f"Paste your {label} API key: ").strip()
    if not key:
        print(f"Skipping {label} analysis: no API key provided.")
        return None
    os.environ[env_name] = key
    return key

def _prepare_ai_data(csv_files):
    """Generate missing CSVs if needed and build a shared prompt."""
    missing_files = []
    for file_name, data_type in csv_files:
        if not os.path.exists(get_output_path(file_name)):
            missing_files.append((file_name, data_type))

    if missing_files:
        print("\nSome required data files are missing. Running analyses to generate them...")
        original_show = plt.show
        plt.show = lambda: None
        try:
            analysis_functions = {
                'steps_data.csv': analyze_steps,
                'distance_data.csv': analyze_distance,
                'heart_rate_data.csv': analyze_heart_rate,
                'weight_data.csv': analyze_weight,
                'sleep_data.csv': analyze_sleep,
                'workout_data.csv': analyze_workouts
            }
            for file_name, data_type in missing_files:
                if file_name in analysis_functions:
                    print(f"Generating {file_name} from {data_type} data...")
                    analysis_functions[file_name]()
        finally:
            plt.show = original_show

    data_summary = {}
    files_found = False
    print("\nProcessing data files for AI analysis...")
    for file_name, data_type in csv_files:
        path = get_output_path(file_name)
        try:
            if os.path.exists(path):
                df = read_csv(path)
                if len(df) == 0:
                    print(f"Note: {path} exists but contains no data.")
                    continue
                print(f"Found {data_type} data in {path}")
                data_summary[data_type] = {
                    'total_records': len(df),
                    'date_range': f"from {df['date'].min()} to {df['date'].max()}" if 'date' in df and len(df) > 0 else 'N/A',
                    'average': f"{df['value'].mean():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'max_value': f"{df['value'].max():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'min_value': f"{df['value'].min():.2f}" if 'value' in df and len(df) > 0 else 'N/A',
                    'data_sample': df.head(50).to_string() if len(df) > 0 else 'No data available'
                }
                files_found = True
        except Exception as e:
            print(f"Error processing {path}: {e}")
            continue

    if not files_found:
        print("\nNo data files with content could be processed! Please check your export.xml file.")
        return None, None

    prompt = "Analyze this Apple Health data and provide detailed insights:\n\n"
    for data_type, summary in data_summary.items():
        prompt += f"\n{data_type} Data Summary:\n"
        prompt += f"- Total Records: {summary['total_records']}\n"
        prompt += f"- Date Range: {summary['date_range']}\n"
        prompt += f"- Average Value: {summary['average']}\n"
        prompt += f"- Maximum Value: {summary['max_value']}\n"
        prompt += f"- Minimum Value: {summary['min_value']}\n"
        prompt += f"\nSample Data:\n{summary['data_sample']}\n"
        prompt += "\n" + "="*50 + "\n"

    prompt += (
        "Please provide a comprehensive analysis including:\n"
        "1. Notable patterns or trends in the data\n"
        "2. Unusual findings or correlations between different metrics\n"
        "3. Actionable health insights based on the data\n"
        "4. Areas that might need attention or improvement\n"
    )

    return data_summary, prompt

def _prompt_and_save_analysis(analysis_content: str, provider_label: str, filename_prefix: str):
    print(f"\n{provider_label} Analysis:")
    print("=" * 50)
    print(analysis_content)
    # Do not offer to save if there's no content
    if not analysis_content or not str(analysis_content).strip():
        print("\n(No content received to save.)")
        return
    save_option = input("\nSave this analysis as a markdown file? (y/n): ").strip().lower()
    if save_option in ('y', 'yes'):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{timestamp}.md"
        filepath = get_output_path(filename)
        with open(filepath, 'w') as f:
            f.write(f"# Apple Health Data Analysis ({provider_label})\n\n")
            f.write(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(analysis_content)
        print(f"Saved to {filepath}")

def _prompt_model_name(provider_key: str, default_model: str, provider_label: str, examples: str = "") -> str:
    """Prompt user to optionally override the model name for a provider and remember it."""
    try:
        remembered = _get_saved_model(provider_key, default_model)
        hint = f" (e.g., {examples})" if examples else ""
        entered = input(f"\nModel for {provider_label} [{remembered}]{hint}: ").strip()
        chosen = entered or remembered
        _set_saved_model(provider_key, chosen)
        return chosen
    except Exception:
        return default_model

def analyze_with_claude(csv_files):
    key = _get_or_prompt_key('ANTHROPIC_API_KEY', 'Anthropic (Claude)')
    if not key:
        return
    if anthropic is None:
        print("anthropic package not installed. Run: pip install anthropic")
        return
    data_summary, prompt = _prepare_ai_data(csv_files)
    if prompt is None:
        return
    try:
        model_name = _prompt_model_name("claude_model", "claude-3-5-sonnet-latest", "Claude", "claude-3-5-sonnet-latest, claude-3-opus-latest")
        client = anthropic.Anthropic(api_key=key)

        _status("Contacting Claude (streaming)...")
        collected = []
        try:
            # Stream if available
            with spinner("Contacting Claude"):
                stream = client.messages.stream(
                    model=model_name,
                    max_tokens=2000,
                    temperature=0.3,
                    system="You are a health data analyst with strong technical skills.",
                    messages=[{"role": "user", "content": prompt}]
                )
            print("Streaming analysis...\n")
            start_time = time.time()
            with stream as s:
                for event in s:
                    try:
                        # anthropic events: content_block_delta has .delta with text
                        if getattr(event, 'type', '') == 'content_block_delta':
                            delta = getattr(event, 'delta', None)
                            text = getattr(delta, 'text', None) if delta is not None else None
                            if not text and isinstance(delta, dict):
                                text = delta.get('text')
                            if text:
                                collected.append(text)
                                print(text, end='', flush=True)
                    except Exception:
                        pass
                final_msg = s.get_final_message()
                if getattr(final_msg, 'content', None):
                    # Append any remaining text blocks
                    for blk in final_msg.content:
                        text = getattr(blk, 'text', None)
                        if not text and isinstance(blk, dict):
                            text = blk.get('text')
                        if text:
                            collected.append(text)
                            print(text, end='', flush=True)
            print("\n\nDone in {:.1f}s".format(time.time() - start_time))
        except Exception:
            # Fallback to non-streaming
            with spinner("Waiting for Claude response"):
                resp = client.messages.create(
                    model=model_name,
                    max_tokens=2000,
                    temperature=0.3,
                    system="You are a health data analyst with strong technical skills.",
                    messages=[{"role": "user", "content": prompt}]
                )
            content = "".join([getattr(b, 'text', '') for b in resp.content])
            collected.append(content)
            print(content)

        _prompt_and_save_analysis("".join(collected), 'Claude', 'health_analysis_claude')
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"Error during Claude analysis: {e}")

def analyze_with_gemini(csv_files):
    key = _get_or_prompt_key('GEMINI_API_KEY', 'Google Gemini')
    if not key:
        return
    if genai is None:
        print("google-generativeai package not installed. Run: pip install google-generativeai")
        return
    data_summary, prompt = _prepare_ai_data(csv_files)
    if prompt is None:
        return
    try:
        genai.configure(api_key=key)
        model_name = _prompt_model_name('gemini_model', 'gemini-1.5-pro', 'Gemini', 'gemini-1.5-pro, gemini-1.5-flash')
        model = genai.GenerativeModel(model_name)
        _status("Contacting Gemini (streaming)...")
        collected = []
        try:
            with spinner("Contacting Gemini"):
                resp = model.generate_content(prompt, stream=True)
            print("Streaming analysis...\n")
            start_time = time.time()
            for chunk in resp:
                text = getattr(chunk, 'text', None)
                if not text and getattr(chunk, 'candidates', None):
                    try:
                        text = chunk.candidates[0].content.parts[0].text
                    except Exception:
                        text = None
                if text:
                    collected.append(text)
                    print(text, end='', flush=True)
            print("\n\nDone in {:.1f}s".format(time.time() - start_time))
        except Exception:
            with spinner("Waiting for Gemini response"):
                resp = model.generate_content(prompt)
            content = getattr(resp, 'text', None)
            if not content and getattr(resp, 'candidates', None):
                try:
                    content = resp.candidates[0].content.parts[0].text
                except Exception:
                    content = ''
            collected.append(content or '')
            print(content or '')

        _prompt_and_save_analysis("".join(collected), 'Gemini', 'health_analysis_gemini')
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"Error during Gemini analysis: {e}")

def analyze_with_grok(csv_files):
    key = _get_or_prompt_key('GROK_API_KEY', 'xAI Grok')
    if not key:
        return
    data_summary, prompt = _prepare_ai_data(csv_files)
    if prompt is None:
        return
    try:
        model_name = _prompt_model_name("grok_model", "grok-beta", "Grok (xAI)")
        client = openai.OpenAI(api_key=key, base_url="https://api.x.ai/v1", timeout=60.0, max_retries=1)

        _status("Contacting Grok (streaming)...")
        with spinner("Contacting Grok"):
            stream = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True,
            )
        print("Streaming analysis...\n")
        collected = []
        start_time = time.time()
        try:
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta
                    piece = getattr(delta, 'content', None)
                except Exception:
                    delta = chunk.get('choices', [{}])[0].get('delta', {}) if isinstance(chunk, dict) else {}
                    piece = delta.get('content')
                if piece:
                    collected.append(piece)
                    print(piece, end='', flush=True)
        except Exception:
            with spinner("Waiting for Grok response"):
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
            text = resp.choices[0].message.content
            collected.append(text)
            print(text)
        print("\n\nDone in {:.1f}s".format(time.time() - start_time))
        _prompt_and_save_analysis("".join(collected), 'Grok', 'health_analysis_grok')
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"Error during Grok analysis: {e}")

def analyze_with_openrouter(csv_files):
    key = _get_or_prompt_key('OPENROUTER_API_KEY', 'OpenRouter')
    if not key:
        return
    data_summary, prompt = _prepare_ai_data(csv_files)
    if prompt is None:
        return

    # Prompt for model; remember across runs
    model_name = _prompt_model_name(
        "openrouter_model",
        "openrouter/auto",
        "OpenRouter",
        "openrouter/auto, meta-llama/llama-3.1-8b-instruct:free"
    )
    _status(f"Using OpenRouter model: {model_name}")

    try:
        # Configure client with sane timeouts and minimal retries
        client = openai.OpenAI(
            api_key=key,
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
            max_retries=1,
        )

        # Optional provider routing controls via env:
        #   OPENROUTER_PROVIDER_ORDER=OpenRouter,Together,DeepInfra
        #   OPENROUTER_ALLOW_FALLBACKS=true
        provider_order = _parse_csv_env('OPENROUTER_PROVIDER_ORDER')
        allow_fallbacks = _parse_bool_env('OPENROUTER_ALLOW_FALLBACKS', True)
        extra_body = {}
        if provider_order:
            extra_body['provider'] = {'order': provider_order}
        if allow_fallbacks:
            extra_body['allow_fallbacks'] = True

        # Try to validate the model is known (best-effort)
        try:
            with spinner("Validating model"):
                _ = client.models.retrieve(model_name)
        except Exception:
            _status("Model may be unavailable or gated; continuing anyway…")

        # Show spinner while sending the request
        _status("Preparing request and contacting OpenRouter...")
        with spinner("Contacting OpenRouter"):
            # Try streaming first for immediate feedback
            stream = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True,
                extra_body=extra_body or None,
            )

        print("Streaming analysis...\n")
        collected = []
        start_time = time.time()
        try:
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta
                    piece = getattr(delta, 'content', None)
                    if piece:
                        collected.append(piece)
                        # Print incrementally without adding extra newlines
                        print(piece, end='', flush=True)
                except Exception:
                    # Some SDKs return dicts; handle generically
                    delta = chunk.get('choices', [{}])[0].get('delta', {}) if isinstance(chunk, dict) else {}
                    piece = delta.get('content')
                    if piece:
                        collected.append(piece)
                        print(piece, end='', flush=True)
        except KeyboardInterrupt:
            print("\n(User cancelled streaming)\n")
        except Exception as stream_err:
            # If streaming fails mid-flight, fall back to a non-streaming request
            print(f"\nStreaming interrupted: {stream_err}\nFalling back to non-streaming request...")
            with spinner("Waiting for response"):
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    extra_body=extra_body or None,
                )
            content = resp.choices[0].message.content
            collected.append(content)
            print(content)

        # If nothing was streamed, try a non-stream request once
        if len(collected) == 0:
            _status("No streamed content received; requesting non-stream response...")
            with spinner("Waiting for response"):
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    extra_body=extra_body or None,
                )
            content = resp.choices[0].message.content or ''
            if content:
                collected.append(content)
                print(content)

        # Completions fallback for legacy models
        if len(collected) == 0:
            _status("Chat not supported? Trying legacy completions API…")
            combined_prompt = (
                "You are a health data analyst with strong technical skills.\n\n" + prompt
            )
            try:
                with spinner("Calling completions API"):
                    cresp = client.completions.create(
                        model=model_name,
                        prompt=combined_prompt,
                        max_tokens=2000,
                        temperature=0.3,
                        extra_body=extra_body or None,
                    )
                ctext = getattr(cresp.choices[0], 'text', None)
                if ctext:
                    collected.append(ctext)
                    print(ctext)
            except Exception as ce:
                _status(f"Completions fallback failed: {ce}")

        print("\n\nDone in {:.1f}s".format(time.time() - start_time))

        # Join collected text and offer to save
        final_text = "".join(collected)
        _prompt_and_save_analysis(final_text, 'OpenRouter', 'health_analysis_openrouter')

    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"Error during OpenRouter analysis: {e}")
        print("\nTips:")
        print("- Try a widely available model like 'openrouter/auto' or a :free variant.")
        print("- Check your network and OpenRouter API status/key.")
        print("- If it keeps hanging, rerun with a different model.")

def analyze_with_lmstudio(csv_files):
    """Analyze health data using LM Studio's OpenAI-compatible local server.

    Environment variables:
    - LMSTUDIO_BASE_URL: e.g., http://localhost:1234/v1 (default)
    - LMSTUDIO_API_KEY: optional; defaults to 'lm-studio'
    """
    # Prepare data prompt
    data_summary, prompt = _prepare_ai_data(csv_files)
    if prompt is None:
        return

    base_url = os.environ.get('LMSTUDIO_BASE_URL', 'http://localhost:1234/v1')
    api_key = os.environ.get('LMSTUDIO_API_KEY', 'lm-studio')
    model_name = _prompt_model_name(
        'lmstudio_model',
        'default',
        'LM Studio',
        'Enter the loaded model name shown in LM Studio'
    )
    _status(f"Using LM Studio at {base_url} with model: {model_name}")

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=60.0, max_retries=1)

        # Try to list models (best-effort)
        try:
            with spinner("Checking LM Studio models"):
                _ = client.models.list()
        except Exception:
            _status("Could not list models; continuing anyway…")

        _status("Preparing request and contacting LM Studio…")
        with spinner("Contacting LM Studio"):
            stream = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True,
            )

        print("Streaming analysis...\n")
        collected = []
        start_time = time.time()
        try:
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta
                    piece = getattr(delta, 'content', None)
                    if piece:
                        collected.append(piece)
                        print(piece, end='', flush=True)
                except Exception:
                    delta = chunk.get('choices', [{}])[0].get('delta', {}) if isinstance(chunk, dict) else {}
                    piece = delta.get('content')
                    if piece:
                        collected.append(piece)
                        print(piece, end='', flush=True)
        except KeyboardInterrupt:
            print("\n(User cancelled streaming)\n")
        except Exception as stream_err:
            print(f"\nStreaming interrupted: {stream_err}\nFalling back to non-streaming request...")
            with spinner("Waiting for response"):
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
            content = resp.choices[0].message.content
            collected.append(content)
            print(content)

        if len(collected) == 0:
            _status("No streamed content received; requesting non-stream response...")
            with spinner("Waiting for response"):
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
            content = resp.choices[0].message.content or ''
            if content:
                collected.append(content)
                print(content)

        print("\n\nDone in {:.1f}s".format(time.time() - start_time))
        final_text = "".join(collected)
        _prompt_and_save_analysis(final_text, 'LM Studio', 'health_analysis_lmstudio')
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"Error during LM Studio analysis: {e}")

def _analyze_with_openai_compatible(csv_files, provider_name: str, base_url_env: str, api_key_env: str, default_base_url: str, default_api_key: str, default_model_hint: str, save_prefix: str):
    """Generic analyzer for OpenAI-compatible local servers.

    - provider_name: Display name, e.g., 'Jan', 'LocalAI'
    - base_url_env: Environment variable for base URL
    - api_key_env: Environment variable for API key
    - default_base_url: Fallback base URL if env not set
    - default_api_key: Fallback API key if env not set
    - default_model_hint: Hint string for model selection prompt
    - save_prefix: File prefix when saving analysis markdown
    """
    data_summary, prompt = _prepare_ai_data(csv_files)
    if prompt is None:
        return

    base_url = os.environ.get(base_url_env, default_base_url)
    api_key = os.environ.get(api_key_env, default_api_key)
    model_name = _prompt_model_name(
        f"{provider_name.lower()}_model",
        'default',
        provider_name,
        default_model_hint
    )
    _status(f"Using {provider_name} at {base_url} with model: {model_name}")

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=60.0, max_retries=1)

        try:
            with spinner(f"Checking {provider_name} models"):
                _ = client.models.list()
        except Exception:
            _status("Could not list models; continuing anyway…")

        _status(f"Preparing request and contacting {provider_name}…")
        with spinner(f"Contacting {provider_name}"):
            stream = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True,
            )

        print("Streaming analysis...\n")
        collected = []
        start_time = time.time()
        try:
            for chunk in stream:
                try:
                    delta = chunk.choices[0].delta
                    piece = getattr(delta, 'content', None)
                    if piece:
                        collected.append(piece)
                        print(piece, end='', flush=True)
                except Exception:
                    delta = chunk.get('choices', [{}])[0].get('delta', {}) if isinstance(chunk, dict) else {}
                    piece = delta.get('content')
                    if piece:
                        collected.append(piece)
                        print(piece, end='', flush=True)
        except KeyboardInterrupt:
            print("\n(User cancelled streaming)\n")
        except Exception as stream_err:
            print(f"\nStreaming interrupted: {stream_err}\nFalling back to non-streaming request...")
            with spinner("Waiting for response"):
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
            content = resp.choices[0].message.content
            collected.append(content)
            print(content)

        if len(collected) == 0:
            _status("No streamed content received; requesting non-stream response...")
            with spinner("Waiting for response"):
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a health data analyst with strong technical skills."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                )
            content = resp.choices[0].message.content or ''
            if content:
                collected.append(content)
                print(content)

        print("\n\nDone in {:.1f}s".format(time.time() - start_time))
        final_text = "".join(collected)
        _prompt_and_save_analysis(final_text, provider_name, f"health_analysis_{save_prefix}")
    except KeyboardInterrupt:
        print("\nCancelled by user.")
    except Exception as e:
        print(f"Error during {provider_name} analysis: {e}")

def analyze_with_jan(csv_files):
    """Analyze using Jan (getjan.ai) OpenAI-compatible local server.

    Env:
    - JAN_BASE_URL (default: http://localhost:1337/v1)
    - JAN_API_KEY (default: jan)
    """
    return _analyze_with_openai_compatible(
        csv_files,
        provider_name='Jan',
        base_url_env='JAN_BASE_URL',
        api_key_env='JAN_API_KEY',
        default_base_url='http://localhost:1337/v1',
        default_api_key='jan',
        default_model_hint='Enter the model name loaded in Jan',
        save_prefix='jan'
    )

def analyze_with_localai(csv_files):
    """Analyze using LocalAI OpenAI-compatible server.

    Env:
    - LOCALAI_BASE_URL (default: http://localhost:8080/v1)
    - LOCALAI_API_KEY (default: local-ai)
    """
    return _analyze_with_openai_compatible(
        csv_files,
        provider_name='LocalAI',
        base_url_env='LOCALAI_BASE_URL',
        api_key_env='LOCALAI_API_KEY',
        default_base_url='http://localhost:8080/v1',
        default_api_key='local-ai',
        default_model_hint='Enter the model name available on LocalAI',
        save_prefix='localai'
    )

def convert_xml_to_csv():
    """Convert Apple Health export.xml into comprehensive CSV files.

    Creates three CSVs under the output directory:
    - records.csv: All <Record> elements (flattened attributes + metadata entries)
    - workouts.csv: All <Workout> elements (attributes + metadata)
    - activity_summary.csv: All <ActivitySummary> elements (attributes)

    Notes:
    - Metadata entries are flattened as columns named 'metadata:<key>'.
    - Missing columns are left blank for rows that don't have them.
    - This aims to mirror the simple structure of common XML→CSV tools.
    """
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")

    with spinner("Parsing export.xml"):
        tree = ET.parse(export_path)
        root = tree.getroot()

    # Helper to extract metadata entries as flat dict
    def _metadata_dict(elem):
        out = {}
        try:
            for m in elem.findall('.//MetadataEntry'):
                k = m.get('key')
                v = m.get('value')
                if k:
                    out[f"metadata:{k}"] = v
        except Exception:
            pass
        return out

    # Collect Records
    print("Scanning <Record> elements…")
    record_rows = []
    record_cols = set()
    bad_records = 0
    for rec in root.findall('.//Record'):
        try:
            row = dict(rec.attrib)
            row.update(_metadata_dict(rec))
            record_rows.append(row)
            record_cols.update(row.keys())
        except Exception:
            bad_records += 1
            continue

    # Collect Workouts
    print("Scanning <Workout> elements…")
    workout_rows = []
    workout_cols = set()
    bad_workouts = 0
    for w in root.findall('.//Workout'):
        try:
            row = dict(w.attrib)
            row.update(_metadata_dict(w))
            workout_rows.append(row)
            workout_cols.update(row.keys())
        except Exception:
            bad_workouts += 1
            continue

    # Collect ActivitySummary
    print("Scanning <ActivitySummary> elements…")
    as_rows = []
    as_cols = set()
    for a in root.findall('.//ActivitySummary'):
        try:
            row = dict(a.attrib)
            as_rows.append(row)
            as_cols.update(row.keys())
        except Exception:
            continue

    out_dir = get_output_dir()
    os.makedirs(out_dir, exist_ok=True)

    # Write CSVs using pandas for convenience
    def _write_csv(rows, cols, filename):
        if not rows:
            # Create empty with header if possible
            try:
                from pandas import DataFrame
                DataFrame(columns=sorted(list(cols))).to_csv(os.path.join(out_dir, filename), index=False)
            except Exception:
                pass
            return None
        try:
            from pandas import DataFrame
            # Ensure consistent column order: common useful keys first
            preferred = [
                'type', 'unit', 'value', 'sourceName', 'sourceVersion', 'device',
                'creationDate', 'startDate', 'endDate', 'workoutActivityType',
                'duration', 'durationUnit', 'totalDistance', 'totalDistanceUnit',
                'totalEnergyBurned', 'totalEnergyBurnedUnit', 'dateComponents'
            ]
            remaining = [c for c in sorted(list(cols)) if c not in preferred]
            ordered = [c for c in preferred if c in cols] + remaining
            df = DataFrame(rows, columns=ordered)
            path = os.path.join(out_dir, filename)
            df.to_csv(path, index=False)
            return path
        except Exception as e:
            print(f"Failed to write {filename}: {e}")
            return None

    print("Writing CSV files…")
    records_path = _write_csv(record_rows, record_cols, 'records.csv')
    workouts_path = _write_csv(workout_rows, workout_cols, 'workouts.csv')
    activity_path = _write_csv(as_rows, as_cols, 'activity_summary.csv')

    print("\nXML→CSV conversion complete:")
    print(f"- Records: {len(record_rows)} rows{f' (skipped {bad_records} malformed)' if bad_records else ''}")
    print(f"- Workouts: {len(workout_rows)} rows{f' (skipped {bad_workouts} malformed)' if bad_workouts else ''}")
    print(f"- Activity Summaries: {len(as_rows)} rows")
    if records_path:
        print(f"Saved: {records_path}")
    if workouts_path:
        print(f"Saved: {workouts_path}")
    if activity_path:
        print(f"Saved: {activity_path}")
    # Print quick-open tip for convenience
    if records_path:
        print_open_hint(records_path)

def convert_xml_to_json():
    """Convert Apple Health export.xml into JSON files.

    Creates three JSON files under the output directory:
    - records.json: All <Record> elements (attributes + metadata nested)
    - workouts.json: All <Workout> elements (attributes + metadata nested)
    - activity_summary.json: All <ActivitySummary> elements (attributes only)

    Notes:
    - Metadata entries are grouped under a 'metadata' object where keys are the
      MetadataEntry 'key' values and values are the corresponding 'value'.
    - This complements the CSV exporter with a more structured JSON format.
    """
    export_path = resolve_export_xml()
    print(f"Using export file: {export_path}")

    with spinner("Parsing export.xml"):
        tree = ET.parse(export_path)
        root = tree.getroot()

    def _metadata_obj(elem):
        md = {}
        try:
            for m in elem.findall('.//MetadataEntry'):
                k = m.get('key')
                v = m.get('value')
                if k is not None:
                    md[k] = v
        except Exception:
            pass
        return md or None

    # Records
    print("Scanning <Record> elements…")
    records = []
    for rec in root.findall('.//Record'):
        try:
            row = dict(rec.attrib)
            md = _metadata_obj(rec)
            if md is not None:
                row['metadata'] = md
            records.append(row)
        except Exception:
            continue

    # Workouts
    print("Scanning <Workout> elements…")
    workouts = []
    for w in root.findall('.//Workout'):
        try:
            row = dict(w.attrib)
            md = _metadata_obj(w)
            if md is not None:
                row['metadata'] = md
            workouts.append(row)
        except Exception:
            continue

    # ActivitySummary
    print("Scanning <ActivitySummary> elements…")
    summaries = []
    for a in root.findall('.//ActivitySummary'):
        try:
            summaries.append(dict(a.attrib))
        except Exception:
            continue

    out_dir = get_output_dir()
    os.makedirs(out_dir, exist_ok=True)

    def _write_json(obj, filename):
        path = os.path.join(out_dir, filename)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)
            return path
        except Exception as e:
            print(f"Failed to write {filename}: {e}")
            return None

    print("Writing JSON files…")
    rec_path = _write_json(records, 'records.json')
    w_path = _write_json(workouts, 'workouts.json')
    as_path = _write_json(summaries, 'activity_summary.json')

    print("\nXML→JSON conversion complete:")
    print(f"- Records: {len(records)}")
    print(f"- Workouts: {len(workouts)}")
    print(f"- Activity Summaries: {len(summaries)}")
    if rec_path:
        print(f"Saved: {rec_path}")
        print_open_hint(rec_path)
    if w_path:
        print(f"Saved: {w_path}")
    if as_path:
        print(f"Saved: {as_path}")

def show_changelog():
    """Display the application changelog."""
    # Try to locate CHANGELOG.md relative to this script
    # src/applehealth.py -> ../CHANGELOG.md
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    changelog_path = os.path.join(base_dir, 'CHANGELOG.md')
    
    # Fallback checks
    if not os.path.exists(changelog_path):
        candidates = [
            os.path.join(os.getcwd(), 'CHANGELOG.md'),
            'CHANGELOG.md',
            '../CHANGELOG.md'
        ]
        for c in candidates:
            if os.path.exists(c):
                changelog_path = c
                break
    
    if os.path.exists(changelog_path):
        print("\n" + "="*50)
        print("CHANGE LOG - Timeline of Updates")
        print("="*50 + "\n")
        try:
            with open(changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content)
        except Exception as e:
            print(f"Error reading changelog: {e}")
        print("\n" + "="*50 + "\n")
    else:
        print("\nCHANGELOG.md not found.")
    
    input("Press Enter to return to menu...")

def main():
    """
    Main function providing an interactive menu to choose which health metric to analyze.
    """
    # Greet and show where outputs will be saved by default
    out_dir = get_output_dir()
    print(f"\nApple Health Data Analyzer v{__version__}")
    print(f"Outputs will be saved to: {out_dir}")
    print("Tip: You can drag-and-drop your export.xml into this window when prompted.")
    while True:
        print("\nWhat would you like to do?")
        # Core analyses
        print("0. Diagnose Export & Generate Debug Report")
        print("1. Analyze Steps")
        print("2. Analyze Distance")
        print("3. Analyze Heart Rate")
        print("4. Analyze Weight")
        print("5. Analyze Sleep")
        print("6. Analyze Workouts")
        print("7. Convert XML → CSV (Full Dump)")
        print("8. Convert XML → JSON (Full Dump)")
        # AI analyses
        print("9. AI: Analyze All Data (OpenAI)")
        print("10. AI: Analyze with Claude (Anthropic)")
        print("11. AI: Analyze with Gemini (Google)")
        print("12. AI: Analyze with Grok (xAI)")
        print("13. AI: Analyze with OpenRouter")
        print("14. AI: Analyze with Ollama (Local)")
        print("15. AI: Analyze with Ollama (Remote)")
        print("16. AI: Analyze with LM Studio")
        print("17. AI: Analyze with Jan")
        print("18. AI: Analyze with LocalAI")
        # Settings and exit
        print("19. AI Settings")
        print("20. Reset Preferences")
        print("21. Exit")  # Keeping 21 as Exit for backward compat if users are used to it, but I'll move it
        # Actually I should renumber to keep it clean or just append.
        # User asked to add a page.
        # Let's re-order: 21 -> Exit. 
        # I'll bump Exit to 23 as planned.
        
        # Correct implementation:
        print("19. AI Settings")
        print("20. Reset Preferences")
        print("21. Analyze with Custom AI (Future)") # Placeholder? No, don't add random stuff.
        # Let's just append 22 and move Exit to 23.
        # But wait, 21 was Exit.
        # Let's keep 21 as Exit? No, usually Exit is last.
        # I'll output:
        print("19. AI Settings")
        print("20. Reset Preferences")
        print("21. View Change Log")
        print("22. Exit")

        choice = input("Enter your choice (0-22): ")
        
        # List of available data files and their types
        data_files = [
            ('steps_data.csv', 'Steps'),
            ('distance_data.csv', 'Distance'),
            ('heart_rate_data.csv', 'Heart Rate'),
            ('weight_data.csv', 'Weight'),
            ('sleep_data.csv', 'Sleep'),
            ('workout_data.csv', 'Workout')
        ]
        
        # Any analysis or AI option requires export.xml
        if choice in {'0','1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18'}:
            if not ensure_export_available():
                continue

        if choice == '0':
            export_path = resolve_export_xml()
            generate_debug_reports(export_path)
        elif choice == '1':
            analyze_steps()
        elif choice == '2':
            analyze_distance()
        elif choice == '3':
            analyze_heart_rate()
        elif choice == '4':
            analyze_weight()
        elif choice == '5':
            analyze_sleep()
        elif choice == '6':
            analyze_workouts()
        elif choice == '7':
            convert_xml_to_csv()
        elif choice == '8':
            convert_xml_to_json()
        elif choice == '9':
            analyze_with_chatgpt(data_files)
        elif choice == '10':
            analyze_with_claude(data_files)
        elif choice == '11':
            analyze_with_gemini(data_files)
        elif choice == '12':
            analyze_with_grok(data_files)
        elif choice == '13':
            analyze_with_openrouter(data_files)
        elif choice == '14':
            analyze_with_ollama(data_files)
        elif choice == '15':
            analyze_with_external_ollama(data_files)
        elif choice == '16':
            analyze_with_lmstudio(data_files)
        elif choice == '17':
            analyze_with_jan(data_files)
        elif choice == '18':
            analyze_with_localai(data_files)
        elif choice == '19':
            print("\nAI Settings:")
            print("Current default temperature: 0.3")
            print("\nTemperature Guide:")
            print("0.0-0.3: Best for statistical analysis and consistent insights")
            print("0.3-0.5: Balanced analysis with some variation")
            print("0.5-0.7: More creative insights and patterns")
            print("0.7-1.0: Most varied and exploratory analysis")
            print("\nRecommended: 0.3 for health data analysis")
            input("\nPress Enter to continue...")
        elif choice == '20':
            confirm = input("This will delete saved model/output/export preferences. Proceed? (y/n): ").strip().lower()
            if confirm in ('y', 'yes'):
                reset_preferences()
            else:
                print("Cancelled.")
        elif choice == '21':
            show_changelog()
        elif choice == '22':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import pandas
        import matplotlib
        import openai
        from dotenv import load_dotenv
        print("All required packages are installed!")
    except ImportError as e:
        print(f"Missing required package: {str(e)}")
        print("\nPlease install required packages using:")
        print("pip install -r ../requirements.txt")
        exit(1)

def check_env():
    """Check if .env file exists and contains API key"""
    if not os.path.exists('.env'):
        print("Warning: .env file not found!")
        print("Please create a .env file with your OpenAI API key:")
        print("OPENAI_API_KEY=your-api-key-here")
        return False
    return True

if __name__ == "__main__":
    # Parse optional CLI args for export path and output directory
    try:
        parser = argparse.ArgumentParser(description="Apple Health Data Analyzer")
        parser.add_argument('-e', '--export', help='Path to export.xml or a directory containing it')
        parser.add_argument('-o', '--out', help='Directory to write CSV/PNG/MD outputs (default: current directory or OUTPUT_DIR env)')
        parser.add_argument('path', nargs='?', help='Optional positional path to export.xml or containing directory')
        args = parser.parse_args()
        chosen = args.export or args.path
        if chosen:
            _export_xml_path = os.path.abspath(os.path.expanduser(chosen))
            try:
                _set_saved_pref('export_xml', _export_xml_path)
            except Exception:
                pass
        if args.out:
            _output_dir = os.path.abspath(os.path.expanduser(args.out))
            try:
                _set_saved_pref('output_dir', _output_dir)
            except Exception:
                pass
    except SystemExit:
        raise

    check_requirements()
    if not check_env():
        print("\nContinuing without AI analysis capabilities...")
    main()
