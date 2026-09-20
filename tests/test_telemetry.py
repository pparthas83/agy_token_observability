"""Unit tests for Token Telemetry phase breakdowns, context extraction, and metrics."""

import json
import pytest
from context_extractor import (
    generate_fallback_context,
    extract_turn_context_metadata,
    get_static_scope,
)


def test_static_scope_capabilities():
    scope = get_static_scope()
    assert scope["native_tools_count"] == 14
    assert "run_command" in scope["native_tools_sample"]
    assert "view_file" in scope["native_tools_sample"]
    assert "cloudrun" in scope["mcp_servers"]
    assert scope["skills_count"] == 42
    assert "Linux" in scope["os"]


def test_generate_fallback_context():
    fb = generate_fallback_context(
        step_index=100,
        prompt_tokens=50000,
        cached_tokens=40000,
        tool_name="run_command",
        user_prompt_preview="Test prompt"
    )
    assert fb["step_index"] == 100
    assert fb["user_request_preview"] == "Test prompt"
    assert fb["checkpoint_active"] is True
    assert fb["working_injections"]["command_runs"] == 1
    assert fb["working_injections"]["file_reads"] == 0
    assert fb["static_scope"]["native_tools_count"] == 14


def test_telemetry_phase_breakdown():
    # Example turn
    client_prep_ms = 2500
    ttft_latency_ms = 1300
    generation_duration_ms = 10000
    thinking_tokens = 500
    output_tokens = 2000

    # Thinking share calculation
    thinking_ratio = thinking_tokens / output_tokens if output_tokens > 0 else 0.0
    thinking_ms = int(generation_duration_ms * thinking_ratio)
    streaming_ms = max(0, generation_duration_ms - thinking_ms)

    assert thinking_ms == 2500
    assert streaming_ms == 7500
    assert (thinking_ms + streaming_ms) == generation_duration_ms

    total_turn_ms = client_prep_ms + ttft_latency_ms + generation_duration_ms
    assert total_turn_ms == 13800


def test_directional_context_percentages():
    total_prompt = 100000
    cached = 75000
    uncached = total_prompt - cached

    cached_pct = round((cached / total_prompt) * 100, 1)
    uncached_pct = round((uncached / total_prompt) * 100, 1)

    assert cached_pct == 75.0
    assert uncached_pct == 25.0
    assert (cached_pct + uncached_pct) == 100.0


def test_extract_turn_context_nonexistent_conv():
    # Non-existent conversation should return deterministic fallback without throwing
    res = extract_turn_context_metadata(
        conversation_id="non-existent-conv-id",
        step_index=5,
        prompt_tokens=1000,
        cached_tokens=0,
    )
    assert res["step_index"] == 5
    assert res["checkpoint_active"] is False
    assert res["static_scope"]["native_tools_count"] == 14
