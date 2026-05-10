"""Backwards-compatibility shim. The real code lives in src/healthai/cli.py."""
from healthai.cli import main

if __name__ == "__main__":
    main()
