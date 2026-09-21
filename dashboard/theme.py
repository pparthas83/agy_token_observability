"""
Google Cloud Console Design System & Theme Engine
Antigravity Token Observability & FinOps Telemetry Dashboard

Authoritative source of design tokens, colors, typography, margins,
and chart layout standards across all views in the dashboard.
"""

from typing import Any, Dict, Optional

# --- 1. GOOGLE CLOUD BRAND & SEMANTIC PALETTE ---
COLOR_BG = "#F8F9FA"              # Google Cloud console surface background
COLOR_SURFACE = "#FFFFFF"         # Card and modal container background
COLOR_BORDER = "#DADCE0"          # Standard Google border
COLOR_BORDER_LIGHT = "#F1F3F4"    # Subtle divider / grid lines
COLOR_TEXT_PRIMARY = "#202124"    # Primary text (Google Sans / Roboto)
COLOR_TEXT_SECONDARY = "#5F6368"  # Secondary / muted text
COLOR_TEXT_CHARCOAL = "#3C4043"   # Axis labels, ticks, table body

# Semantic Google Colors
GOOGLE_BLUE = "#1A73E8"
GOOGLE_GREEN = "#1E8E3E"
GOOGLE_AMBER = "#FBBC04"
GOOGLE_RED = "#D93025"
GOOGLE_PURPLE = "#9334E6"
GOOGLE_GREY = "#80868B"

# Standard chart categorical palette
GOOGLE_CHART_COLORS = [
    "#1A73E8",  # Google Blue
    "#34A853",  # Google Green
    "#FBBC04",  # Google Yellow/Amber
    "#EA4335",  # Google Red
    "#9334E6",  # Google Purple
    "#12B5CB",  # Cyan
    "#FA7B17",  # Orange
    "#80868B",  # Google Grey
]

# --- 2. TYPOGRAPHY SYSTEM ---
FONT_FAMILY_TITLE = "Google Sans, sans-serif"
FONT_FAMILY_BODY = "Roboto, sans-serif"
FONT_FAMILY_MONO = "Roboto Mono, monospace"

# --- 3. CHART MARGIN STANDARDS ---
# Minimum left margins ensure formatted numbers ($0.00, 120k) are never clipped
MARGIN_CONTINUOUS_CHART = dict(l=75, r=25, t=10, b=45)
MARGIN_SPEND_BAR = dict(l=60, r=10, t=10, b=10)
MARGIN_DONUT = dict(l=10, r=10, t=10, b=10)
MARGIN_GANTT_CHART = dict(l=80, r=20, t=30, b=30)

# --- 4. REUSABLE CHART LAYOUT FACTORIES ---
def get_base_chart_layout(
    height: int = 320,
    margin: Optional[Dict[str, int]] = None,
    font_color: str = COLOR_TEXT_SECONDARY,
) -> Dict[str, Any]:
    """Return standard Google Cloud white-card chart layout base."""
    return dict(
        height=height,
        margin=margin or MARGIN_CONTINUOUS_CHART,
        paper_bgcolor=COLOR_SURFACE,
        plot_bgcolor=COLOR_SURFACE,
        font=dict(family=FONT_FAMILY_BODY, size=12, color=font_color),
    )


def configure_continuous_yaxis(
    title: Optional[str] = None,
    is_currency: bool = False,
    show_grid: bool = True,
    standoff: int = 14,
) -> Dict[str, Any]:
    """Generate standardized y-axis configuration with automargin and standoff."""
    yaxis_config: Dict[str, Any] = dict(
        automargin=True,
        showgrid=show_grid,
        gridcolor=COLOR_BORDER_LIGHT,
        linecolor=COLOR_BORDER,
        tickfont=dict(family=FONT_FAMILY_MONO, size=11, color=COLOR_TEXT_CHARCOAL),
    )
    if is_currency:
        yaxis_config["tickprefix"] = "$"
        yaxis_config["tickformat"] = ".2f"

    if title:
        yaxis_config["title"] = dict(
            text=title,
            standoff=standoff,
            font=dict(family=FONT_FAMILY_TITLE, size=12, color=COLOR_TEXT_CHARCOAL),
        )

    return yaxis_config


def build_trajectory_annotations(
    first_turn_no: int,
    curr_turn_no: int,
    y_pos: float = -0.08,
) -> list:
    """Build paper-anchored annotations for First Turn and Current Turn.

    Uses xref='paper' and explicit left/right anchoring to guarantee that
    'Current Turn (#...)' is never culled by Plotly and never overflows the container.
    """
    return [
        dict(
            xref="paper",
            yref="paper",
            x=0.0,
            y=y_pos,
            xanchor="left",
            yanchor="top",
            text=f"First Turn (#{first_turn_no})",
            showarrow=False,
            font=dict(size=11, family=FONT_FAMILY_TITLE, color=COLOR_TEXT_CHARCOAL),
        ),
        dict(
            xref="paper",
            yref="paper",
            x=1.0,
            y=y_pos,
            xanchor="right",
            yanchor="top",
            text=f"Current Turn (#{curr_turn_no})",
            showarrow=False,
            font=dict(size=11, family=FONT_FAMILY_TITLE, color=COLOR_TEXT_CHARCOAL),
        ),
    ]
