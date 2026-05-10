#!/usr/bin/env bash
set -euo pipefail

CYAN='\033[38;5;81m'
GREEN='\033[38;5;82m'
YELLOW='\033[38;5;226m'
RESET='\033[0m'

echo ""
echo -e "  ${CYAN}healthai installer${RESET}"
echo -e "  ${CYAN}──────────────────────────────────${RESET}"
echo ""

# 1. Check Python
if ! command -v python3 &>/dev/null; then
  echo -e "  ${YELLOW}✗ Python 3 not found. Install from https://python.org${RESET}"
  exit 1
fi

PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "  ${GREEN}✓${RESET} Python $PY_VERSION found"

# 2. Check/install pipx
if ! command -v pipx &>/dev/null; then
  echo "  Installing pipx..."
  python3 -m pip install --user pipx --quiet
  python3 -m pipx ensurepath
  echo -e "  ${GREEN}✓${RESET} pipx installed"
else
  echo -e "  ${GREEN}✓${RESET} pipx found"
fi

# 3. Install healthai
echo "  Installing healthai..."
pipx install healthai --quiet
echo -e "  ${GREEN}✓${RESET} healthai installed"
echo ""
echo -e "  Run ${CYAN}healthai${RESET} to get started."
echo ""
