"""Curated LiteLLM model catalogue and interactive model picker."""
from __future__ import annotations

from healthai.ui import _C, _W, _D, _G, _Y, _X

# Each entry: (provider_group, litellm_string, display_name, needs_key, key_env)
MODELS: list[tuple[str, str, str, bool, str | None]] = [
    ("OpenAI",          "gpt-4o",                                            "GPT-4o — flagship",              True,  "OPENAI_API_KEY"),
    ("OpenAI",          "gpt-4o-mini",                                       "GPT-4o Mini — fast & cheap",     True,  "OPENAI_API_KEY"),
    ("OpenAI",          "o3-mini",                                           "o3-mini — reasoning",            True,  "OPENAI_API_KEY"),
    ("OpenAI",          "o4-mini",                                           "o4-mini — latest reasoning",     True,  "OPENAI_API_KEY"),
    ("Anthropic",       "claude-opus-4-20250514",                            "Claude Opus 4 — most capable",   True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-sonnet-4-20250514",                          "Claude Sonnet 4 — balanced",     True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-3-7-sonnet-20250219",                        "Claude 3.7 Sonnet — reasoning",  True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-3-5-sonnet-20241022",                        "Claude 3.5 Sonnet",              True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-3-haiku-20240307",                           "Claude 3 Haiku — fast/cheap",    True,  "ANTHROPIC_API_KEY"),
    ("Google Gemini",   "gemini/gemini-2.5-pro",                             "Gemini 2.5 Pro — most capable",  True,  "GEMINI_API_KEY"),
    ("Google Gemini",   "gemini/gemini-2.5-flash",                           "Gemini 2.5 Flash — fast",        True,  "GEMINI_API_KEY"),
    ("Google Gemini",   "gemini/gemini-2.0-flash",                           "Gemini 2.0 Flash — stable",      True,  "GEMINI_API_KEY"),
    ("Google Gemini",   "gemini/gemini-1.5-pro-latest",                      "Gemini 1.5 Pro — long context",  True,  "GEMINI_API_KEY"),
    ("Groq",            "groq/llama-3.3-70b-versatile",                      "Llama 3.3 70B — very fast",      True,  "GROQ_API_KEY"),
    ("Groq",            "groq/llama-3.1-8b-instant",                         "Llama 3.1 8B — ultra-fast",      True,  "GROQ_API_KEY"),
    ("Groq",            "groq/meta-llama/llama-4-scout-17b-16e-instruct",    "Llama 4 Scout",                  True,  "GROQ_API_KEY"),
    ("Groq",            "groq/meta-llama/llama-4-maverick-17b-128e-instruct","Llama 4 Maverick",               True,  "GROQ_API_KEY"),
    ("Mistral",         "mistral/mistral-large-latest",                      "Mistral Large — flagship",       True,  "MISTRAL_API_KEY"),
    ("Mistral",         "mistral/mistral-small-latest",                      "Mistral Small — cheap",          True,  "MISTRAL_API_KEY"),
    ("Mistral",         "mistral/codestral-latest",                          "Codestral — code specialist",    True,  "MISTRAL_API_KEY"),
    ("Mistral",         "mistral/magistral-medium-2506",                     "Magistral Medium — reasoning",   True,  "MISTRAL_API_KEY"),
    ("DeepSeek",        "deepseek/deepseek-chat",                            "DeepSeek Chat (V3)",             True,  "DEEPSEEK_API_KEY"),
    ("DeepSeek",        "deepseek/deepseek-reasoner",                        "DeepSeek R1 — reasoning",        True,  "DEEPSEEK_API_KEY"),
    ("xAI",             "xai/grok-4",                                        "Grok 4 — flagship",              True,  "XAI_API_KEY"),
    ("xAI",             "xai/grok-3",                                        "Grok 3",                         True,  "XAI_API_KEY"),
    ("xAI",             "xai/grok-3-mini",                                   "Grok 3 Mini",                    True,  "XAI_API_KEY"),
    ("Perplexity",      "perplexity/sonar-pro",                              "Sonar Pro — search+AI",          True,  "PERPLEXITYAI_API_KEY"),
    ("Perplexity",      "perplexity/sonar",                                  "Sonar — fast search",            True,  "PERPLEXITYAI_API_KEY"),
    ("Perplexity",      "perplexity/sonar-reasoning-pro",                    "Sonar Reasoning Pro",            True,  "PERPLEXITYAI_API_KEY"),
    ("Cohere",          "command-a-03-2025",                                 "Command A — flagship",           True,  "COHERE_API_KEY"),
    ("Cohere",          "command-r-plus-08-2024",                            "Command R+ — strong RAG",        True,  "COHERE_API_KEY"),
    ("OpenRouter",      "openrouter/openai/gpt-4o",                          "GPT-4o via OpenRouter",          True,  "OPENROUTER_API_KEY"),
    ("OpenRouter",      "openrouter/anthropic/claude-3.5-sonnet",            "Claude 3.5 via OpenRouter",      True,  "OPENROUTER_API_KEY"),
    ("OpenRouter",      "openrouter/meta-llama/llama-3.3-70b-instruct",      "Llama 3.3 70B via OpenRouter",   True,  "OPENROUTER_API_KEY"),
    ("Ollama (local)",  "ollama_chat/llama3",                                "Llama 3 — local, free",          False, None),
    ("Ollama (local)",  "ollama_chat/mistral",                               "Mistral 7B — local, free",       False, None),
    ("Ollama (local)",  "ollama_chat/codellama",                             "Code Llama — local, free",       False, None),
    ("Ollama (local)",  "ollama_chat/deepseek-r1",                           "DeepSeek R1 — local, free",      False, None),
    ("Ollama (local)",  "ollama_chat/gemma2",                                "Gemma 2 — local, free",          False, None),
    ("Custom",          "__custom__",                                        "Enter a custom model string…",   False, None),
]

# Unique ordered group names
GROUPS: list[str] = list(dict.fromkeys(m[0] for m in MODELS))


def pick_model(current_model: str = "") -> tuple[str, str | None]:
    """
    Interactive numbered model picker grouped by provider.

    Returns (litellm_model_string, key_env_var_or_None).
    Returns ("", None) if the user cancels.
    If user picks Custom, prompts for a free-form string.
    """
    print(f"\n  {_W}Choose your AI model{_X}  {_D}(type a number or press Enter to keep current){_X}\n")

    num = 1
    index_map: dict[int, tuple] = {}
    current_num: int | None = None

    for group in GROUPS:
        group_entries = [m for m in MODELS if m[0] == group]
        bar = "─" * max(1, 40 - len(group))
        print(f"  {_D}── {group} {bar}{_X}")
        for entry in group_entries:
            _grp, model_str, display, needs_key, key_env = entry
            free = f"  {_G}free{_X}" if not needs_key else ""
            marker = f"  {_G}← current{_X}" if model_str == current_model else ""
            if model_str == current_model:
                current_num = num
            print(f"  {_D}{num:>3}.{_X}  {display}{free}{marker}")
            index_map[num] = entry
            num += 1
        print()

    default_hint = str(current_num) if current_num else ""
    try:
        raw = input(f"  {_C}›{_X} Enter number{f' [{default_hint}]' if default_hint else ''}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return ("", None)

    if not raw and current_model:
        return (current_model, None)

    if not raw.isdigit() or int(raw) not in index_map:
        print(f"  {_Y}Invalid — keeping current model{_X}")
        return (current_model, None)

    chosen = index_map[int(raw)]
    _grp, model_str, display, needs_key, key_env = chosen

    if model_str == "__custom__":
        try:
            custom = input(f"  {_C}›{_X} Enter litellm model string (e.g. groq/llama3): ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return ("", None)
        if not custom:
            return (current_model, None)
        return (custom, None)

    return (model_str, key_env)
