"""Route chat input to the configured AI model via litellm."""
from __future__ import annotations
import os
import json
import sys
import time
import threading

from healthai.models import MODELS

_MODEL_LABELS: dict[str, str] = {m[1]: m[2] for m in MODELS if m[1] != "__custom__"}

_PREFS_PATH = os.path.join(os.path.expanduser("~"), ".applehealth", "ai_prefs.json")

ALL_DATA_FILES = [
    ("steps_data.csv",      "Steps"),
    ("distance_data.csv",   "Distance"),
    ("heart_rate_data.csv", "Heart Rate"),
    ("weight_data.csv",     "Weight"),
    ("sleep_data.csv",      "Sleep"),
    ("workout_data.csv",    "Workout"),
]

_LEGACY_PROVIDER_MAP = {
    "openai":     "gpt-4o",
    "claude":     "claude-sonnet-4-20250514",
    "gemini":     "gemini/gemini-2.5-flash",
    "grok":       "xai/grok-3",
    "openrouter": "openrouter/openai/gpt-4o",
    "ollama":     "ollama_chat/llama3",
    "lmstudio":   "lmstudio/local",
    "litellm":    "gpt-4o",
}


def _load_prefs() -> dict:
    try:
        if os.path.exists(_PREFS_PATH):
            with open(_PREFS_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def get_configured_model() -> str:
    """Return the full litellm model string from prefs, defaulting to gpt-4o."""
    prefs = _load_prefs()
    model = prefs.get("default_model") or prefs.get("default_provider", "gpt-4o")
    return _LEGACY_PROVIDER_MAP.get(model, model)


# Backwards-compat alias — cli.py calls this name
get_configured_provider = get_configured_model


def get_model_label(model_str: str) -> str:
    return _MODEL_LABELS.get(model_str, model_str)


# Backwards-compat alias
get_provider_label = get_model_label


def _build_context(output_dir: str) -> str:
    """Read available CSV files and return them as a single context string."""
    parts = []
    for filename, label in ALL_DATA_FILES:
        path = os.path.join(output_dir, filename)
        if os.path.exists(path):
            try:
                with open(path) as f:
                    content = f.read(8000)
                parts.append(f"=== {label} ({filename}) ===\n{content}")
            except Exception:
                pass
    return "\n\n".join(parts) if parts else ""


_THINKING_PHRASES = [
    "Thinking…",
    "Analyzing your data…",
    "Crunching the numbers…",
    "Reading your health records…",
    "Almost there…",
    "Connecting the dots…",
]
_SPINNER_FRAMES = ["⠋", "⠙", "⠚", "⠞", "⠖", "⠦", "⠴", "⠲", "⠳", "⠓"]


def _thinking_spinner(stop_event: threading.Event) -> None:
    """Animated thinking indicator — runs in a background thread."""
    from healthai.ui import _D, _X
    start = time.time()
    i = 0
    phrase_idx = 0
    phrase_change = 3.0  # seconds between phrase rotations
    try:
        while not stop_event.is_set():
            elapsed = time.time() - start
            frame = _SPINNER_FRAMES[i % len(_SPINNER_FRAMES)]
            phrase = _THINKING_PHRASES[phrase_idx % len(_THINKING_PHRASES)]
            line = f"\r  {_D}{frame}  {phrase}  {elapsed:.1f}s{_X}   "
            sys.stdout.write(line)
            sys.stdout.flush()
            if elapsed >= phrase_change * (phrase_idx + 1):
                phrase_idx += 1
            i += 1
            time.sleep(0.08)
    except Exception:
        pass
    # clear the line
    sys.stdout.write("\r" + " " * 72 + "\r")
    sys.stdout.flush()


def chat(user_message: str) -> dict:
    """Send user_message to the configured litellm model with health CSV context.

    Returns a stats dict: {"elapsed": float, "tokens_in": int, "tokens_out": int}.
    """
    try:
        import litellm
    except ImportError:
        print("  litellm not installed. Run: pip install litellm")
        return {"elapsed": 0.0, "tokens_in": 0, "tokens_out": 0}

    from healthai.ui import _C, _D, _G, _X, _Y

    model = get_configured_model()
    prefs = _load_prefs()
    output_dir = prefs.get("output_dir", os.path.join(os.path.expanduser("~"), "healthai_output"))

    # Inject any saved API key for this model into the environment
    for _grp, _mstr, _disp, _needs_key, _key_env in MODELS:
        if _mstr == model and _key_env and not os.environ.get(_key_env):
            saved = prefs.get(_key_env, "")
            if saved:
                os.environ[_key_env] = saved
            break

    context = _build_context(output_dir)
    system_prompt = (
        "You are a personal health analyst with access to the user's Apple Health data. "
        "Answer questions using the data provided. Be specific — cite numbers and dates. "
        "If data is insufficient, say so clearly.\n\n"
        + (f"Health data:\n{context}" if context else "No health data found. Ask the user to run /csv first.")
    )

    print()
    stop = threading.Event()
    spinner_thread = threading.Thread(target=_thinking_spinner, args=(stop,), daemon=True)
    spinner_thread.start()

    t0 = time.time()
    try:
        extra: dict = {}
        if model.startswith("ollama"):
            extra["api_base"] = prefs.get("ollama_host", "http://localhost:11434")
        if prefs.get("openai_compat_base") and model.startswith("openai/"):
            extra["api_base"] = prefs["openai_compat_base"]

        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            **extra,
        )
        elapsed = time.time() - t0
        stop.set()
        spinner_thread.join()

        answer = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        tokens_in  = getattr(usage, "prompt_tokens",     0) if usage else 0
        tokens_out = getattr(usage, "completion_tokens", 0) if usage else 0

        print(f"  {_G}●{_X} {answer.strip()}\n")
        return {"elapsed": elapsed, "tokens_in": tokens_in, "tokens_out": tokens_out}

    except Exception as e:
        elapsed = time.time() - t0
        stop.set()
        spinner_thread.join()
        print(f"  {_Y}Error:{_X} {e}\n  Run /settings to check your model and API key.\n")
        return {"elapsed": elapsed, "tokens_in": 0, "tokens_out": 0}
