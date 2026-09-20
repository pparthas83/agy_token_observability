"""Unit tests for stream_to_bq.py BigQuery row construction and sync state."""

import datetime
import json
import os
import tempfile
import pytest
from unittest.mock import patch
import stream_to_bq


def test_build_bigquery_rows():
    raw_records = [
        {
            "conversation_id": "conv-abc-123",
            "step_index": 4,
            "timestamp": datetime.datetime(2026, 9, 20, 12, 0, 0, tzinfo=datetime.timezone.utc),
            "antigravity_project_id": "proj-99",
            "antigravity_project_name": "token_observability",
            "workspace_name": "token_observability",
            "workspace_uri": "file:///path/to/token_observability",
            "surface": "app",
            "model": "gemini-3.8-flash",
            "prompt_tokens": 1000,
            "output_tokens": 500,
            "cached_tokens": 800,
            "thinking_tokens": 50,
            "content_tokens": 450,
            "total_tokens": 1500,
            "latency_ms": 250,
            "ttft_latency_ms": 250,
            "client_prep_ms": 50,
            "generation_duration_ms": 500,
            "tokens_per_second": 1000.0,
            "step_type": "PLANNER_RESPONSE",
            "tool_name": None,
        }
    ]

    rows, row_ids = stream_to_bq.build_bigquery_rows(raw_records, user_email="developer@example.com")

    assert len(rows) == 1
    assert len(row_ids) == 1
    assert row_ids[0] == "conv-abc-123_4"

    r = rows[0]
    assert r["event_id"] == "conv-abc-123_4"
    assert r["conversation_id"] == "conv-abc-123"
    assert r["step_index"] == 4
    assert r["user_email"] == "developer@example.com"
    assert r["antigravity_project_name"] == "token_observability"
    assert r["cached_tokens"] == 800
    assert r["thinking_tokens"] == 50
    assert r["content_tokens"] == 450
    # Cost for 1,000 prompt + 500 output @ Flash rates ($0.15/M, $0.60/M):
    # 0.00015 + 0.00030 = 0.00045
    assert float(r["estimated_cost_usd"]) == 0.00045


def test_sync_state_save_and_load():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_file_path = os.path.join(tmpdir, ".sync_state.json")
        with patch("stream_to_bq.STATE_FILE", state_file_path):
            # Fresh state
            assert stream_to_bq.load_sync_state() == {}

            # Save state
            test_state = {"conv-1": 10, "conv-2": 45}
            stream_to_bq.save_sync_state(test_state)

            # Reload and verify
            loaded = stream_to_bq.load_sync_state()
            assert loaded == test_state
