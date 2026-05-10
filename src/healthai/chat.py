"""Route chat input to the configured AI model via litellm."""
from __future__ import annotations
import os
import json

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


def chat(user_message: str) -> None:
    """Send user_message to the configured litellm model with health CSV context."""
    try:
        import litellm
    except ImportError:
        print("  litellm not installed. Run: pip install litellm")
        return

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

    print(f"\n  {_D}Thinking…{_X}")
    try:
        extra: dict = {}
        if model.startswith("ollama"):
            extra["api_base"] = prefs.get("ollama_host", "http://localhost:11434")

        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_message},
            ],
            **extra,
        )
        answer = response.choices[0].message.content or ""
        print(f"\n  {_G}●{_X} {answer.strip()}\n")
    except Exception as e:
        print(f"\n  {_Y}Error:{_X} {e}\n  Run /settings to check your model and API key.\n")
