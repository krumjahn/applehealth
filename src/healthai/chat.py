"""Route chat input to the configured AI provider."""
from __future__ import annotations
import os
import json


ALL_DATA_FILES = [
    ("steps_data.csv",     "Steps"),
    ("distance_data.csv",  "Distance"),
    ("heart_rate_data.csv","Heart Rate"),
    ("weight_data.csv",    "Weight"),
    ("sleep_data.csv",     "Sleep"),
    ("workout_data.csv",   "Workout"),
]

PROVIDER_FUNCTION_MAP = {
    "openai":        "analyze_with_chatgpt",
    "claude":        "analyze_with_claude",
    "gemini":        "analyze_with_gemini",
    "grok":          "analyze_with_grok",
    "openrouter":    "analyze_with_openrouter",
    "ollama":        "analyze_with_ollama",
    "ollama_remote": "analyze_with_external_ollama",
    "lmstudio":      "analyze_with_lmstudio",
    "jan":           "analyze_with_jan",
    "localai":       "analyze_with_localai",
    "msty":          "analyze_with_msty",
    "litellm":       "analyze_with_litellm",
}

PROVIDER_LABELS = {
    "openai":        "OpenAI",
    "claude":        "Claude",
    "gemini":        "Gemini",
    "grok":          "Grok",
    "openrouter":    "OpenRouter",
    "ollama":        "Ollama",
    "ollama_remote": "Ollama (Remote)",
    "lmstudio":      "LM Studio",
    "jan":           "Jan",
    "localai":       "LocalAI",
    "msty":          "Msty",
    "litellm":       "LiteLLM",
}


def get_configured_provider() -> str:
    """Return provider id from prefs, defaulting to 'openai'."""
    try:
        path = os.path.join(os.path.expanduser("~"), ".applehealth", "ai_prefs.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f).get("default_provider", "openai")
    except Exception:
        pass
    return "openai"


def get_provider_label(provider_id: str) -> str:
    return PROVIDER_LABELS.get(provider_id, provider_id)


def chat(user_message: str) -> None:
    """Send user_message to the configured provider with all health CSV data as context."""
    import healthai.cli as _cli

    provider_id = get_configured_provider()
    fn_name = PROVIDER_FUNCTION_MAP.get(provider_id, "analyze_with_chatgpt")
    fn = getattr(_cli, fn_name, None)

    if fn is None:
        print(f"  Unknown provider '{provider_id}'. Run /settings to reconfigure.")
        return

    os.environ["HEALTHAI_USER_QUESTION"] = user_message
    try:
        fn(ALL_DATA_FILES)
    finally:
        os.environ.pop("HEALTHAI_USER_QUESTION", None)
