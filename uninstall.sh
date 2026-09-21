#!/usr/bin/env bash
# ==============================================================================
# Antigravity Token Observability — Clean Uninstaller
# Author: Pradeep Parthasarathy (pradeepsarathy@google.com)
# License: Apache 2.0
# ==============================================================================
set -euo pipefail

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

INSTALL_DIR="${HOME}/.antigravity-observability"
HOOKS_JSON="${HOOKS_JSON:-${HOME}/.gemini/config/hooks.json}"
NON_INTERACTIVE=false

for arg in "$@"; do
  case $arg in
    --non-interactive|-y)
      NON_INTERACTIVE=true
      shift
      ;;
    --dir=*)
      INSTALL_DIR="${arg#*=}"
      shift
      ;;
    --hooks-file=*)
      HOOKS_JSON="${arg#*=}"
      shift
      ;;
    --help|-h)
      echo "Antigravity Token Observability Uninstaller"
      echo "Usage: uninstall.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --dir=PATH             Installation directory (default: ~/.antigravity-observability)"
      echo "  --hooks-file=PATH      Path to hooks.json (default: ~/.gemini/config/hooks.json)"
      echo "  --non-interactive, -y  Skip confirmation prompt"
      echo "  --help, -h             Show this help message"
      exit 0
      ;;
    *)
      ;;
  esac
done

echo -e "${YELLOW}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║      Google Antigravity Token Observability Uninstaller          ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

if [ "$NON_INTERACTIVE" = false ] && [ -t 0 ]; then
  read -r -p "Are you sure you want to uninstall Antigravity Token Observability? [y/N]: " CONFIRM
  case "$CONFIRM" in
    [yY][eE][sS]|[yY])
      ;;
    *)
      echo "Uninstall canceled."
      exit 0
      ;;
  esac
fi

# 1. Safely remove hook from hooks.json
if [ -f "$HOOKS_JSON" ]; then
  echo -e "${CYAN}[1/2]${NC} Unregistering hook from ${HOOKS_JSON}..."
  TARGET_HOOKS_FILE="${HOOKS_JSON}" python3 - <<'PYEOF'
import json
import os
import shutil

hooks_file = os.path.expanduser(os.environ["TARGET_HOOKS_FILE"])
if os.path.exists(hooks_file):
    try:
        shutil.copyfile(hooks_file, hooks_file + ".bak")
    except Exception as e:
        print(f"      Warning: Could not create backup of {hooks_file}: {e}")

    try:
        data = {}
        with open(hooks_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                data = json.loads(content)
        if "token-observability" in data:
            del data["token-observability"]
            tmp_file = hooks_file + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_file, hooks_file)
            print("      Successfully removed 'token-observability' hook.")
        else:
            print("      'token-observability' hook was not found in hooks.json.")
    except Exception as e:
        print(f"      Warning: Could not process {hooks_file}: {e}")
PYEOF
else
  echo -e "${CYAN}[1/2]${NC} No hooks configuration found at ${HOOKS_JSON}."
fi

# 2. Remove Installation Directory
echo -e "${CYAN}[2/2]${NC} Removing installation directory: ${INSTALL_DIR}..."
if [ -d "$INSTALL_DIR" ]; then
  # If running uninstall.sh from inside INSTALL_DIR, schedule deletion after exit
  SCRIPT_PARENT="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
  if [ "$SCRIPT_PARENT" = "$INSTALL_DIR" ]; then
    (sleep 1 && rm -rf "$INSTALL_DIR") &
    echo "      Installation files scheduled for cleanup."
  else
    rm -rf "$INSTALL_DIR"
    echo "      Installation directory removed."
  fi
else
  echo "      Directory ${INSTALL_DIR} does not exist."
fi

echo ""
echo -e "${GREEN}${BOLD}✔ Antigravity Token Observability has been successfully uninstalled.${NC}"
echo ""
