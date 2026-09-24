"""Model rate cards and cost estimation calculations."""

from typing import Dict, Tuple

# Rate card in USD per million tokens: (prompt_rate_per_m, output_rate_per_m)
RATE_CARDS: Dict[str, Tuple[float, float]] = {
    # Gemini 3.8 Flash (Active introductory rate through Dec 31, 2026: $0.75 prompt, $3.75 output)
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-3.5-flash": (0.75, 3.75),
    # Gemini 2.5 Flash ($0.30 prompt, $2.50 output)
    "gemini-2.5-flash": (0.30, 2.50),
    # Gemini 2.0 Flash ($0.15 prompt, $0.60 output)
    "gemini-2.0-flash": (0.15, 0.60),
    "flash": (0.75, 3.75),
    # Gemini Flash-Lite ($0.075 prompt, $0.30 output)
    "flash_lite": (0.075, 0.30),
    # Gemini Pro models
    "gemini-3.1-pro": (2.00, 12.00),
    "gemini-2.5-pro": (1.25, 10.00),
    "gemini-1.5-pro": (1.25, 5.00),
    "pro": (1.25, 10.00),
    # Claude models (if routed via Vertex / Antigravity)
    "claude-3.7-sonnet": (3.00, 15.00),
    "claude-3.5-sonnet": (3.00, 15.00),
    # Fallback / Default rate (Gemini 3.8 Flash baseline)
    "default": (0.75, 3.75),
}

# Context caching discount per 1M tokens: uncached_prompt_rate - cached_read_rate
CACHE_SAVINGS_PER_M: Dict[str, float] = {
    "gemini-3.8-flash": 0.675,   # $0.75 prompt - $0.075 cache read (90% discount)
    "gemini-3.6-flash": 0.675,
    "gemini-3.5-flash": 0.675,
    "gemini-2.5-flash": 0.270,   # $0.30 prompt - $0.030 cache read (90% discount)
    "gemini-2.0-flash": 0.1125,  # $0.15 prompt - $0.0375 cache read (75% discount)
    "flash": 0.675,
    "flash_lite": 0.05625,       # $0.075 prompt - $0.01875 cache read (75% discount)
    "gemini-3.1-pro": 1.80,      # $2.00 prompt - $0.20 cache read (90% discount)
    "gemini-2.5-pro": 1.125,     # $1.25 prompt - $0.125 cache read (90% discount)
    "gemini-1.5-pro": 0.9375,    # $1.25 prompt - $0.3125 cache read (75% discount)
    "pro": 1.125,
    "default": 0.675,
}


def get_model_rates(model_name: str) -> Tuple[float, float]:
    """Matches a model string to its corresponding rate card."""
    if not model_name:
        return RATE_CARDS["default"]

    model_lower = model_name.lower()
    for key in sorted(RATE_CARDS.keys(), key=len, reverse=True):
        if key != "default" and key in model_lower:
            return RATE_CARDS[key]

    return RATE_CARDS["default"]


def get_cache_savings_rate(model_name: str) -> float:
    """Returns the USD savings per 1M cached tokens compared to full prompt price."""
    if not model_name:
        return CACHE_SAVINGS_PER_M["default"]

    model_lower = model_name.lower()
    for key in sorted(CACHE_SAVINGS_PER_M.keys(), key=len, reverse=True):
        if key != "default" and key in model_lower:
            return CACHE_SAVINGS_PER_M[key]

    return CACHE_SAVINGS_PER_M["default"]


def calculate_cost(prompt_tokens: int, output_tokens: int, model_name: str) -> float:
    """Calculates estimated USD cost for a given step execution."""
    prompt_rate, output_rate = get_model_rates(model_name)
    prompt_cost = (prompt_tokens / 1_000_000.0) * prompt_rate
    output_cost = (output_tokens / 1_000_000.0) * output_rate
    return round(prompt_cost + output_cost, 6)


def format_step_cost(val: float) -> Tuple[str, str]:
    """Formats single-step LLM cost with adaptive precision and hover tooltip text.

    Args:
        val: Estimated cost in USD.

    Returns:
        Tuple of (display_string, tooltip_string).
        Examples:
        - 0.000432 -> ("$0.0004", "Exact: $0.000432 USD")
        - 0.009080 -> ("$0.0091", "Exact: $0.009080 USD")
        - 0.0512   -> ("$0.05", "Exact: $0.051200 USD")
        - 1.254    -> ("$1.25", "Exact: $1.254000 USD")
        - 0.000045 -> ("$0.000045", "Exact: $0.000045 USD")
        - 0.0      -> ("$0.00", "$0.000000 USD (free tier / zero cost)")
    """
    if val is None or val <= 0:
        return "$0.00", "$0.000000 USD (free tier / zero cost)"
    try:
        val = float(val)
    except (ValueError, TypeError):
        return str(val), str(val)

    tooltip = f"Exact: ${val:,.6f} USD"
    if val >= 0.01:
        display = f"${val:,.2f}"
    elif val >= 0.0001:
        display = f"${val:,.4f}"
    else:
        display = f"${val:,.6f}"
    return display, tooltip

