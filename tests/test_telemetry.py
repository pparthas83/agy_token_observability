"""Unit tests for Token Telemetry phase breakdowns, context extraction, and metrics."""

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


def test_sidebar_navigation_elements():
    """Verify left navigation panel branding, project scope, and button changes."""
    with open("dashboard/app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. System Telemetry section must be removed
    assert "SYSTEM TELEMETRY" not in content
    assert "BigQuery Stream Active" not in content

    # 2. Refresh Tokenomics Cache button with appropriate icon
    assert 'st.button("Refresh Tokenomics Cache", icon=":material/refresh:", use_container_width=True)' in content
    assert "Refresh BigQuery Cache" not in content

    # 3. Project scope must not contain Dataset or Cloud ID
    assert 'Cloud ID:' not in content
    assert 'Dataset:' not in content

    # 4. Argolis Account renamed to Cloud Account
    assert 'Argolis Account:' not in content
    assert 'Cloud Account:' in content
    assert 'Cloud Project:' in content

    # 5. Your Antigravity Token Analytics renamed to My Antigravity Token Analytics
    assert 'My Antigravity<br/>Token Analytics' in content
    assert 'My Antigravity Token Analytics' in content
    assert 'Your Antigravity' not in content


def test_light_theme_lock_and_plotly_legends():
    """Verify permanent light theme configuration, dropdown styling, and Plotly legend visibility."""
    import os

    # 1. Verify .streamlit/config.toml exists and locks base to light
    assert os.path.exists("dashboard/.streamlit/config.toml")
    with open("dashboard/.streamlit/config.toml", "r", encoding="utf-8") as f:
        config_content = f.read()
    assert 'base = "light"' in config_content
    assert 'primaryColor = "#1A73E8"' in config_content

    # 2. Verify dashboard/app.py enforces theme=None on plotly charts
    with open("dashboard/app.py", "r", encoding="utf-8") as f:
        app_content = f.read()

    assert 'st.plotly_chart(fig_spend, use_container_width=True, theme=None)' in app_content
    assert 'st.plotly_chart(fig_pie, use_container_width=True, theme=None)' in app_content
    assert 'st.plotly_chart(fig_prog, use_container_width=True, theme=None)' in app_content
    assert 'st.plotly_chart(fig_cost, use_container_width=True, theme=None)' in app_content
    assert 'st.plotly_chart(fig_waterfall, use_container_width=True, theme=None)' in app_content

    # 3. Verify CSS rules enforce Google Cloud light theme on selectboxes and popovers
    assert 'div[data-baseweb="select"]' in app_content
    assert 'div[data-baseweb="popover"]' in app_content
    assert 'background-color: #FFFFFF !important;' in app_content


def test_gantt_chart_yaxis_styling():
    """Verify Gantt chart (fig_waterfall) y-axis labels have adequate margin, automargin, and consistent styling."""
    with open("dashboard/app.py", "r", encoding="utf-8") as f:
        app_content = f.read()

    # 1. Left margin must be at least 80px to prevent clipping
    assert "margin=dict(l=80, r=20, t=30, b=30)" in app_content

    # 2. automargin=True must be enabled to dynamically adjust to multi-digit turn numbers
    assert "automargin=True" in app_content

    # 3. yaxis styling must use consistent charcoal color (#3C4043) and Roboto Mono
    assert 'tickfont=dict(family="Roboto Mono, monospace", size=11, color="#3C4043")' in app_content
    assert 'ticks="outside"' in app_content
    assert 'linecolor="#DADCE0"' in app_content


def test_github_setup_modal():
    """Verify GitHub repository link and setup guide modal exist and are configured correctly."""
    with open("dashboard/app.py", "r", encoding="utf-8") as f:
        app_content = f.read()

    # 1. Dialog decorator and modal function
    assert '@st.dialog("Antigravity Token Observability — Architecture & Setup Guide", width="large")' in app_content
    assert "def show_github_setup_modal():" in app_content

    # 2. GitHub repository links and branding
    assert "pparthas83 / agy_token_observability" in app_content
    assert "https://github.com/pparthas83/agy_token_observability" in app_content

    # 3. Breadcrumb row trigger button and prompt verbiage
    assert 'st.button("GitHub & Setup Guide", icon=":material/code:", use_container_width=True)' in app_content
    assert "Want to see your Antigravity metrics? Click this button" in app_content

    # 4. Step-by-step setup tabs
    assert "🚀 Quick Start" in app_content
    assert "⚡ Automated Hook Sync" in app_content
    assert "☁️ Cloud Run Deployment" in app_content
    assert "🏗️ Architecture & Schema" in app_content

    # 5. Generic placeholders (no personal project IDs in the modal)
    assert "YOUR_PROJECT_ID" in app_content
    # Ensure personal project ID is not in the modal code
    modal_code = app_content[app_content.find("def show_github_setup_modal():") : app_content.find("with st.sidebar:")]
    assert "pradeep-demo-1" not in modal_code
    assert "832497031659" not in modal_code

    # 6. Note callout section under View on GitHub box
    assert "Please follow these steps to get a similar dashboard up and running for your own personal antigravity instance" in modal_code
    assert "border-left: 4px solid #1A73E8" in modal_code


def test_sidebar_attribution_footer():
    """Verify left navigation sidebar attribution footer contains LDAP, full name, and technology credits."""
    with open("dashboard/app.py", "r", encoding="utf-8") as f:
        app_content = f.read()

    # 1. Author Name, LDAP & Concept / Ideation attribution
    assert "Concept &amp; Ideation by" in app_content
    assert "Pradeep Parthasarathy" in app_content
    assert "pradeepsarathy@google.com" in app_content

    # 2. Build attribution (Antigravity and Gemini)
    assert "Build by <strong style=\"color: #202124; font-weight: 600;\">Antigravity</strong> and <strong style=\"color: #202124; font-weight: 600;\">Gemini</strong>" in app_content


def test_repository_attribution_assets():
    """Verify LICENSE, CITATION.cff, and README.md attribution assets exist with Pradeep Parthasarathy."""
    import os

    # 1. Check LICENSE
    assert os.path.exists("LICENSE")
    with open("LICENSE", "r", encoding="utf-8") as f:
        license_text = f.read()
    assert "Apache License" in license_text
    assert "Copyright 2026 Pradeep Parthasarathy (pradeepsarathy@google.com)" in license_text

    # 2. Check CITATION.cff
    assert os.path.exists("CITATION.cff")
    with open("CITATION.cff", "r", encoding="utf-8") as f:
        cff_text = f.read()
  
    assert "family-names: \"Parthasarathy\"" in cff_text
    assert "given-names: \"Pradeep\"" in cff_text
    assert "email: \"pradeepsarathy@google.com\"" in cff_text

    # 3. Check README.md
    with open("README.md", "r", encoding="utf-8") as f:
        readme_text = f.read()
    assert "Pradeep Parthasarathy" in readme_text
    assert "pradeepsarathy@google.com" in readme_text
    assert "Apache_2.0" in readme_text



