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
    # Gemini prompt cache discount: $0.15/M -> $0.0375/M (savings = $0.1125/M)
    tot_cached = 49_889_551
    dollars_saved = (tot_cached / 1_000_000.0) * 0.1125
    assert round(dollars_saved, 2) == 5.61


def test_fmt_tok_short():
    def _fmt_tok_short(n: int) -> str:
        if n >= 1_000_000:
            return f"{n/1_000_000.0:.2f}M"
        elif n >= 1_000:
            return f"{n/1000.0:.1f}k"
        return f"{int(n):,}"

    assert _fmt_tok_short(64_417_519) == "64.42M"
    assert _fmt_tok_short(102_069) == "102.1k"
    assert _fmt_tok_short(672) == "672"
