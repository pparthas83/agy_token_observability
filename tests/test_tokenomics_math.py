"""Unit tests for tokenomics math, cache hit rate, and session token composition."""

import pytest


def calculate_uncached_prompt(prompt_tokens: int, cached_tokens: int) -> int:
    """Computes uncached prompt tokens according to Antigravity telemetry conventions."""
    if prompt_tokens >= cached_tokens:
        return prompt_tokens - cached_tokens
    return prompt_tokens


def test_uncached_prompt_calculation():
    # Case 1: Initial turn without cache
    assert calculate_uncached_prompt(prompt_tokens=25000, cached_tokens=0) == 25000

    # Case 2: Incremental turn where prompt_tokens contains only new input
    assert calculate_uncached_prompt(prompt_tokens=2160, cached_tokens=99237) == 2160

    # Case 3: Turn where prompt_tokens reported total prompt including cache
    assert calculate_uncached_prompt(prompt_tokens=40146, cached_tokens=27446) == 12700


def test_token_slices_sum_to_exact_100_percent():
    # Real conversation values from BigQuery
    tot_cached = 49_889_551
    tot_uncached = 13_958_263
    tot_thinking = 237_264
    tot_content = 332_441

    grand_total = tot_cached + tot_uncached + tot_thinking + tot_content
    assert grand_total == 64_417_519

    pct_cached = (tot_cached / grand_total) * 100.0
    pct_uncached = (tot_uncached / grand_total) * 100.0
    pct_thinking = (tot_thinking / grand_total) * 100.0
    pct_content = (tot_content / grand_total) * 100.0

    sum_pct = pct_cached + pct_uncached + pct_thinking + pct_content
    assert round(sum_pct, 4) == 100.0000

    # Individual shares
    assert round(pct_cached, 1) == 77.4
    assert round(pct_uncached, 1) == 21.7
    assert round(pct_thinking, 1) == 0.4
    assert round(pct_content, 1) == 0.5


def test_cache_hit_rate_calculation():
    tot_cached = 49_889_551
    tot_uncached = 13_958_263
    tot_prompt = tot_cached + tot_uncached

    hit_rate = (tot_cached / tot_prompt) * 100.0
    assert round(hit_rate, 1) == 78.1


def test_cache_savings_calculation():
    # Gemini 3.8 Flash prompt cache discount: $0.75/M -> $0.075/M (savings = $0.675/M)
    tot_cached = 49_889_551
    dollars_saved = (tot_cached / 1_000_000.0) * 0.675
    assert round(dollars_saved, 2) == 33.68


def fmt_tok(n):
    """Format token counts compactly (e.g., 1.25M, 45.2k, or 520)."""
    if n is None:
        return "0"
    try:
        n = float(n)
    except (ValueError, TypeError):
        return str(n)
    if n >= 1_000_000:
        return f"{n/1_000_000.0:.2f}M"
    elif n >= 1_000:
        return f"{n/1000.0:.1f}k"
    return f"{int(n):,}"


def test_fmt_tok():
    assert fmt_tok(64_417_519) == "64.42M"
    assert fmt_tok(102_069) == "102.1k"
    assert fmt_tok(672) == "672"
    assert fmt_tok(0) == "0"
    assert fmt_tok(None) == "0"
    assert fmt_tok(1_500_000.0) == "1.50M"
    assert fmt_tok(50_000) == "50.0k"


def test_financial_trajectory_cumulative_math():
    import pricing

    turns = [
        {"step_index": 1, "cost_usd": 0.05, "cached_tokens": 10_000, "model": "gemini-3.8-flash"},
        {"step_index": 2, "cost_usd": 0.02, "cached_tokens": 50_000, "model": "gemini-3.8-flash"},
    ]

    cum_actual = 0.0
    cum_saved = 0.0
    results = []
    for t in turns:
        cum_actual += t["cost_usd"]
        saved = (t["cached_tokens"] / 1_000_000.0) * pricing.get_cache_savings_rate(t["model"])
        cum_saved += saved
        results.append({
            "cum_actual_cost": round(cum_actual, 6),
            "cum_baseline_cost": round(cum_actual + cum_saved, 6),
        })

    assert results[0]["cum_actual_cost"] == 0.05
    assert results[1]["cum_actual_cost"] == 0.07
    assert results[0]["cum_baseline_cost"] == 0.05675
    assert results[1]["cum_baseline_cost"] == 0.1105

