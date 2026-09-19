#!/usr/bin/env bash
# Wrapper script for Antigravity Stop lifecycle hook
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/.venv/bin/python3" "${SCRIPT_DIR}/stream_to_bq.py" --hook
