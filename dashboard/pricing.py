"""Model rate cards and cost estimation calculations."""

from typing import Dict, Tuple

# Rate card in USD per million tokens: (prompt_rate_per_m, output_rate_per_m)
RATE_CARDS: Dict[str, Tuple[float, float]] = {
    # Gemini Flash models
    "gemini-3.8-flash": (0.15, 0.60),
    "gemini-2.5-flash": (0.15, 0.60),
    "flash": (0.15, 0.60),
    "flash_lite": (0.075, 0.30),
    # Gemini Pro models
    "gemini-3.8-pro": (1.25, 5.00),
    "gemini-2.5-pro": (1.25, 5.00),
    "pro": (1.25, 5.00),
    # Claude models (if routed via Vertex / Antigravity)
    "claude-3.7-sonnet": (3.00, 15.00),
    "claude-3.5-sonnet": (3.00, 15.00),
    # Fallback / Default rate
    "default": (0.15, 0.60),
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

