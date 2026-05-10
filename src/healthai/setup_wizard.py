import os
import json

_C  = "\033[38;5;81m"
_W  = "\033[1;37m"
_D  = "\033[2;37m"
_G  = "\033[38;5;82m"
_Y  = "\033[38;5;226m"
_X  = "\033[0m"

PROVIDERS = [
    {"id": "openai",     "label": "OpenAI (ChatGPT)",        "needs_key": True,  "key_env": "OPENAI_API_KEY"},
    {"id": "claude",     "label": "Claude (Anthropic)",      "needs_key": True,  "key_env": "ANTHROPIC_API_KEY"},
    {"id": "gemini",     "label": "Gemini (Google)",         "needs_key": True,  "key_env": "GOOGLE_API_KEY"},
    {"id": "grok",       "label": "Grok (xAI)",              "needs_key": True,  "key_env": "XAI_API_KEY"},
    {"id": "openrouter", "label": "OpenRouter",              "needs_key": True,  "key_env": "OPENROUTER_API_KEY"},
    {"id": "ollama",     "label": "Ollama (Local — free)",   "needs_key": False, "key_env": None},
    {"id": "lmstudio",   "label": "LM Studio (Local — free)","needs_key": False, "key_env": None},
    {"id": "litellm",    "label": "LiteLLM (Universal)",     "needs_key": False, "key_env": None},
]


def _prefs_path() -> str:
    home = os.path.expanduser("~")
    pref_dir = os.path.join(home, ".applehealth")
    os.makedirs(pref_dir, exist_ok=True)
    return os.path.join(pref_dir, "ai_prefs.json")


def _load_prefs() -> dict:
    path = _prefs_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_prefs(prefs: dict):
    with open(_prefs_path(), "w") as f:
        json.dump(prefs, f, indent=2)


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {_C}›{_X} {prompt}{suffix}: ").strip()
        return val or default
    except (KeyboardInterrupt, EOFError):
        print()
        return default


def _divider():
    print(f"\n  {_D}{'─' * 50}{_X}\n")


def run_setup() -> dict:
    """Interactive first-run setup. Returns completed prefs dict."""
    print(f"\n  🫀 {_W}Welcome to healthai setup!{_X}")
    print(f"  {_D}This only runs once. You can re-run it with: healthai --setup{_X}\n")

    prefs = _load_prefs()

    # ── Step 1: LLM Provider ─────────────────────────────────────
    _divider()
    print(f"  {_W}Step 1 of 4 — Choose your AI provider{_X}\n")
    for i, p in enumerate(PROVIDERS, 1):
        local = f"  {_G}(no API key needed){_X}" if not p["needs_key"] else ""
        print(f"    {_D}{i}.{_X}  {p['label']}{local}")

    while True:
        raw = _ask("\nEnter number", "1")
        if raw.isdigit() and 1 <= int(raw) <= len(PROVIDERS):
            provider = PROVIDERS[int(raw) - 1]
            break
        print(f"  {_Y}Please enter a number between 1 and {len(PROVIDERS)}{_X}")

    prefs["default_provider"] = provider["id"]
    print(f"\n  {_G}✓{_X} Provider set to: {provider['label']}")

    # ── Step 2: API Key ──────────────────────────────────────────
    if provider["needs_key"]:
        _divider()
        print(f"  {_W}Step 2 of 4 — API Key{_X}")
        print(f"  {_D}Set {provider['key_env']} in your shell, or paste it here.{_X}")
        print(f"  {_D}(Stored in ~/.applehealth/ai_prefs.json — never sent anywhere){_X}\n")

        existing = os.environ.get(provider["key_env"], "") or prefs.get(provider["key_env"], "")
        if existing:
            print(f"  {_G}✓{_X} Found existing key ending in ...{existing[-4:]}")
            keep = _ask("Keep it? (y/n)", "y").lower()
            if keep != "n":
                prefs[provider["key_env"]] = existing
            else:
                key = _ask("Paste new API key")
                if key:
                    prefs[provider["key_env"]] = key
        else:
            key = _ask("Paste API key")
            if key:
                prefs[provider["key_env"]] = key
    else:
        print(f"\n  {_G}✓{_X} No API key needed for {provider['label']}")
        if provider["id"] == "ollama":
            try:
                import ollama as _ol
                _ol.Client().list()
                print(f"  {_G}✓{_X} Ollama is running and reachable")
            except Exception:
                print(f"  {_Y}⚠{_X}  Ollama not detected. Make sure it's running: https://ollama.com")

    # ── Step 3: export.xml path ──────────────────────────────────
    _divider()
    print(f"  {_W}Step 3 of 4 — Apple Health export.xml{_X}")
    print(f"  {_D}Export from: iPhone Health app → your avatar → Export All Health Data{_X}\n")

    existing_export = prefs.get("export_xml_path", "")
    if existing_export and os.path.exists(existing_export):
        print(f"  {_G}✓{_X} Found saved path: {existing_export}")
        keep = _ask("Keep it? (y/n)", "y").lower()
        if keep == "n":
            existing_export = ""

    if not existing_export:
        raw = _ask("Path to export.xml (drag-and-drop works)")
        path = raw.strip().strip("'\"").replace("\\ ", " ")
        path = os.path.expanduser(path)
        if path and os.path.exists(path):
            prefs["export_xml_path"] = path
            print(f"  {_G}✓{_X} export.xml found")
        elif path:
            print(f"  {_Y}⚠{_X}  File not found — you can set this later when prompted")

    # ── Step 4: Output directory ─────────────────────────────────
    _divider()
    print(f"  {_W}Step 4 of 4 — Output directory{_X}")
    print(f"  {_D}Where should charts and CSV exports be saved?{_X}\n")

    default_out = os.path.join(os.path.expanduser("~"), "healthai_output")
    existing_out = prefs.get("output_dir", "")
    raw = _ask("Output directory", existing_out or default_out)
    out = os.path.expanduser(raw.strip().strip("'\""))
    os.makedirs(out, exist_ok=True)
    prefs["output_dir"] = out
    print(f"  {_G}✓{_X} Output directory: {out}")

    # ── Save ─────────────────────────────────────────────────────
    _divider()
    prefs["setup_complete"] = True
    _save_prefs(prefs)
    print(f"  🫀 {_G}Setup complete!{_X} Config saved to ~/.applehealth/ai_prefs.json")
    print(f"\n  {_D}To re-run setup: {_C}healthai --setup{_X}\n")

    return prefs


def is_setup_complete() -> bool:
    return _load_prefs().get("setup_complete", False)
