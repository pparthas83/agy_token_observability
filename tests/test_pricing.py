"""Unit tests for pricing.py rate card resolution and cost calculation."""

import pytest
import pricing


def test_get_model_rates_exact_and_fuzzy():
    # Exact match for Gemini Flash
    assert pricing.get_model_rates("gemini-3.8-flash") == (0.75, 3.75)
    assert pricing.get_model_rates("gemini-2.5-flash") == (0.30, 2.50)
    assert pricing.get_model_rates("gemini-2.0-flash") == (0.15, 0.60)
    
    # Fuzzy match / substring
    assert pricing.get_model_rates("gemini-3.8-flash-exp") == (0.75, 3.75)
    assert pricing.get_model_rates("flash") == (0.75, 3.75)
    assert pricing.get_model_rates("flash_lite") == (0.075, 0.30)

    # Gemini Pro
    assert pricing.get_model_rates("gemini-3.1-pro") == (2.00, 12.00)
    assert pricing.get_model_rates("gemini-2.5-pro") == (1.25, 10.00)
    assert pricing.get_model_rates("gemini-1.5-pro") == (1.25, 5.00)

    # Claude models
    assert pricing.get_model_rates("claude-3.7-sonnet") == (3.00, 15.00)
    assert pricing.get_model_rates("claude-3.5-sonnet") == (3.00, 15.00)

    # Fallback default
    assert pricing.get_model_rates("unknown-future-model") == (0.75, 3.75)
    assert pricing.get_model_rates("") == (0.75, 3.75)
    assert pricing.get_model_rates(None) == (0.75, 3.75)


def test_get_cache_savings_rate():
    assert pricing.get_cache_savings_rate("gemini-3.8-flash") == 0.675
    assert pricing.get_cache_savings_rate("gemini-2.5-flash") == 0.270
    assert pricing.get_cache_savings_rate("gemini-2.0-flash") == 0.1125
    assert pricing.get_cache_savings_rate("gemini-2.5-pro") == 1.125
    assert pricing.get_cache_savings_rate("gemini-3.1-pro") == 1.80
    assert pricing.get_cache_savings_rate("default") == 0.675


def test_calculate_cost_gemini_flash():
    # 1,000,000 prompt tokens @ $0.75/M = $0.75
    # 1,000,000 output tokens @ $3.75/M = $3.75
    # Total = $4.50
    cost = pricing.calculate_cost(1_000_000, 1_000_000, "gemini-3.8-flash")
    assert cost == 4.50


def test_calculate_cost_precision_and_rounding():
    # 2,160 prompt tokens @ $0.75/M = 0.001620
    # 672 output tokens @ $3.75/M = 0.002520
    # Total = 0.004140 -> rounded to 6 decimals: 0.00414
    cost = pricing.calculate_cost(2_160, 672, "gemini-3.8-flash")
    assert cost == 0.00414


def test_calculate_cost_zero_tokens():
    assert pricing.calculate_cost(0, 0, "gemini-3.8-flash") == 0.0


def test_format_step_cost_subcent_microcosts():
    # Micro-cost with context caching (Turn #3719)
    disp, tip = pricing.format_step_cost(0.000432)
    assert disp == "$0.0004"
    assert tip == "Exact: $0.000432 USD"

    # Micro-cost near 1 cent (Turn #3731 cache miss)
    disp, tip = pricing.format_step_cost(0.009080)
    assert disp == "$0.0091"
    assert tip == "Exact: $0.009080 USD"


def test_format_step_cost_standard_costs():
    # 5 cents
    disp, tip = pricing.format_step_cost(0.0512)
    assert disp == "$0.05"
    assert tip == "Exact: $0.051200 USD"

    # $1.25 Pro heavy output
    disp, tip = pricing.format_step_cost(1.254)
    assert disp == "$1.25"
    assert tip == "Exact: $1.254000 USD"


def test_format_step_cost_edge_cases():
    # Zero / free tier
    disp, tip = pricing.format_step_cost(0.0)
    assert disp == "$0.00"
    assert "free tier" in tip

    disp, tip = pricing.format_step_cost(None)
    assert disp == "$0.00"

    # Extreme sub-micro cost (< 0.0001)
    disp, tip = pricing.format_step_cost(0.000045)
    assert disp == "$0.000045"
    assert tip == "Exact: $0.000045 USD"

