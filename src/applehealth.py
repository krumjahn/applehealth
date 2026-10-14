"""Backwards-compatibility shim for legacy integrations (OpenClaw skill, scripts).

The real code lives in src/healthai/cli.py. When imported, this module aliases
itself to that module in sys.modules so attribute access like
``applehealth.analyze_steps``, ``applehealth.plt`` or ``applehealth._set_saved_pref``
works exactly as it did before the v1.10 refactor — including setting module
state such as ``applehealth._output_dir`` or ``applehealth._export_xml_path``.
"""
import sys

from healthai.cli import main  # noqa: F401  (explicit re-export for tooling)

if __name__ == "__main__":
    main()
else:
    from healthai import cli as _cli

    # Import time: become the healthai.cli module for all intents and purposes.
    sys.modules[__name__] = _cli
