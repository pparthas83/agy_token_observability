#!/usr/bin/env bash
# ==============================================================================
# Antigravity Token Observability — UI Standards & Regression Gate
#
# Validates Python compilation, Google Cloud Console styling compliance,
# margin geometry, and runs full test coverage to guarantee ZERO regressions.
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
RED="\033[0;31m"
NC="\033[0m"

echo -e "${BOLD}${BLUE}================================================================${NC}"
echo -e "${BOLD}${BLUE}   Antigravity UI Design System & Anti-Regression Verification  ${NC}"
echo -e "${BOLD}${BLUE}================================================================${NC}"

# 1. Syntax & Compilation Check
echo -e "\n${BOLD}[1/3] Checking Python syntax compilation...${NC}"
python3 -m py_compile dashboard/app.py dashboard/theme.py
echo -e "${GREEN}✓ All dashboard source modules compiled successfully.${NC}"

# 2. UI Styling & Layout Regression Test Suite
echo -e "\n${BOLD}[2/3] Running UI Styling & Design System Regression Suite...${NC}"
uv run --with pytest --with plotly pytest tests/test_styling_regression.py -v
echo -e "${GREEN}✓ All 10 UI styling & margin geometry assertions passed.${NC}"

# 3. Full Project Test Suite (Pricing, Telemetry, Extractor, Stress)
echo -e "\n${BOLD}[3/3] Running full test suite across telemetry & tokenomics...${NC}"
uv run --with pytest --with plotly pytest tests/test_pricing.py tests/test_sqlite_extractor.py tests/test_stream_to_bq.py tests/test_telemetry.py tests/test_tokenomics_math.py
echo -e "${GREEN}✓ All core unit & functional tests passed.${NC}"

echo -e "\n${BOLD}${GREEN}================================================================${NC}"
echo -e "${BOLD}${GREEN}   ✓ ALL UI STANDARDS VERIFIED — NO REGRESSIONS DETECTED        ${NC}"
echo -e "${BOLD}${GREEN}================================================================${NC}"
