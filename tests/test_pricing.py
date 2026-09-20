"""Unit tests for pricing.py rate card resolution and cost calculation."""

import pytest
import pricing


def test_get_model_rates_exact_and_fuzzy():
    # Exact match for Gemini Flash
    assert pricing.get_model_rates("gemini-3.8-flash") == (0.15, 0.60)
    assert pricing.get_model_rates("gemini-2.5-flash") == (0.15, 0.60)
    
    # Fuzzy match / substring
    assert pricing.get_model_rates("gemini-3.8-flash-exp") == (0.15, 0.60)
    assert pricing.get_model_rates("flash") == (0.15, 0.60)
    assert pricing.get_model_rates("flash_lite") == (0.075, 0.30)

    # Gemini Pro
    assert pricing.get_model_rates("gemini-3.8-pro") == (1.25, 5.00)
    assert pricing.get_model_rates("gemini-2.5-pro") == (1.25, 5.00)

    # Claude models
    assert pricing.get_model_rates("claude-3.7-sonnet") == (3.00, 15.00)
    assert pricing.get_model_rates("claude-3.5-sonnet") == (3.00, 15.00)

    # Fallback default
    assert pricing.get_model_rates("unknown-future-model") == (0.15, 0.60)
    assert pricing.get_model_rates("") == (0.15, 0.60)
    assert pricing.get_model_rates(None) == (0.15, 0.60)


def test_calculate_cost_gemini_flash():
    # 1,000,000 prompt tokens @ $0.15/M = $0.15
    # 1,000,000 output tokens @ $0.60/M = $0.60
    # Total = $0.75
    cost = pricing.calculate_cost(1_000_000, 1_000_000, "gemini-3.8-flash")
    assert cost == 0.75


def test_calculate_cost_precision_and_rounding():
    # 2,160 prompt tokens @ $0.15/M = 0.000324
    # 672 output tokens @ $0.60/M = 0.0004032
    # Total = 0.0007272 -> rounded to 6 decimals: 0.000727
    cost = pricing.calculate_cost(2_160, 672, "gemini-3.8-flash")
    assert cost == 0.000727


def test_calculate_cost_zero_tokens():
    assert pricing.calculate_cost(0, 0, "gemini-3.8-flash") == 0.0
