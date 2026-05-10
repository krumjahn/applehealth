# Shared terminal UI helpers for healthai

_R  = "\033[38;5;196m"
_P  = "\033[38;5;197m"
_P2 = "\033[38;5;204m"
_P3 = "\033[38;5;211m"
_W  = "\033[1;37m"
_D  = "\033[2;37m"
_C  = "\033[38;5;81m"
_G  = "\033[38;5;82m"
_Y  = "\033[38;5;226m"
_X  = "\033[0m"

_BANNER_LINES = [
    r"    _    ____  ____  _     _____   _   _ _____    _    _   _____ _   _ ",
    r"   / \  |  _ \|  _ \| |   | ____| | | | | ____|  / \  | | |_   _| | | |",
    r"  / _ \ | |_) | |_) | |   |  _|   | |_| |  _|   / _ \ | |   | | | |_| |",
    r" / ___ \|  __/|  __/| |___| |___  |  _  | |___ / ___ \| |___| | |  _  |",
    r"/_/   \_\_|   |_|   |_____|_____| |_| |_|_____/_/   \_\_____|_| |_| |_|",
]
_BANNER_COLORS = [_R, _R, _P, _P2, _P3]


def print_banner():
    print()
    for color, line in zip(_BANNER_COLORS, _BANNER_LINES):
        print(f"  {color}{line}{_X}")
    tagline = "🫀 Privacy-First Health Intelligence  ·  AI-Powered  ·  Runs Locally"
    print(f"  {_D}{tagline}{_X}")
    print()


def print_box(lines):
    width = max(len(l) for l in lines) + 2
    print(f"  {_C}┌{'─' * width}┐{_X}")
    for line in lines:
        pad = width - len(line) - 1
        print(f"  {_C}│{_X} {line}{' ' * pad}{_C}│{_X}")
    print(f"  {_C}└{'─' * width}┘{_X}")


def print_section(label):
    print(f"\n  {_W}{label}{_X}")
    print(f"  {_D}{'─' * (len(label) + 20)}{_X}")


def print_item(num, label):
    print(f"  {_D}{num:>2}.{_X}  {label}")
