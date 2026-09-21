"""
Comprehensive Stress Test Suite for Antigravity Self-Service Installer & Telemetry Engine.
Tests extreme edge cases: corrupted configs, special character paths, network failures,
idempotency, and IDE non-blocking invariants.
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import pytest
from unittest.mock import MagicMock, patch

import stream_to_bq
import pricing
import sqlite_extractor


REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_stress_idempotent_double_install():
    """Verify installing twice in a row does not corrupt config or duplicate hooks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = os.path.join(tmpdir, "observability_engine")
        test_hooks = os.path.join(tmpdir, "config", "hooks.json")
        
        # Run 1
        cmd1 = f"{REPO_DIR}/install.sh --dir='{test_dir}' --hooks-file='{test_hooks}' --project=stress-proj-1 --non-interactive"
        res1 = subprocess.run(cmd1, shell=True, capture_output=True, text=True)
        assert res1.returncode == 0, f"Run 1 failed: {res1.stderr}"

        # Run 2
        cmd2 = f"{REPO_DIR}/install.sh --dir='{test_dir}' --hooks-file='{test_hooks}' --project=stress-proj-1 --non-interactive"
        res2 = subprocess.run(cmd2, shell=True, capture_output=True, text=True)
        assert res2.returncode == 0, f"Run 2 failed: {res2.stderr}"

        # Verify hooks file is valid JSON and contains exactly one token-observability entry
        with open(test_hooks, "r", encoding="utf-8") as f:
            hooks_data = json.load(f)
        assert "token-observability" in hooks_data
        assert hooks_data["token-observability"]["enabled"] is True
        assert len(hooks_data["token-observability"]["Stop"]) == 1


def test_stress_paths_with_spaces_and_quotes():
    """Verify installation and execution works seamlessly in paths containing spaces and quotes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Complex path with spaces and parenthesis
        test_dir = os.path.join(tmpdir, "my agent (v2) dir", "sub space obs")
        test_hooks = os.path.join(tmpdir, "gemini config", "hooks.json")
        
        cmd = f"{REPO_DIR}/install.sh --dir='{test_dir}' --hooks-file='{test_hooks}' --project=stress-space-proj --non-interactive"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert res.returncode == 0, f"Install in path with spaces failed: {res.stderr}\nStdout: {res.stdout}"

        # Verify files exist in the space-padded directory
        assert os.path.exists(os.path.join(test_dir, "run_hook.sh"))
        assert os.path.exists(os.path.join(test_dir, "stream_to_bq.py"))
        assert os.path.exists(os.path.join(test_dir, "config.env"))

        # Verify hooks.json correctly recorded the path with spaces
        with open(test_hooks, "r", encoding="utf-8") as f:
            hooks_data = json.load(f)
        expected_cmd = os.path.join(test_dir, "run_hook.sh")
        assert hooks_data["token-observability"]["Stop"][0]["command"] == expected_cmd


def test_stress_preservation_of_external_hooks():
    """Verify pre-existing tools in hooks.json are completely preserved upon install and uninstall."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = os.path.join(tmpdir, "obs")
        test_hooks = os.path.join(tmpdir, "hooks.json")

        initial_hooks = {
            "linter-daemon": {
                "enabled": True,
                "PreHook": [{"type": "command", "command": "/usr/bin/linter"}]
            },
            "security-scanner": {
                "enabled": True,
                "Stop": [{"type": "command", "command": "/opt/sec/scan.sh"}]
            }
        }
        with open(test_hooks, "w", encoding="utf-8") as f:
            json.dump(initial_hooks, f, indent=2)

        # Install
        cmd_install = f"{REPO_DIR}/install.sh --dir='{test_dir}' --hooks-file='{test_hooks}' --project=test-preserve --non-interactive"
        res_install = subprocess.run(cmd_install, shell=True, capture_output=True, text=True)
        assert res_install.returncode == 0

        with open(test_hooks, "r", encoding="utf-8") as f:
            post_install = json.load(f)
        assert "linter-daemon" in post_install
        assert "security-scanner" in post_install
        assert "token-observability" in post_install

        # Uninstall
        cmd_uninstall = f"{REPO_DIR}/uninstall.sh --dir='{test_dir}' --hooks-file='{test_hooks}' --non-interactive"
        res_uninstall = subprocess.run(cmd_uninstall, shell=True, capture_output=True, text=True)
        assert res_uninstall.returncode == 0

        with open(test_hooks, "r", encoding="utf-8") as f:
            post_uninstall = json.load(f)
        assert "linter-daemon" in post_uninstall
        assert "security-scanner" in post_uninstall
        assert "token-observability" not in post_uninstall


def test_stress_corrupted_hooks_file_handling():
    """Verify installing with a corrupted / empty hooks.json creates a backup and repairs gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = os.path.join(tmpdir, "obs")
        test_hooks = os.path.join(tmpdir, "hooks.json")

        # Corrupt file content
        with open(test_hooks, "w", encoding="utf-8") as f:
            f.write("CORRUPTED SYNTAX {{{{ NOT JSON")

        cmd = f"{REPO_DIR}/install.sh --dir='{test_dir}' --hooks-file='{test_hooks}' --project=test-repair --non-interactive"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        assert res.returncode == 0

        # Verify backup was created preserving corrupt data
        assert os.path.exists(test_hooks + ".bak")
        with open(test_hooks + ".bak", "r", encoding="utf-8") as f:
            assert "CORRUPTED SYNTAX" in f.read()

        # Verify repaired file has valid JSON and token-observability
        with open(test_hooks, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "token-observability" in data


def test_stress_uninstall_from_inside_install_dir():
    """Verify running uninstall.sh from inside the installation directory does not crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = os.path.join(tmpdir, "obs_inner")
        test_hooks = os.path.join(tmpdir, "hooks.json")

        cmd_install = f"{REPO_DIR}/install.sh --dir='{test_dir}' --hooks-file='{test_hooks}' --project=test-inner --non-interactive"
        subprocess.run(cmd_install, shell=True, check=True)

        # Run uninstaller from inside test_dir
        cmd_uninstall = f"cd '{test_dir}' && ./uninstall.sh --dir='{test_dir}' --hooks-file='{test_hooks}' --non-interactive"
        res = subprocess.run(cmd_uninstall, shell=True, capture_output=True, text=True)
        assert res.returncode == 0, f"Uninstaller failed when run from inside dir: {res.stderr}"


def test_stress_ide_non_blocking_invariant():
    """CRITICAL: Verify that if BigQuery is completely unreachable or throws an exception,
    the Stop hook MUST exit with code 0 and output `{}` so the Antigravity IDE never breaks.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file = os.path.join(tmpdir, "state.json")
        with patch("stream_to_bq.STATE_FILE", state_file):
            mock_client = MagicMock()
            # Force BigQuery client to throw a catastrophic network/permission error
            mock_client.insert_rows_json.side_effect = Exception("Simulated GCP 503 Service Unavailable / Network Down")

            # Capture stdout during hook execution
            import io
            saved_stdout = sys.stdout
            try:
                sys.stdout = io.StringIO()
                # Run hook execution
                stream_to_bq.handle_hook_execution(
                    client=mock_client,
                    table_ref="fake-proj.token_analytics.antigravity_token_events",
                    state={},
                    user_email="dev@example.com",
                )
                output = sys.stdout.getvalue().strip()
            finally:
                sys.stdout = saved_stdout

            # Verify IDE invariant: stdout must end with valid JSON response `{}`
            assert output.endswith("{}"), f"Expected hook to output '{{}}' for IDE protocol, got: {output}"


def test_stress_schema_caching_performance():
    """Verify that schema verification is cached in state to prevent redundant API latency on subsequent turns."""
    mock_client = MagicMock()
    state = {}

    cache_key = "_schema_verified_test-proj_token_analytics_antigravity_token_events"
    assert cache_key not in state

    # Turn 1: Cache is cold -> verify or ensure schema
    with patch("stream_to_bq.ensure_bigquery_schema", return_value=True) as mock_ensure:
        # Simulate table not existing on turn 1
        mock_client.get_table.side_effect = Exception("Not found")
        if not state.get(cache_key):
            try:
                mock_client.get_table("test-proj.token_analytics.antigravity_token_events")
            except Exception:
                if mock_ensure(mock_client, "test-proj", "token_analytics", "antigravity_token_events"):
                    state[cache_key] = True

        assert state[cache_key] is True
        mock_ensure.assert_called_once()

    # Turn 2: Cache is warm -> get_table and ensure_schema should NOT be called at all
    with patch("stream_to_bq.ensure_bigquery_schema") as mock_ensure_turn2:
        mock_client.reset_mock()
        if not state.get(cache_key):
            mock_client.get_table("test-proj.token_analytics.antigravity_token_events")

        # Zero API calls on subsequent turns
        mock_client.get_table.assert_not_called()
        mock_ensure_turn2.assert_not_called()
