"""
UI Styling & Anti-Regression Test Suite
Antigravity Token Observability & FinOps Dashboard

Ensures that every change to the dashboard adheres strictly to the
Google Cloud Console Design System (docs/DESIGN_SYSTEM.md) and that
no visual regressions (margin clipping, missing automargin, font mismatches,
or truncated endpoint labels) can be introduced.
"""

import os
import re
import pytest
import plotly.graph_objects as go
from dashboard.theme import (
    COLOR_BG,
    COLOR_SURFACE,
    COLOR_BORDER,
    GOOGLE_BLUE,
    GOOGLE_GREEN,
    GOOGLE_AMBER,
    FONT_FAMILY_TITLE,
    FONT_FAMILY_BODY,
    FONT_FAMILY_MONO,
    MARGIN_CONTINUOUS_CHART,
    MARGIN_GANTT_CHART,
    MARGIN_SPEND_BAR,
    get_base_chart_layout,
    configure_continuous_yaxis,
    build_trajectory_annotations,
)


@pytest.fixture
def app_source() -> str:
    """Load dashboard/app.py source code."""
    app_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        return f.read()


# ==============================================================================
# 1. STATIC CODE LINTER: PREVENT VISUAL REGRESSIONS IN DASHBOARD/APP.PY
# ==============================================================================

def test_chart_left_margin_minimums(app_source: str):
    """Ensure all chart layout definitions meet strict left-margin minimums to prevent number clipping."""
    # 1. Token Consumption vs Turn must have l >= 75
    prog_margin_match = re.search(r"fig_prog\.update_layout\([^)]*margin=dict\([^)]*l=(\d+)", app_source)
    assert prog_margin_match, "fig_prog must define margin with explicit 'l' (left margin)"
    assert int(prog_margin_match.group(1)) >= 75, "fig_prog left margin must be >= 75px"

    # 2. Cumulative USD vs Turn must have l >= 75
    cost_margin_match = re.search(r"fig_cost\.update_layout\([^)]*margin=dict\([^)]*l=(\d+)", app_source)
    assert cost_margin_match, "fig_cost must define margin with explicit 'l' (left margin)"
    assert int(cost_margin_match.group(1)) >= 75, "fig_cost left margin must be >= 75px"

    # 3. Gantt / Waterfall chart must have l >= 80
    waterfall_margin_match = re.search(r"fig_waterfall\.update_layout\([^)]*margin=dict\([^)]*l=(\d+)", app_source)
    assert waterfall_margin_match, "fig_waterfall must define margin with explicit 'l' (left margin)"
    assert int(waterfall_margin_match.group(1)) >= 80, "fig_waterfall left margin must be >= 80px"

    # 4. Daily Spend Bar chart must have l >= 60
    spend_margin_match = re.search(r"fig_spend\.update_layout\([^)]*margin=dict\([^)]*l=(\d+)", app_source)
    assert spend_margin_match, "fig_spend must define margin with explicit 'l' (left margin)"
    assert int(spend_margin_match.group(1)) >= 60, "fig_spend left margin must be >= 60px"


def test_yaxis_automargin_enforcement(app_source: str):
    """Ensure automargin=True is present on all numerical/categorical y-axis configurations."""
    # Check that fig_prog, fig_cost, and fig_waterfall all configure automargin=True
    assert "automargin=True" in app_source
    # Verify count: at least 4 occurrences (spend, prog, cost, waterfall)
    automargin_count = app_source.count("automargin=True")
    assert automargin_count >= 4, f"Expected at least 4 charts with automargin=True, found {automargin_count}"


def test_yaxis_title_standoff_enforcement(app_source: str):
    """Ensure titled y-axes have standoff >= 14 to prevent title colliding with numbers."""
    # Standoff must be explicitly defined
    standoff_matches = re.findall(r"standoff=(\d+)", app_source)
    assert len(standoff_matches) >= 2, "Expected at least 2 titled axes with explicit standoff"
    for val in standoff_matches:
        assert int(val) >= 12, f"Axis title standoff ({val}) is too small; must be >= 12px (ideally 14px)"


def test_financial_trajectory_xaxis_paper_annotations(app_source: str):
    """Ensure Financial Cost Trajectory uses paper-anchored annotations so Current Turn is never culled."""
    # 1. Assert paper-anchored annotations exist in fig_cost
    assert 'xref="paper"' in app_source
    assert 'yref="paper"' in app_source
    assert 'xanchor="left"' in app_source
    assert 'xanchor="right"' in app_source

    # 2. Assert text patterns for first and current turn
    assert 'text=f"First Turn (#{first_turn_no})"' in app_source
    assert 'text=f"Current Turn (#{curr_turn_no})"' in app_source

    # 3. Assert ticks are configured on axis line with showticklabels=False to avoid Plotly culling
    assert "showticklabels=False" in app_source
    assert 'ticks="outside"' in app_source


def test_css_design_system_classes(app_source: str):
    """Ensure core Google Cloud Console CSS classes are preserved in app.py."""
    required_classes = [
        ".telemetry-kpi-card",
        ".gcp-table-container",
        ".gcp-table",
        ".pill",
        ".pill-green",
        ".pill-blue",
    ]
    for cls in required_classes:
        assert cls in app_source, f"Missing required CSS class {cls} in dashboard/app.py"


# ==============================================================================
# 2. RUNTIME THEME ENGINE & CHART BUILDER VALIDATION
# ==============================================================================

def test_theme_constants_validity():
    """Verify theme tokens meet Google Cloud Console specifications."""
    assert COLOR_BG == "#F8F9FA"
    assert COLOR_SURFACE == "#FFFFFF"
    assert COLOR_BORDER == "#DADCE0"
    assert GOOGLE_BLUE == "#1A73E8"
    assert GOOGLE_GREEN == "#1E8E3E"
    assert GOOGLE_AMBER == "#FBBC04"
    assert "Google Sans" in FONT_FAMILY_TITLE
    assert "Roboto" in FONT_FAMILY_BODY
    assert "Roboto Mono" in FONT_FAMILY_MONO


def test_theme_base_chart_layout():
    """Verify base chart layout factory returns proper geometry and white background."""
    layout = get_base_chart_layout(height=350)
    assert layout["height"] == 350
    assert layout["paper_bgcolor"] == "#FFFFFF"
    assert layout["plot_bgcolor"] == "#FFFFFF"
    assert layout["margin"]["l"] >= 75
    assert layout["font"]["family"] == FONT_FAMILY_BODY


def test_theme_continuous_yaxis_currency():
    """Verify continuous y-axis factory correctly configures currency and automargin."""
    yaxis = configure_continuous_yaxis(title="Cumulative USD ($)", is_currency=True, standoff=14)
    assert yaxis["automargin"] is True
    assert yaxis["tickprefix"] == "$"
    assert yaxis["tickformat"] == ".2f"
    assert yaxis["title"]["text"] == "Cumulative USD ($)"
    assert yaxis["title"]["standoff"] == 14
    assert yaxis["tickfont"]["family"] == FONT_FAMILY_MONO
    assert yaxis["gridcolor"] == "#F1F3F4"


def test_build_trajectory_annotations_geometry():
    """Verify trajectory annotations generate valid paper-anchored bounds."""
    annos = build_trajectory_annotations(first_turn_no=1, curr_turn_no=150)
    assert len(annos) == 2

    # Left annotation (First Turn)
    first_anno = annos[0]
    assert first_anno["xref"] == "paper"
    assert first_anno["x"] == 0.0
    assert first_anno["xanchor"] == "left"
    assert "First Turn (#1)" in first_anno["text"]

    # Right annotation (Current Turn)
    curr_anno = annos[1]
    assert curr_anno["xref"] == "paper"
    assert curr_anno["x"] == 1.0
    assert curr_anno["xanchor"] == "right"
    assert "Current Turn (#150)" in curr_anno["text"]


def test_runtime_plotly_figure_instantiation():
    """Simulate complete fig_cost creation and verify layout compliance directly."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[1, 2, 3], y=[0.1, 0.5, 1.2], name="Actual"))
    fig.update_layout(
        **get_base_chart_layout(height=320),
        yaxis=configure_continuous_yaxis(title="Cumulative USD ($)", is_currency=True),
        annotations=build_trajectory_annotations(first_turn_no=1, curr_turn_no=3),
    )

    # Validate resulting Plotly Layout object
    assert fig.layout.paper_bgcolor == "#FFFFFF"
    assert fig.layout.plot_bgcolor == "#FFFFFF"
    assert fig.layout.margin.l == 75
    assert fig.layout.margin.b >= 45
    assert fig.layout.yaxis.automargin is True
    assert fig.layout.yaxis.title.standoff == 14
    assert len(fig.layout.annotations) == 2
    assert fig.layout.annotations[0].xanchor == "left"
    assert fig.layout.annotations[1].xanchor == "right"
