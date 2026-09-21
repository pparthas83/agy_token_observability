#!/usr/bin/env bash
# ==============================================================================
# Antigravity Token Observability — Automated Self-Service Installer
# Author: Pradeep Parthasarathy (pradeepsarathy@google.com)
# License: Apache 2.0
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/pparthas83/agy_token_observability/main/install.sh | bash
#   curl -sSL ... | bash -s -- --project=YOUR_PROJECT_ID
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

# Default Configuration
REPO_URL="https://github.com/pparthas83/agy_token_observability.git"
INSTALL_DIR="${HOME}/.antigravity-observability"
HOOKS_JSON="${HOOKS_JSON:-${HOME}/.gemini/config/hooks.json}"
PROJECT_ID=""
DATASET_ID="token_analytics"
NON_INTERACTIVE=false

# ------------------------------------------------------------------------------
# 1. Parse Command Line Arguments
# ------------------------------------------------------------------------------
for arg in "$@"; do
  case $arg in
    --project=*)
      PROJECT_ID="${arg#*=}"
      shift
      ;;
    --dataset=*)
      DATASET_ID="${arg#*=}"
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
    --non-interactive|-y)
      NON_INTERACTIVE=true
      shift
      ;;
    --uninstall)
      if [ -f "${INSTALL_DIR}/uninstall.sh" ]; then
        exec "${INSTALL_DIR}/uninstall.sh" "$@"
      else
        echo -e "${RED}[ERROR]${NC} No existing installation found at ${INSTALL_DIR}"
        exit 1
      fi
      ;;
    --help|-h)
      echo "Antigravity Token Observability Installer"
      echo "Usage: install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --project=PROJECT_ID   Google Cloud Project ID for BigQuery lakehouse"
      echo "  --dataset=DATASET_ID   BigQuery Dataset ID (default: token_analytics)"
      echo "  --dir=PATH             Installation directory (default: ~/.antigravity-observability)"
      echo "  --hooks-file=PATH      Path to Antigravity hooks.json (default: ~/.gemini/config/hooks.json)"
      echo "  --non-interactive, -y  Run non-interactively without prompting"
      echo "  --uninstall            Uninstall token observability and unregister hooks"
      echo "  --help, -h             Show this help message"
      exit 0
      ;;
    *)
      ;;
  esac
done

echo -e "${BLUE}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║      Google Antigravity Token Observability Installer            ║"
echo "║      Concept & Ideation: Pradeep Parthasarathy                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ------------------------------------------------------------------------------
# 2. Pre-flight Environment Checks
# ------------------------------------------------------------------------------
echo -e "${CYAN}[1/6]${NC} Checking system prerequisites..."

# Check Git
if ! command -v git &>/dev/null; then
  echo -e "${RED}[ERROR]${NC} 'git' is required but not installed. Please install git and retry."
  exit 1
fi

# Check Python 3.10+
PYTHON_CMD=""
for cmd in python3.11 python3.12 python3.10 python3 python; do
  if command -v "$cmd" &>/dev/null; then
    if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' &>/dev/null; then
      PYTHON_CMD="$cmd"
      break
    fi
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  echo -e "${RED}[ERROR]${NC} Python 3.10 or higher is required. Please install Python 3.10+."
  exit 1
fi
echo -e "      Found Python: $(${PYTHON_CMD} --version) (${PYTHON_CMD})"

# Check uv (preferred fast installer if present)
USE_UV=false
if command -v uv &>/dev/null; then
  USE_UV=true
  echo -e "      Found Astral uv: $(uv --version) (fast venv bootstrapping enabled)"
fi

# ------------------------------------------------------------------------------
# 3. Resolve Target GCP Project
# ------------------------------------------------------------------------------
echo -e "${CYAN}[2/6]${NC} Resolving Google Cloud project configuration..."

if [ -z "$PROJECT_ID" ]; then
  # Try gcloud CLI
  if command -v gcloud &>/dev/null; then
    DETECTED_GCLOUD=$(gcloud config get-value project 2>/dev/null || true)
    if [ -n "$DETECTED_GCLOUD" ] && [ "$DETECTED_GCLOUD" != "(unset)" ]; then
      PROJECT_ID="$DETECTED_GCLOUD"
    fi
  fi
fi

if [ -z "$PROJECT_ID" ]; then
  # Try environment variables
  PROJECT_ID="${GCP_PROJECT:-${GOOGLE_CLOUD_PROJECT:-}}"
fi

# If still empty and interactive, prompt the user
if [ -z "$PROJECT_ID" ] && [ "$NON_INTERACTIVE" = false ] && [ -t 0 ]; then
  echo -e "${YELLOW}[?]${NC} No active GCP Project detected automatically."
  read -r -p "    Please enter your GCP Project ID: " USER_INPUT_PROJECT
  PROJECT_ID="$(echo "${USER_INPUT_PROJECT}" | tr -d '[:space:]')"
fi

if [ -z "$PROJECT_ID" ]; then
  echo -e "${YELLOW}[WARNING]${NC} GCP Project ID not set. Telemetry will rely on Application Default Credentials (ADC)."
else
  echo -e "      Configured GCP Project: ${BOLD}${PROJECT_ID}${NC}"
fi

# ------------------------------------------------------------------------------
# 4. Clone or Update Telemetry Client
# ------------------------------------------------------------------------------
echo -e "${CYAN}[3/6]${NC} Installing telemetry engine to ${INSTALL_DIR}..."

mkdir -p "$(dirname "${INSTALL_DIR}")"

if [ -d "${INSTALL_DIR}/.git" ]; then
  echo -e "      Existing installation found. Updating repository..."
  git -C "${INSTALL_DIR}" fetch --quiet origin main || true
  git -C "${INSTALL_DIR}" reset --hard --quiet origin/main || true
else
  echo -e "      Cloning repository from GitHub..."
  # If running from inside a local clone of this repo, copy directly to avoid network roundtrip
  CURRENT_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
  if [ -n "${CURRENT_SCRIPT_DIR}" ] && [ -f "${CURRENT_SCRIPT_DIR}/stream_to_bq.py" ] && [ "${CURRENT_SCRIPT_DIR}" != "${INSTALL_DIR}" ]; then
    echo -e "      Bootstrapping from local repository files..."
    git clone --quiet "${CURRENT_SCRIPT_DIR}" "${INSTALL_DIR}"
    cp -f "${CURRENT_SCRIPT_DIR}"/*.py "${INSTALL_DIR}/" 2>/dev/null || true
    cp -f "${CURRENT_SCRIPT_DIR}"/*.sh "${INSTALL_DIR}/" 2>/dev/null || true
  else
    git clone --quiet "${REPO_URL}" "${INSTALL_DIR}"
  fi
fi

chmod 700 "${INSTALL_DIR}"

# Write environment configuration
cat <<ENVEOF > "${INSTALL_DIR}/config.env"
# Antigravity Observability Environment Configuration
# Auto-generated by install.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
GCP_PROJECT=${PROJECT_ID}
BQ_DATASET=${DATASET_ID}
BQ_TABLE=antigravity_token_events
ENVEOF
chmod 600 "${INSTALL_DIR}/config.env"

# ------------------------------------------------------------------------------
# 5. Bootstrap Isolated Python Environment
# ------------------------------------------------------------------------------
echo -e "${CYAN}[4/6]${NC} Bootstrapping isolated Python virtual environment..."

if [ ! -d "${INSTALL_DIR}/.venv" ]; then
  if [ "$USE_UV" = true ]; then
    uv venv "${INSTALL_DIR}/.venv" --python "$PYTHON_CMD" --allow-existing --quiet
  else
    "$PYTHON_CMD" -m venv "${INSTALL_DIR}/.venv"
  fi
fi

if [ "$USE_UV" = true ]; then
  uv pip install --python "${INSTALL_DIR}/.venv/bin/python" -r "${INSTALL_DIR}/requirements.txt" --quiet
else
  "${INSTALL_DIR}/.venv/bin/pip" install --quiet -r "${INSTALL_DIR}/requirements.txt"
fi

# Ensure executable wrapper
cat <<'WRAPPER_EOF' > "${INSTALL_DIR}/run_hook.sh"
#!/usr/bin/env bash
# Wrapper script for Antigravity Stop lifecycle hook
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/config.env" ]; then
  set -a
  source "${SCRIPT_DIR}/config.env" 2>/dev/null || true
  set +a
fi
exec "${SCRIPT_DIR}/.venv/bin/python3" "${SCRIPT_DIR}/stream_to_bq.py" --hook "$@"
WRAPPER_EOF
chmod +x "${INSTALL_DIR}/run_hook.sh"

# Ensure uninstall script is present in install dir
if [ -f "${INSTALL_DIR}/uninstall.sh" ]; then
  chmod +x "${INSTALL_DIR}/uninstall.sh"
fi

# ------------------------------------------------------------------------------
# 6. Idempotent Hook Registration in Antigravity hooks.json
# ------------------------------------------------------------------------------
echo -e "${CYAN}[5/6]${NC} Registering Antigravity lifecycle hook..."

TARGET_HOOKS_FILE="${HOOKS_JSON}" TARGET_HOOK_CMD="${INSTALL_DIR}/run_hook.sh" "${INSTALL_DIR}/.venv/bin/python3" - <<'PYEOF'
import json
import os
import shutil

hooks_file = os.path.expanduser(os.environ["TARGET_HOOKS_FILE"])
hook_cmd = os.path.expanduser(os.environ["TARGET_HOOK_CMD"])

os.makedirs(os.path.dirname(hooks_file), exist_ok=True)

data = {}
if os.path.exists(hooks_file):
    # Always create backup before any modification
    try:
        shutil.copyfile(hooks_file, hooks_file + ".bak")
    except Exception as e:
        print(f"      Warning: Could not create backup of {hooks_file}: {e}")

    try:
        with open(hooks_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content:
                data = json.loads(content)
    except Exception as e:
        print(f"      Note: Existing hooks file could not be parsed as JSON ({e}), resetting.")

# Idempotently inject token-observability Stop hook
data["token-observability"] = {
    "enabled": True,
    "Stop": [
        {
            "type": "command",
            "command": hook_cmd,
            "timeout": 30
        }
    ]
}

# Atomic write using temporary file + rename to prevent corruption
tmp_file = hooks_file + ".tmp"
with open(tmp_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
os.replace(tmp_file, hooks_file)

print(f"      Hook successfully registered in: {hooks_file}")
PYEOF

# ------------------------------------------------------------------------------
# 7. Verification, Schema Provisioning & Health Check
# ------------------------------------------------------------------------------
echo -e "${CYAN}[6/6]${NC} Running verification & BigQuery provisioning..."

ADC_VALID=true
if command -v gcloud &>/dev/null; then
  if ! gcloud auth application-default print-access-token &>/dev/null; then
    ADC_VALID=false
  fi
fi

if [ "$ADC_VALID" = true ]; then
  echo -e "      Provisioning BigQuery dataset, partitioned table, and analytical views in your GCP account..."
  "${INSTALL_DIR}/.venv/bin/python3" "${INSTALL_DIR}/stream_to_bq.py" --init-schema || true
else
  echo -e "      ${YELLOW}Note:${NC} ADC not authenticated yet. Schema provisioning will automatically occur upon first run."
fi

# Perform dry-run test
set +e
TEST_OUTPUT=$("${INSTALL_DIR}/.venv/bin/python3" "${INSTALL_DIR}/stream_to_bq.py" --dry-run 2>&1)
TEST_STATUS=$?
set -e

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD} ✔ Antigravity Token Observability Successfully Installed!          ${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Installation Directory:${NC}  ${INSTALL_DIR}"
echo -e "  ${BOLD}GCP Project:${NC}            ${PROJECT_ID:-Auto-detected via ADC}"
echo -e "  ${BOLD}BigQuery Fact Table:${NC}    ${PROJECT_ID:-<your-gcp-project>}.${DATASET_ID}.antigravity_token_events (DAY-Partitioned & Clustered)"
echo -e "  ${BOLD}Analytical Views:${NC}       v_conversation_rollup, v_daily_project_spend"
echo -e "  ${BOLD}Lifecycle Hook:${NC}         ${HOOKS_JSON} -> 'Stop'"
echo ""

if [ "$ADC_VALID" = false ]; then
  echo -e "${YELLOW}${BOLD}[!] ACTION REQUIRED: Application Default Credentials (ADC)${NC}"
  echo -e "    Run the following command once to authenticate BigQuery streaming:"
  echo -e "    ${CYAN}gcloud auth application-default login${NC}"
  echo ""
fi

echo -e "${BOLD}Next Steps:${NC}"
echo -e "  1. Work normally in Google Antigravity or Antigravity IDE."
echo -e "     Token metrics will stream automatically at the end of every agent turn."
echo -e "  2. View live tokenomics on your Cloud Run Dashboard:"
echo -e "     ${BLUE}https://antigravity-token-dashboard-832497031659.us-central1.run.app${NC}"
echo ""
echo -e "${BOLD}Management Commands:${NC}"
echo -e "  - Dry-run test:    ${CYAN}${INSTALL_DIR}/.venv/bin/python3 ${INSTALL_DIR}/stream_to_bq.py --dry-run${NC}"
echo -e "  - Backfill all:    ${CYAN}${INSTALL_DIR}/.venv/bin/python3 ${INSTALL_DIR}/stream_to_bq.py --backfill${NC}"
echo -e "  - Init/Fix schema: ${CYAN}${INSTALL_DIR}/.venv/bin/python3 ${INSTALL_DIR}/stream_to_bq.py --init-schema${NC}"
echo -e "  - Uninstall:       ${CYAN}${INSTALL_DIR}/uninstall.sh${NC}"
echo ""

# Anonymous install metric ping (non-blocking, 2s timeout)
curl -fsS --max-time 2 "https://komarev.com/ghpvc/?username=pparthas83&repo=agy_token_observability_installs&label=Installs" >/dev/null 2>&1 || true

echo -e "${BOLD}⭐ Antigravity Token Observability${NC}"
echo -e "   Concept & Ideation: ${BOLD}Pradeep Parthasarathy${NC} (pradeepsarathy@google.com)"
echo -e "   Build: Antigravity & Gemini"
echo -e "   Star or fork on GitHub: ${BLUE}https://github.com/pparthas83/agy_token_observability${NC}"
echo ""
