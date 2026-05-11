"""LiteLLM model catalogue and interactive fuzzy-search model picker.

The MODELS list is built dynamically from litellm.model_cost at import time so
it stays current whenever litellm is upgraded.  A small curated FEATURED block
is pinned at the top for quick access; everything else comes from the live dict.
"""
from __future__ import annotations

import os
import json

from healthai.ui import _C, _W, _D, _G, _Y, _X

# ── Curated featured models (always shown first) ─────────────────────────────
# (group, litellm_string, display_name, needs_key, key_env)
_FEATURED: list[tuple[str, str, str, bool, str | None]] = [
    ("★ Featured",  "gpt-5.5",                        "GPT-5.5 — latest OpenAI",            True,  "OPENAI_API_KEY"),
    ("★ Featured",  "gpt-4.1",                        "GPT-4.1 — stable flagship",          True,  "OPENAI_API_KEY"),
    ("★ Featured",  "o4-mini",                        "o4-mini — reasoning",                True,  "OPENAI_API_KEY"),
    ("★ Featured",  "codex-mini-latest",               "Codex Mini — agentic coding",        True,  "OPENAI_API_KEY"),
    ("★ Featured",  "claude-opus-4-7-20260416",       "Claude Opus 4.7 — most capable",     True,  "ANTHROPIC_API_KEY"),
    ("★ Featured",  "claude-opus-4-6-20260205",       "Claude Opus 4.6",                    True,  "ANTHROPIC_API_KEY"),
    ("★ Featured",  "claude-sonnet-4-5-20250929",     "Claude Sonnet 4.5 — balanced",       True,  "ANTHROPIC_API_KEY"),
    ("★ Featured",  "gemini/gemini-2.5-pro",          "Gemini 2.5 Pro",                     True,  "GEMINI_API_KEY"),
    ("★ Featured",  "gemini/gemini-2.5-flash-preview-04-17", "Gemini 2.5 Flash — fast",     True,  "GEMINI_API_KEY"),
    ("★ Featured",  "xai/grok-4-latest",              "Grok 4 — xAI flagship",              True,  "XAI_API_KEY"),
    ("★ Featured",  "deepseek/deepseek-chat",         "DeepSeek V3 — cheap + smart",        True,  "DEEPSEEK_API_KEY"),
    ("★ Featured",  "groq/llama-3.3-70b-versatile",  "Llama 3.3 70B via Groq — very fast", True,  "GROQ_API_KEY"),
    ("★ Featured",  "ollama_chat/llama3.1",           "Llama 3.1 via Ollama — local/free",  False, None),
]

# ── Sentinel entries (local servers + custom) ─────────────────────────────────
_SENTINELS: list[tuple[str, str, str, bool, str | None]] = [
    # named local servers
    ("Local Servers", "__ollama__",   "Ollama — any model (localhost:11434)",    False, None),
    ("Local Servers", "__jan__",      "Jan — local server (localhost:1337)",     False, None),
    ("Local Servers", "__lmstudio__", "LM Studio (localhost:1234)",              False, None),
    ("Local Servers", "__llamacpp__", "llama.cpp server (localhost:8080)",       False, None),
    ("Local Servers", "__gpt4all__",  "GPT4All (localhost:4891)",                False, None),
    ("Local Servers", "__openai_compat__", "Custom OpenAI-compatible endpoint",  False, None),
    # fully custom
    ("Custom",        "__custom__",   "Enter any litellm model string…",         False, None),
]

# Providers we surface as top-level groups from litellm.model_cost
_PROVIDER_LABEL: dict[str, str] = {
    "openai":        "OpenAI",
    "anthropic":     "Anthropic",
    "gemini":        "Google Gemini",
    "xai":           "xAI (Grok)",
    "groq":          "Groq",
    "deepseek":      "DeepSeek",
    "mistral":       "Mistral",
    "perplexity":    "Perplexity",
    "cohere_chat":   "Cohere",
    "moonshot":      "Kimi (Moonshot)",
    "minimax":       "MiniMax",
    "dashscope":     "Alibaba Qwen",
    "cerebras":      "Cerebras",
    "sambanova":     "SambaNova",
    "fireworks_ai":  "Fireworks AI",
    "nvidia_nim":    "NVIDIA NIM",
    "ai21":          "AI21",
    "nebius":        "Nebius",
    "zai":           "Z.AI (Zhipu)",
    "together_ai":   "Together AI",
    "deepinfra":     "DeepInfra",
    "openrouter":    "OpenRouter",
    "bedrock":       "AWS Bedrock",
    "ollama":        "Ollama (local)",
    "vertex_ai":     "Google Vertex AI",
}

_PROVIDER_KEY: dict[str, str] = {
    "openai":       "OPENAI_API_KEY",
    "anthropic":    "ANTHROPIC_API_KEY",
    "gemini":       "GEMINI_API_KEY",
    "xai":          "XAI_API_KEY",
    "groq":         "GROQ_API_KEY",
    "deepseek":     "DEEPSEEK_API_KEY",
    "mistral":      "MISTRAL_API_KEY",
    "perplexity":   "PERPLEXITYAI_API_KEY",
    "cohere_chat":  "COHERE_API_KEY",
    "moonshot":     "MOONSHOT_API_KEY",
    "minimax":      "MINIMAX_API_KEY",
    "dashscope":    "DASHSCOPE_API_KEY",
    "cerebras":     "CEREBRAS_API_KEY",
    "sambanova":    "SAMBANOVA_API_KEY",
    "fireworks_ai": "FIREWORKS_AI_API_KEY",
    "nvidia_nim":   "NVIDIA_NIM_API_KEY",
    "ai21":         "AI21_API_KEY",
    "nebius":       "NEBIUS_API_KEY",
    "zai":          "ZAI_API_KEY",
    "together_ai":  "TOGETHERAI_API_KEY",
    "deepinfra":    "DEEPINFRA_API_KEY",
    "openrouter":   "OPENROUTER_API_KEY",
    "bedrock":      "AWS_ACCESS_KEY_ID",
    "vertex_ai":    "GOOGLE_APPLICATION_CREDENTIALS",
}

# Featured model strings — skip these when building the "all" section to avoid dups
_FEATURED_STRINGS: frozenset[str] = frozenset(m[1] for m in _FEATURED)

# Model string prefixes/substrings to exclude from the dynamic list (noisy/irrelevant)
_EXCLUDE_PREFIXES = (
    "ft:",          # fine-tune templates
    "1024-x-",      # image size keys (bedrock image gen)
    "512-x-",
    "256-x-",
    "openai/container",
    "sample_spec",
)
_EXCLUDE_MODES = {"image_generation", "embedding", "audio_transcription",
                  "audio_speech", "moderation", "rerank", "search"}


def _build_models() -> list[tuple[str, str, str, bool, str | None]]:
    """Build the full model list: featured first, then live litellm catalogue."""
    try:
        import litellm  # noqa: PLC0415
        cost_map: dict = litellm.model_cost
    except Exception:
        return _FEATURED + _SENTINELS

    # Group chat-mode models by provider label
    grouped: dict[str, list[tuple[str, str, str, bool, str | None]]] = {}
    for model_str, info in cost_map.items():
        provider = info.get("litellm_provider", "")
        if provider not in _PROVIDER_LABEL:
            continue
        mode = info.get("mode", "chat")
        if mode in _EXCLUDE_MODES:
            continue
        if any(model_str.startswith(p) or model_str == p for p in _EXCLUDE_PREFIXES):
            continue
        if model_str in _FEATURED_STRINGS:
            continue

        group = _PROVIDER_LABEL[provider]
        key_env = _PROVIDER_KEY.get(provider)
        needs_key = key_env is not None and provider != "ollama"

        entry = (group, model_str, model_str, needs_key, key_env)
        grouped.setdefault(group, []).append(entry)

    # Sort within each group alphabetically, then sort groups by display order
    group_order = list(_PROVIDER_LABEL.values())
    all_entries: list[tuple[str, str, str, bool, str | None]] = []
    for group in group_order:
        if group in grouped:
            all_entries.extend(sorted(grouped[group], key=lambda e: e[1]))

    return _FEATURED + all_entries + _SENTINELS


# Build once at import time
MODELS: list[tuple[str, str, str, bool, str | None]] = _build_models()
GROUPS: list[str] = list(dict.fromkeys(m[0] for m in MODELS))


def _filter_models(query: str) -> list[tuple[str, str, str, bool, str | None]]:
    """Return models whose group+litellm_string+display all match every token."""
    if not query:
        return MODELS
    tokens = query.lower().split()
    results = []
    for entry in MODELS:
        group, model_str, display, _nk, _ke = entry
        haystack = f"{group} {model_str} {display}".lower()
        if all(t in haystack for t in tokens):
            results.append(entry)
    return results


def pick_model(current_model: str = "") -> tuple[str, str | None]:
    """Interactive fuzzy-search model picker.

    Returns (litellm_model_string, key_env_var_or_None).
    Returns ("", None) on cancel.
    """
    try:
        return _pick_model_pt(current_model)
    except Exception:
        return _pick_model_fallback(current_model)


def _pick_model_pt(current_model: str) -> tuple[str, str | None]:
    """prompt_toolkit full-screen fuzzy picker."""
    from prompt_toolkit import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.styles import Style

    style = Style.from_dict({
        "header":   "bold",
        "group":    "ansigray",
        "selected": "bold ansibrightcyan reverse",
        "model":    "",
        "meta":     "ansigray",
        "free":     "ansibrightgreen",
        "current":  "ansibrightgreen",
        "footer":   "ansigray",
        "hint":     "ansigray",
    })

    state: dict = {"query": "", "cursor": 0, "result": None, "done": False}

    def get_filtered() -> list[tuple[str, str, str, bool, str | None]]:
        return _filter_models(state["query"])

    def clamp_cursor(filtered: list) -> None:
        n = len(filtered)
        state["cursor"] = max(0, min(state["cursor"], n - 1)) if n else 0

    def render_list() -> list:
        filtered = get_filtered()
        clamp_cursor(filtered)
        total = len(MODELS)
        shown = len(filtered)

        lines: list = []
        lines.append(("class:header", "  Choose your AI model\n"))
        lines.append(("class:hint",   "  Type to search · ↑↓ navigate · Enter select · Esc cancel\n\n"))
        q = state["query"]
        lines.append(("",             "  search: "))
        lines.append(("class:model",  q))
        lines.append(("",             "█\n\n"))

        prev_group = None
        for i, entry in enumerate(filtered):
            group, model_str, display, needs_key, key_env = entry
            if group != prev_group:
                bar = "─" * max(1, 52 - len(group))
                lines.append(("class:group", f"  ── {group} {bar}\n"))
                prev_group = group

            is_selected = (i == state["cursor"])
            is_current  = (model_str == current_model)

            prefix   = "▸ " if is_selected else "  "
            free_tag = "  free" if not needs_key and model_str not in ("__ollama__", "__jan__",
                       "__lmstudio__", "__llamacpp__", "__gpt4all__", "__openai_compat__",
                       "__custom__") else ""
            curr_tag = "  ← current" if is_current else ""

            name_col = f"{display:<46}"
            cls = "class:selected" if is_selected else "class:model"
            lines.append((cls, f"  {prefix}{name_col}"))
            if free_tag:
                lines.append(("class:free", free_tag))
            if curr_tag:
                lines.append(("class:current", curr_tag))
            if not free_tag and not curr_tag and key_env:
                lines.append(("class:meta", f"  {key_env}"))
            lines.append(("", "\n"))

        lines.append(("", "\n"))
        lines.append(("class:footer", f"  {shown} of {total} models  (upgrade litellm for newest models)\n"))
        return lines

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("c-p")
    def _up(event):
        filtered = get_filtered()
        if filtered:
            state["cursor"] = (state["cursor"] - 1) % len(filtered)
        event.app.invalidate()

    @kb.add("down")
    @kb.add("c-n")
    def _down(event):
        filtered = get_filtered()
        if filtered:
            state["cursor"] = (state["cursor"] + 1) % len(filtered)
        event.app.invalidate()

    @kb.add("enter")
    def _enter(event):
        filtered = get_filtered()
        if filtered and 0 <= state["cursor"] < len(filtered):
            state["result"] = filtered[state["cursor"]]
        state["done"] = True
        event.app.exit()

    @kb.add("escape")
    @kb.add("c-c")
    @kb.add("c-d")
    def _cancel(event):
        state["done"] = True
        event.app.exit()

    @kb.add("backspace")
    def _backspace(event):
        if state["query"]:
            state["query"] = state["query"][:-1]
            state["cursor"] = 0
        event.app.invalidate()

    @kb.add("<any>")
    def _char(event):
        ch = event.data
        if ch and ch.isprintable() and ch not in ("\r", "\n"):
            state["query"] += ch
            state["cursor"] = 0
        event.app.invalidate()

    layout = Layout(HSplit([
        Window(content=FormattedTextControl(render_list, focusable=True), wrap_lines=False),
    ]))

    app: Application = Application(
        layout=layout,
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
    )

    print()
    app.run()
    print()

    if not state["result"]:
        return ("", None)

    _grp, model_str, display, needs_key, key_env = state["result"]
    return _handle_sentinel(model_str, key_env)


def _handle_sentinel(model_str: str, key_env: str | None) -> tuple[str, str | None]:
    """Prompt for extra info when a sentinel entry is selected."""
    _LOCAL_DEFAULTS = {
        "__ollama__":    ("http://localhost:11434", "ollama"),
        "__jan__":       ("http://localhost:1337/v1", "openai"),
        "__lmstudio__":  ("http://localhost:1234/v1", "openai"),
        "__llamacpp__":  ("http://localhost:8080/v1", "openai"),
        "__gpt4all__":   ("http://localhost:4891/v1", "openai"),
    }

    if model_str in _LOCAL_DEFAULTS:
        default_base, prefix = _LOCAL_DEFAULTS[model_str]
        server_name = model_str.strip("_").replace("llamacpp", "llama.cpp").replace(
            "lmstudio", "LM Studio").replace("gpt4all", "GPT4All").replace(
            "jan", "Jan").replace("ollama", "Ollama")
        try:
            base = input(f"  {_C}›{_X} {server_name} base URL [{default_base}]: ").strip() or default_base
            mdl  = input(f"  {_C}›{_X} Model name (e.g. llama3, mistral): ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return ("", None)
        if not mdl:
            return ("", None)
        _save_compat_base(base)
        if prefix == "ollama":
            return (f"ollama_chat/{mdl}", None)
        return (f"openai/{mdl}", None)

    if model_str == "__openai_compat__":
        try:
            base = input(f"  {_C}›{_X} API base URL (e.g. http://localhost:1234/v1): ").strip()
            mdl  = input(f"  {_C}›{_X} Model name: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return ("", None)
        if base and mdl:
            _save_compat_base(base)
            return (f"openai/{mdl}", None)
        return ("", None)

    if model_str == "__custom__":
        try:
            custom = input(f"  {_C}›{_X} Enter litellm model string (e.g. groq/llama3): ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return ("", None)
        return (custom, None) if custom else ("", None)

    return (model_str, key_env)


def _save_compat_base(base: str) -> None:
    p = os.path.join(os.path.expanduser("~"), ".applehealth", "ai_prefs.json")
    try:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                prefs = json.load(fh)
        else:
            prefs = {}
    except Exception:
        prefs = {}
    prefs["openai_compat_base"] = base
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(prefs, fh, indent=2)


def _pick_model_fallback(current_model: str) -> tuple[str, str | None]:
    """Plain numbered list fallback when prompt_toolkit is unavailable."""
    print(f"\n  {_W}Choose your AI model{_X}\n")
    num = 1
    index_map: dict[int, tuple[str, str, str, bool, str | None]] = {}
    current_num: int | None = None
    prev_group = None

    for entry in MODELS:
        group, model_str, display, needs_key, key_env = entry
        if group != prev_group:
            print(f"\n  {_D}── {group}{_X}")
            prev_group = group
        free   = f"  {_G}free{_X}" if not needs_key else ""
        marker = f"  {_G}← current{_X}" if model_str == current_model else ""
        if model_str == current_model:
            current_num = num
        print(f"  {_D}{num:>3}.{_X}  {display}{free}{marker}")
        index_map[num] = entry
        num += 1

    default_hint = str(current_num) if current_num else ""
    try:
        raw = input(f"\n  {_C}›{_X} Enter number{f' [{default_hint}]' if default_hint else ''}: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return ("", None)

    if not raw and current_model:
        return (current_model, None)
    if not raw.isdigit() or int(raw) not in index_map:
        if current_model:
            return (current_model, None)
        print(f"  {_Y}Invalid selection{_X}")
        return ("", None)

    _grp, model_str, display, needs_key, key_env = index_map[int(raw)]
    return _handle_sentinel(model_str, key_env)
