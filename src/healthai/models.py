"""Curated LiteLLM model catalogue and interactive fuzzy-search model picker."""
from __future__ import annotations

from healthai.ui import _C, _W, _D, _G, _Y, _X

# Each entry: (provider_group, litellm_string, display_name, needs_key, key_env)
MODELS: list[tuple[str, str, str, bool, str | None]] = [
    # ── OpenAI ──────────────────────────────────────────────────────────────
    ("OpenAI",          "gpt-4o",                                               "GPT-4o — flagship multimodal",       True,  "OPENAI_API_KEY"),
    ("OpenAI",          "gpt-4o-mini",                                          "GPT-4o Mini — fast & cheap",         True,  "OPENAI_API_KEY"),
    ("OpenAI",          "gpt-4.1",                                              "GPT-4.1 — latest generation",        True,  "OPENAI_API_KEY"),
    ("OpenAI",          "gpt-4.1-mini",                                         "GPT-4.1 Mini",                       True,  "OPENAI_API_KEY"),
    ("OpenAI",          "o3",                                                    "o3 — full reasoning",                True,  "OPENAI_API_KEY"),
    ("OpenAI",          "o3-mini",                                               "o3-mini — reasoning, efficient",     True,  "OPENAI_API_KEY"),
    ("OpenAI",          "o4-mini",                                               "o4-mini — latest small reasoning",   True,  "OPENAI_API_KEY"),
    # ── Anthropic ────────────────────────────────────────────────────────────
    ("Anthropic",       "claude-opus-4-6-20260205",                              "Claude Opus 4.6 — most capable",     True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-opus-4-5-20251101",                              "Claude Opus 4.5",                    True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-sonnet-4-5-20250929",                            "Claude Sonnet 4.5 — balanced",       True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-sonnet-4-20250514",                              "Claude Sonnet 4",                    True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-3-7-sonnet-20250219",                            "Claude 3.7 Sonnet — reasoning",      True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-3-5-sonnet-20241022",                            "Claude 3.5 Sonnet",                  True,  "ANTHROPIC_API_KEY"),
    ("Anthropic",       "claude-3-haiku-20240307",                               "Claude 3 Haiku — fast/cheap",        True,  "ANTHROPIC_API_KEY"),
    # ── Google Gemini ─────────────────────────────────────────────────────────
    ("Google Gemini",   "gemini/gemini-2.5-pro",                                 "Gemini 2.5 Pro — most capable",      True,  "GEMINI_API_KEY"),
    ("Google Gemini",   "gemini/gemini-2.5-flash-preview-04-17",                 "Gemini 2.5 Flash — fast",            True,  "GEMINI_API_KEY"),
    ("Google Gemini",   "gemini/gemini-2.0-flash",                               "Gemini 2.0 Flash — stable",          True,  "GEMINI_API_KEY"),
    ("Google Gemini",   "gemini/gemini-1.5-pro-latest",                          "Gemini 1.5 Pro — long context",      True,  "GEMINI_API_KEY"),
    # ── Groq ─────────────────────────────────────────────────────────────────
    ("Groq",            "groq/llama-3.3-70b-versatile",                          "Llama 3.3 70B — very fast",          True,  "GROQ_API_KEY"),
    ("Groq",            "groq/llama-3.1-8b-instant",                             "Llama 3.1 8B — ultra-fast",          True,  "GROQ_API_KEY"),
    ("Groq",            "groq/meta-llama/llama-4-scout-17b-16e-instruct",        "Llama 4 Scout — vision",             True,  "GROQ_API_KEY"),
    ("Groq",            "groq/meta-llama/llama-4-maverick-17b-128e-instruct",    "Llama 4 Maverick",                   True,  "GROQ_API_KEY"),
    ("Groq",            "groq/qwen/qwen3-32b",                                   "Qwen3 32B via Groq",                 True,  "GROQ_API_KEY"),
    # ── Mistral ───────────────────────────────────────────────────────────────
    ("Mistral",         "mistral/magistral-medium-2506",                         "Magistral Medium — reasoning",       True,  "MISTRAL_API_KEY"),
    ("Mistral",         "mistral/magistral-small-2506",                          "Magistral Small — reasoning",        True,  "MISTRAL_API_KEY"),
    ("Mistral",         "mistral/mistral-large-latest",                          "Mistral Large — flagship",           True,  "MISTRAL_API_KEY"),
    ("Mistral",         "mistral/mistral-small-latest",                          "Mistral Small — cheap",              True,  "MISTRAL_API_KEY"),
    ("Mistral",         "mistral/codestral-latest",                              "Codestral — code specialist",        True,  "MISTRAL_API_KEY"),
    # ── DeepSeek ─────────────────────────────────────────────────────────────
    ("DeepSeek",        "deepseek/deepseek-chat",                                "DeepSeek Chat V3",                   True,  "DEEPSEEK_API_KEY"),
    ("DeepSeek",        "deepseek/deepseek-reasoner",                            "DeepSeek R1 — reasoning",            True,  "DEEPSEEK_API_KEY"),
    # ── xAI ──────────────────────────────────────────────────────────────────
    ("xAI",             "xai/grok-4-1-fast-reasoning",                           "Grok 4.1 Fast — reasoning+vision",   True,  "XAI_API_KEY"),
    ("xAI",             "xai/grok-4-1-fast-non-reasoning",                       "Grok 4.1 Fast — standard",           True,  "XAI_API_KEY"),
    ("xAI",             "xai/grok-3",                                            "Grok 3",                             True,  "XAI_API_KEY"),
    ("xAI",             "xai/grok-3-mini",                                       "Grok 3 Mini",                        True,  "XAI_API_KEY"),
    # ── Perplexity ────────────────────────────────────────────────────────────
    ("Perplexity",      "perplexity/sonar-pro",                                  "Sonar Pro — search+AI",              True,  "PERPLEXITYAI_API_KEY"),
    ("Perplexity",      "perplexity/sonar",                                      "Sonar — fast search",                True,  "PERPLEXITYAI_API_KEY"),
    ("Perplexity",      "perplexity/sonar-reasoning-pro",                        "Sonar Reasoning Pro",                True,  "PERPLEXITYAI_API_KEY"),
    ("Perplexity",      "perplexity/sonar-deep-research",                        "Sonar Deep Research",                True,  "PERPLEXITYAI_API_KEY"),
    # ── Cohere ───────────────────────────────────────────────────────────────
    ("Cohere",          "command-a-03-2025",                                     "Command A — flagship",               True,  "COHERE_API_KEY"),
    ("Cohere",          "command-r-plus-08-2024",                                "Command R+ — strong RAG",            True,  "COHERE_API_KEY"),
    ("Cohere",          "command-r-08-2024",                                     "Command R — efficient RAG",          True,  "COHERE_API_KEY"),
    # ── Kimi / Moonshot AI ────────────────────────────────────────────────────
    ("Kimi (Moonshot)", "moonshot/kimi-k2.5",                                    "Kimi K2.5 — flagship",               True,  "MOONSHOT_API_KEY"),
    ("Kimi (Moonshot)", "moonshot/kimi-latest",                                  "Kimi Latest",                        True,  "MOONSHOT_API_KEY"),
    ("Kimi (Moonshot)", "moonshot/moonshot-v1-128k",                             "Moonshot 128K context",              True,  "MOONSHOT_API_KEY"),
    # ── MiniMax ──────────────────────────────────────────────────────────────
    ("MiniMax",         "minimax/MiniMax-M2.1",                                  "MiniMax M2.1 — flagship",            True,  "MINIMAX_API_KEY"),
    ("MiniMax",         "minimax/MiniMax-M2.1-lightning",                        "MiniMax M2.1 Lightning — fast",      True,  "MINIMAX_API_KEY"),
    ("MiniMax",         "minimax/MiniMax-M2",                                    "MiniMax M2 — agentic+reasoning",     True,  "MINIMAX_API_KEY"),
    # ── Alibaba Qwen / DashScope ──────────────────────────────────────────────
    ("Alibaba Qwen",    "dashscope/qwen-max",                                    "Qwen Max — flagship",                True,  "DASHSCOPE_API_KEY"),
    ("Alibaba Qwen",    "dashscope/qwen-plus",                                   "Qwen Plus — balanced",               True,  "DASHSCOPE_API_KEY"),
    ("Alibaba Qwen",    "dashscope/qwq-32b",                                     "QwQ 32B — reasoning",                True,  "DASHSCOPE_API_KEY"),
    ("Alibaba Qwen",    "dashscope/qwen-turbo",                                  "Qwen Turbo — fast/cheap",            True,  "DASHSCOPE_API_KEY"),
    # ── Cerebras ─────────────────────────────────────────────────────────────
    ("Cerebras",        "cerebras/llama3-70b-instruct",                          "Llama 3 70B — ultra-fast inference", True,  "CEREBRAS_API_KEY"),
    # ── SambaNova ─────────────────────────────────────────────────────────────
    ("SambaNova",       "sambanova/Llama-4-Maverick-17B-128E-Instruct",          "Llama 4 Maverick — fast",            True,  "SAMBANOVA_API_KEY"),
    ("SambaNova",       "sambanova/Meta-Llama-3.3-70B-Instruct",                 "Llama 3.3 70B via SambaNova",        True,  "SAMBANOVA_API_KEY"),
    # ── Fireworks AI ─────────────────────────────────────────────────────────
    ("Fireworks AI",    "fireworks_ai/accounts/fireworks/models/llama-v3p3-70b-instruct", "Llama 3.3 70B via Fireworks", True, "FIREWORKS_AI_API_KEY"),
    ("Fireworks AI",    "fireworks_ai/accounts/fireworks/models/deepseek-r1",    "DeepSeek R1 via Fireworks",          True,  "FIREWORKS_AI_API_KEY"),
    # ── NVIDIA NIM ───────────────────────────────────────────────────────────
    ("NVIDIA NIM",      "nvidia_nim/meta/llama3-70b-instruct",                   "Llama 3 70B via NVIDIA NIM",         True,  "NVIDIA_NIM_API_KEY"),
    ("NVIDIA NIM",      "nvidia_nim/nvidia/nemotron-4-340b-instruct",            "Nemotron 340B",                      True,  "NVIDIA_NIM_API_KEY"),
    # ── AI21 ─────────────────────────────────────────────────────────────────
    ("AI21",            "ai21/jamba-1.5-large",                                  "Jamba 1.5 Large",                    True,  "AI21_API_KEY"),
    ("AI21",            "ai21/jamba-1.5-mini",                                   "Jamba 1.5 Mini — cheap",             True,  "AI21_API_KEY"),
    # ── Nebius ───────────────────────────────────────────────────────────────
    ("Nebius",          "nebius/Qwen/Qwen3-235B-A22B",                           "Qwen3 235B via Nebius (EU)",         True,  "NEBIUS_API_KEY"),
    # ── Z.AI / Zhipu ─────────────────────────────────────────────────────────
    ("Z.AI (Zhipu)",    "zai/glm-4.7",                                           "GLM-4.7 — 200K context",             True,  "ZAI_API_KEY"),
    ("Z.AI (Zhipu)",    "zai/glm-4.5-flash",                                     "GLM-4.5 Flash — free tier",          True,  "ZAI_API_KEY"),
    # ── OpenRouter ────────────────────────────────────────────────────────────
    ("OpenRouter",      "openrouter/openai/gpt-4o",                              "GPT-4o via OpenRouter",              True,  "OPENROUTER_API_KEY"),
    ("OpenRouter",      "openrouter/anthropic/claude-3.5-sonnet",                "Claude 3.5 via OpenRouter",          True,  "OPENROUTER_API_KEY"),
    ("OpenRouter",      "openrouter/meta-llama/llama-3.3-70b-instruct",          "Llama 3.3 70B via OpenRouter",       True,  "OPENROUTER_API_KEY"),
    ("OpenRouter",      "openrouter/google/gemini-2.5-pro",                      "Gemini 2.5 Pro via OpenRouter",      True,  "OPENROUTER_API_KEY"),
    # ── AWS Bedrock ───────────────────────────────────────────────────────────
    ("AWS Bedrock",     "bedrock/us.anthropic.claude-3-7-sonnet-20250219-v1:0",  "Claude 3.7 on Bedrock",              True,  "AWS_ACCESS_KEY_ID"),
    ("AWS Bedrock",     "bedrock/meta.llama3-1-405b-instruct-v1:0",              "Llama 3.1 405B on Bedrock",          True,  "AWS_ACCESS_KEY_ID"),
    ("AWS Bedrock",     "bedrock/us.deepseek.r1-v1:0",                           "DeepSeek R1 on Bedrock",             True,  "AWS_ACCESS_KEY_ID"),
    # ── Ollama (local) ────────────────────────────────────────────────────────
    ("Ollama (local)",  "ollama_chat/llama3.1",                                  "Llama 3.1 — local, free",            False, None),
    ("Ollama (local)",  "ollama_chat/mistral",                                   "Mistral 7B — local, free",           False, None),
    ("Ollama (local)",  "ollama_chat/deepseek-r1",                               "DeepSeek R1 — local, free",          False, None),
    ("Ollama (local)",  "ollama_chat/gemma3",                                    "Gemma 3 — local, free",              False, None),
    ("Ollama (local)",  "ollama_chat/qwen3",                                     "Qwen3 — local, free",                False, None),
    # ── OpenAI-compatible ────────────────────────────────────────────────────
    ("OpenAI-compatible", "__openai_compat__",                                   "Custom endpoint (LM Studio, vLLM…)", False, None),
    # ── Custom ────────────────────────────────────────────────────────────────
    ("Custom",          "__custom__",                                            "Enter any litellm model string…",    False, None),
]

GROUPS: list[str] = list(dict.fromkeys(m[0] for m in MODELS))


def _filter_models(query: str) -> list[tuple[str, str, str, bool, str | None]]:
    """Return models matching query against group, litellm string, and display name."""
    if not query:
        return MODELS
    q = query.lower()
    tokens = q.split()
    results = []
    for entry in MODELS:
        group, model_str, display, needs_key, key_env = entry
        haystack = f"{group} {model_str} {display}".lower()
        if all(t in haystack for t in tokens):
            results.append(entry)
    return results


def pick_model(current_model: str = "") -> tuple[str, str | None]:
    """
    Interactive fuzzy-search model picker.

    Returns (litellm_model_string, key_env_var_or_None).
    Returns ("", None) if the user cancels.
    """
    try:
        return _pick_model_pt(current_model)
    except Exception:
        return _pick_model_fallback(current_model)


def _pick_model_pt(current_model: str) -> tuple[str, str | None]:
    """prompt_toolkit-powered fuzzy picker."""
    from prompt_toolkit import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import HSplit, Window
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
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

    state: dict = {
        "query":   "",
        "cursor":  0,
        "result":  None,
        "done":    False,
    }

    def get_filtered() -> list[tuple[str, str, str, bool, str | None]]:
        return _filter_models(state["query"])

    def clamp_cursor(filtered: list) -> None:
        n = len(filtered)
        if n == 0:
            state["cursor"] = 0
        else:
            state["cursor"] = max(0, min(state["cursor"], n - 1))

    def render_list() -> list:
        filtered = get_filtered()
        clamp_cursor(filtered)
        total = len(MODELS)
        shown = len(filtered)

        lines: list = []

        # header
        lines.append(("class:header", f"  Choose your AI model\n"))
        lines.append(("class:hint",   f"  Type to search · ↑↓ navigate · Enter select · Esc cancel\n\n"))

        # search box
        q = state["query"]
        lines.append(("",             f"  search: "))
        lines.append(("class:model",  q))
        lines.append(("",             "█\n\n"))

        # model list grouped
        prev_group = None
        for i, entry in enumerate(filtered):
            group, model_str, display, needs_key, key_env = entry
            if group != prev_group:
                bar = "─" * max(1, 52 - len(group))
                lines.append(("class:group", f"  ── {group} {bar}\n"))
                prev_group = group

            is_selected = (i == state["cursor"])
            is_current  = (model_str == current_model)

            prefix = "▸ " if is_selected else "  "
            free_tag   = "  free" if not needs_key else ""
            curr_tag   = "  ← current" if is_current else ""
            key_str    = key_env or ""

            name_col = f"{display:<42}"
            key_col  = f"{key_str:<22}"

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
        lines.append(("class:footer", f"  {shown} of {total} models\n"))
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

    layout = Layout(
        HSplit([
            Window(
                content=FormattedTextControl(render_list, focusable=True),
                wrap_lines=False,
            ),
        ])
    )

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

    if model_str == "__openai_compat__":
        try:
            base = input(f"  {_C}›{_X} API base URL (e.g. http://localhost:1234/v1): ").strip()
            mdl  = input(f"  {_C}›{_X} Model name (e.g. local-model): ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return ("", None)
        if base and mdl:
            # Store base URL in prefs separately; return openai/ prefixed string
            import json, os
            p = os.path.join(os.path.expanduser("~"), ".applehealth", "ai_prefs.json")
            try:
                prefs = json.load(open(p)) if os.path.exists(p) else {}
            except Exception:
                prefs = {}
            prefs["openai_compat_base"] = base
            with open(p, "w") as f:
                json.dump(prefs, f, indent=2)
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


def _pick_model_fallback(current_model: str) -> tuple[str, str | None]:
    """Plain numbered fallback when prompt_toolkit fails."""
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
        print(f"  {_Y}Invalid selection{_X}")
        return (current_model, None)

    chosen = index_map[int(raw)]
    _grp, model_str, display, needs_key, key_env = chosen

    if model_str in ("__custom__", "__openai_compat__"):
        try:
            custom = input(f"  {_C}›{_X} Enter litellm model string: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return ("", None)
        return (custom, None) if custom else ("", None)

    return (model_str, key_env)
