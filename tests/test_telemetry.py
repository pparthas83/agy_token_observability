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


def compute_directional_context(prompt_tokens: int, cached_tokens: int):
    c_tok = max(0, cached_tokens)
    # If prompt_tokens >= cached_tokens, prompt_tokens is total prompt
    if prompt_tokens >= c_tok:
        fresh_tok = prompt_tokens - c_tok
    else:
        # prompt_tokens is uncached fresh tokens
        fresh_tok = prompt_tokens
    tot_prompt = c_tok + fresh_tok
    if tot_prompt > 0:
        cache_pct = round((c_tok / tot_prompt) * 100.0, 1)
        fresh_pct = round(100.0 - cache_pct, 1)
    else:
        cache_pct = 0.0
        fresh_pct = 100.0
    return tot_prompt, c_tok, fresh_tok, cache_pct, fresh_pct


def test_directional_context_percentages():
    # Case 1: Standard case where prompt_tokens contains total prompt
    tot, c, f, c_pct, f_pct = compute_directional_context(prompt_tokens=100_000, cached_tokens=75_000)
    assert tot == 100_000
    assert c == 75_000
    assert f == 25_000
    assert c_pct == 75.0
    assert f_pct == 25.0
    assert (c_pct + f_pct) == 100.0

    # Case 2: Turn #6674 from user screenshot (prompt_tokens recorded uncached portion)
    tot, c, f, c_pct, f_pct = compute_directional_context(prompt_tokens=2_930, cached_tokens=74_448)
    assert tot == 77_378
    assert c == 74_448
    assert f == 2_930
    assert c_pct == 96.2
    assert f_pct == 3.8
    assert (c_pct + f_pct) == 100.0
    assert 0.0 <= c_pct <= 100.0
    assert 0.0 <= f_pct <= 100.0

    # Case 3: Initial cold prefill turn (no cache)
    tot, c, f, c_pct, f_pct = compute_directional_context(prompt_tokens=15_000, cached_tokens=0)
    assert tot == 15_000
    assert c == 0
    assert f == 15_000
    assert c_pct == 0.0
    assert f_pct == 100.0

    # Case 4: Zero tokens safeguard
    tot, c, f, c_pct, f_pct = compute_directional_context(prompt_tokens=0, cached_tokens=0)
    assert tot == 0
    assert c_pct == 0.0
    assert f_pct == 100.0


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
