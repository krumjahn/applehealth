#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


PLUGIN_ID = "health-analyzer-local"
SKILL_ID = "health-analyzer-mac-local"


def copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"OpenClaw config not found: {path}")
    return json.loads(path.read_text())


def ensure_list_value(container: dict, key: str, value: str) -> None:
    items = container.setdefault(key, [])
    if value not in items:
        items.append(value)


def install_companion(skill_root: Path, restart: bool) -> dict:
    codex_home = Path.home() / ".openclaw"
    plugin_src = skill_root / "assets" / PLUGIN_ID
    skill_src = skill_root / "assets" / SKILL_ID
    plugin_dest = codex_home / "extensions" / PLUGIN_ID
    skill_dest = codex_home / "workspace" / "skills" / SKILL_ID
    config_path = codex_home / "openclaw.json"

    if not plugin_src.exists():
        raise FileNotFoundError(f"Companion plugin bundle missing: {plugin_src}")
    if not skill_src.exists():
        raise FileNotFoundError(f"Companion skill bundle missing: {skill_src}")

    copy_tree(plugin_src, plugin_dest)
    copy_tree(skill_src, skill_dest)

    config = load_config(config_path)

    tools = config.setdefault("tools", {})
    ensure_list_value(tools, "alsoAllow", PLUGIN_ID)

    plugins = config.setdefault("plugins", {})
    ensure_list_value(plugins, "allow", PLUGIN_ID)
    plugins.setdefault("entries", {})[PLUGIN_ID] = {"enabled": True}
    plugins.setdefault("installs", {})[PLUGIN_ID] = {
        "source": "path",
        "spec": str(plugin_dest),
        "installPath": str(plugin_dest),
    }

    config_path.write_text(json.dumps(config, indent=2) + "\n")

    validate = subprocess.run(
        ["openclaw", "config", "validate"],
        capture_output=True,
        text=True,
        check=False,
    )
    if validate.returncode != 0:
        raise RuntimeError(validate.stdout.strip() or validate.stderr.strip() or "OpenClaw config validation failed")

    restarted = False
    if restart:
        gateway = subprocess.run(
            ["openclaw", "gateway", "restart"],
            capture_output=True,
            text=True,
            check=False,
        )
        if gateway.returncode != 0:
            raise RuntimeError(gateway.stdout.strip() or gateway.stderr.strip() or "OpenClaw gateway restart failed")
        restarted = True

    return {
        "success": True,
        "plugin_path": str(plugin_dest),
        "skill_path": str(skill_dest),
        "config_path": str(config_path),
        "restarted": restarted,
        "next_steps": [
            "Open a fresh OpenClaw session.",
            "Use the health-analyzer-mac-local skill for Mac app mode.",
            "Use apple-health-export-analyzer for export.xml mode.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the Health Data AI Analyzer Mac app companion plugin and skill into OpenClaw.")
    parser.add_argument("--restart", action="store_true", help="Restart the OpenClaw gateway after installing the companion plugin.")
    args = parser.parse_args()

    try:
        skill_root = Path(__file__).resolve().parents[1]
        result = install_companion(skill_root, restart=args.restart)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
