import base64
import json
import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery

# Ensure project root is on sys.path for local helper modules
_proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

try:
    import context_extractor
except Exception:
    context_extractor = None

try:
    import pricing
    format_step_cost = pricing.format_step_cost
    get_cache_savings_rate = pricing.get_cache_savings_rate
except Exception:
    def format_step_cost(val):
        if val is None or val <= 0:
            return "$0.00", "$0.000000 USD (free tier / zero cost)"
        val = float(val)
        tip = f"Exact: ${val:,.6f} USD"
        disp = f"${val:,.2f}" if val >= 0.01 else (f"${val:,.4f}" if val >= 0.0001 else f"${val:,.6f}")
        return disp, tip

    def get_cache_savings_rate(model_name):
        return 0.675


# Resolve Antigravity Official Logo
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "antigravity_logo_clean.png")
if os.path.exists(LOGO_PATH):
    with open(LOGO_PATH, "rb") as f:
        LOGO_B64 = base64.b64encode(f.read()).decode("utf-8")
    LOGO_URI = f"data:image/png;base64,{LOGO_B64}"
else:
    LOGO_URI = "https://www.gstatic.com/images/branding/product/2x/cloud_64dp.png"

# Page Configuration
st.set_page_config(
    page_title="My Antigravity Token Analytics",
    page_icon=LOGO_PATH if os.path.exists(LOGO_PATH) else "⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Theme Styling (Google Cloud Light Palette & Antigravity Modern Aesthetic)
st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Roboto:wght@400;500;700&family=Roboto+Mono:wght@400;500&display=swap');

    /* Global Body and Background */
    html, body, [class*="css"], .stApp {
        background-color: #F8F9FA !important;
        color: #202124 !important;
        font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Hide Streamlit default chrome & headers */
    #MainMenu {visibility: hidden;}
    header[data-testid="stHeader"] {display: none !important;}
    footer {visibility: hidden;}
    .block-container {
        padding-top: 1.0rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }

    /* ======================================================== */
    /* HIDE SIDEBAR TOGGLE / COLLAPSE BUTTONS (PERMANENT DRAWER) */
    /* ======================================================== */
    [data-testid="stSidebarHeader"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stExpandSidebarButton"],
    [data-testid="collapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"],
    button[kind="headerNoPadding"],
    [data-testid="stSidebarResizeHandle"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        pointer-events: none !important;
    }

    /* Left Sidebar: Fixed permanent drawer aligned to top-left */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #DADCE0 !important;
    }
    [data-testid="stSidebarContent"] {
        padding-top: 0.8rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
    }
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.3rem !important;
    }

    /* ======================================================== */
    /* BULLETPROOF STREAMLIT RADIO CIRCLE REMOVAL & ALIGN LEFT   */
    /* ======================================================== */
    [data-testid="stRadio"] [data-testid="stRadioOption"] div[class*="e1mpz0hj4"],
    [data-testid="stRadio"] [data-testid="stRadioOption"] div[class*="e1mpz0hj5"],
    [data-testid="stRadio"] [data-testid="stRadioOption"] > div > div:first-child,
    [data-testid="stRadio"] [data-testid="stRadioOption"] input[type="radio"],
    [data-testid="stRadio"] [data-testid="stRadioOption"] span[data-baseweb="radio"],
    [data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {
        display: none !important;
    }

    /* Left Nav Menu Buttons: Aligned directly to top-left */
    [data-testid="stRadio"] {
        margin-left: 0 !important;
        padding-left: 0 !important;
        width: 100% !important;
    }
    [data-testid="stRadio"] [data-testid="stRadioGroup"] {
        align-items: flex-start !important;
        gap: 3px !important;
        width: 100% !important;
    }
    [data-testid="stRadio"] [data-testid="stRadioOption"],
    [data-testid="stRadio"] [role="radiogroup"] > label {
        padding: 9px 12px !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        border-radius: 6px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        background-color: transparent !important;
        border-left: 3px solid transparent !important;
    }

    [data-testid="stRadio"] [data-testid="stRadioOption"]:hover,
    [data-testid="stRadio"] [role="radiogroup"] > label:hover {
        background-color: #F1F3F4 !important;
    }

    /* Active Tab: Google Blue Accent */
    [data-testid="stRadio"] [data-testid="stRadioOption"][data-selected="true"],
    [data-testid="stRadio"] [data-testid="stRadioOption"]:has([data-selected="true"]),
    [data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked),
    [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
        background-color: #E8F0FE !important;
        border-left: 3px solid #1A73E8 !important;
    }

    [data-testid="stRadio"] [data-testid="stRadioOption"][data-selected="true"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stRadio"] [data-testid="stRadioOption"]:has(input:checked) [data-testid="stMarkdownContainer"] p,
    [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {
        color: #1967D2 !important;
        font-weight: 600 !important;
    }

    [data-testid="stRadio"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"],
    [data-testid="stRadio"] [data-testid="stRadioOption"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stRadio"] [role="radiogroup"] > label p {
        font-family: 'Google Sans', sans-serif !important;
        font-size: 13.5px !important;
        font-weight: 500 !important;
        color: #3C4043 !important;
        margin: 0 !important;
        text-align: left !important;
        width: 100% !important;
    }

    /* Button Styling */
    div[data-testid="stButton"] > button {
        background-color: #FFFFFF !important;
        color: #1A73E8 !important;
        border: 1px solid #DADCE0 !important;
        border-radius: 4px !important;
        font-family: 'Google Sans', sans-serif !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 7px 14px !important;
        box-shadow: 0 1px 2px rgba(60,64,67,0.08) !important;
        transition: all 0.15s ease !important;
        width: 100% !important;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #F8F9FA !important;
        border-color: #1A73E8 !important;
        box-shadow: 0 1px 3px rgba(60,64,67,0.18) !important;
        color: #174EA6 !important;
    }

    /* ======================================================== */
    /* GOOGLE CLOUD CONSOLE SELECTBOX & DROPDOWN ENFORCEMENT    */
    /* ======================================================== */
    div[data-testid="stSelectbox"] {
        background-color: transparent !important;
    }
    div[data-testid="stSelectbox"] label p {
        color: #5F6368 !important;
        font-family: 'Google Sans', sans-serif !important;
        font-size: 12px !important;
        font-weight: 500 !important;
    }
    div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border-radius: 4px !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #DADCE0 !important;
        border-radius: 4px !important;
        color: #202124 !important;
        min-height: 38px !important;
    }
    div[data-baseweb="select"] > div:hover {
        border-color: #1A73E8 !important;
    }
    div[data-baseweb="select"] * {
        color: #202124 !important;
        font-family: 'Roboto', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    div[data-baseweb="select"] svg {
        fill: #5F6368 !important;
    }
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    ul[role="listbox"] {
        background-color: #FFFFFF !important;
        border: 1px solid #DADCE0 !important;
        box-shadow: 0 4px 12px rgba(60,64,67,0.15) !important;
    }
    li[role="option"] {
        background-color: #FFFFFF !important;
        color: #202124 !important;
    }
    li[role="option"]:hover,
    li[role="option"][aria-selected="true"] {
        background-color: #E8F0FE !important;
        color: #1A73E8 !important;
    }
    li[role="option"] * {
        color: #202124 !important;
    }
    li[role="option"][aria-selected="true"] * {
        color: #1A73E8 !important;
    }

    /* Sleek Cards */
    /* Base GCP Card */
    .gcp-card {
        background-color: #FFFFFF;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.1), 0 1px 3px 1px rgba(60,64,67,0.05);
        transition: all 0.2s ease-in-out;
        box-sizing: border-box;
    }
    .gcp-card:hover {
        box-shadow: 0 4px 12px 0 rgba(60,64,67,0.12);
        border-color: #BDC1C6;
    }

    /* Standardized 5-Column KPI Metric Cards (Strict height & alignment) */
    .kpi-card {
        background-color: #FFFFFF;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.1), 0 1px 3px 1px rgba(60,64,67,0.05);
        transition: all 0.2s ease-in-out;
        height: 140px;
        min-height: 140px;
        max-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
        overflow: hidden;
    }
    .kpi-card:hover {
        box-shadow: 0 4px 12px 0 rgba(60,64,67,0.12);
        border-color: #BDC1C6;
    }

    /* Column equal stretch */
    div[data-testid="column"] {
        display: flex;
        flex-direction: column;
    }
    div[data-testid="column"] > div {
        flex: 1;
        display: flex;
        flex-direction: column;
    }

    .kpi-title {
        font-size: 0.72rem;
        font-weight: 600;
        color: #5F6368;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
        font-family: 'Roboto', sans-serif;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #202124;
        font-family: 'Google Sans', sans-serif;
        line-height: 1.1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .kpi-icon-container {
        width: 36px;
        height: 36px;
        min-width: 36px;
        min-height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 17px;
        flex-shrink: 0;
        box-sizing: border-box;
    }

    /* Executive Summary Banner */
    .gcp-recommendation-banner {
        background-color: #E8F0FE;
        border: 1px solid #D2E3FC;
        border-left: 4px solid #1A73E8;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 22px;
        display: flex;
        align-items: flex-start;
        gap: 14px;
    }
    .gcp-recommendation-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #174EA6;
        font-family: 'Google Sans', sans-serif;
        margin-bottom: 4px;
    }
    .gcp-recommendation-text {
        font-size: 0.85rem;
        color: #202124;
        line-height: 1.55;
    }

    /* Custom Table Styling */
    .gcp-table-container {
        background: #FFFFFF;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.1);
        overflow-x: auto;
    }
    .gcp-scrollable-table {
        max-height: 480px;
        overflow-y: auto;
        border: 1px solid #DADCE0;
        border-radius: 6px;
    }
    .gcp-scrollable-table thead th {
        position: sticky;
        top: 0;
        background-color: #F8F9FA;
        z-index: 5;
        box-shadow: 0 1px 2px rgba(60,64,67,0.08);
    }
    .gcp-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        text-align: left;
    }
    .gcp-table th {
        background-color: #F8F9FA;
        color: #5F6368;
        font-weight: 600;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 10px 14px;
        border-bottom: 1px solid #DADCE0;
    }
    .gcp-table td {
        padding: 12px 14px;
        border-bottom: 1px solid #F1F3F4;
        color: #202124;
    }
    .gcp-table tr:hover td {
        background-color: #F8F9FA;
    }

    /* Pill Badges */
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
        line-height: 1.2;
    }
    .pill-blue { background: #E8F0FE; color: #1967D2; }
    .pill-green { background: #E6F4EA; color: #137333; }
    .pill-amber { background: #FEF7E0; color: #B06000; }
    .pill-purple { background: #F3E8FD; color: #8430CE; }

    /* Custom progress bar in table */
    .progress-bar-bg {
        background-color: #E8EAED;
        border-radius: 4px;
        height: 6px;
        width: 70px;
        display: inline-block;
        vertical-align: middle;
        overflow: hidden;
        margin-left: 8px;
    }
    .progress-bar-fill {
        background-color: #1A73E8;
        height: 100%;
        border-radius: 4px;
    }

    /* Telemetry Waterfall & Context Map Scoped Styles */
    .telemetry-header-bar {
        background: #FFFFFF;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 2px rgba(60,64,67,0.06);
    }
    .telemetry-kpi-card {
        background: #FFFFFF;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(60,64,67,0.08);
        min-height: 110px;
        max-height: 110px;
        height: 110px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-sizing: border-box;
    }
    .context-card {
        background: #FFFFFF;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(60,64,67,0.06);
        box-sizing: border-box;
        height: 100%;
    }
    .context-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: 'Google Sans', sans-serif;
        font-size: 13px;
        font-weight: 700;
        color: #202124;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #F1F3F4;
    }
    .context-card-item {
        font-size: 12px;
        color: #3C4043;
        line-height: 1.5;
        margin-bottom: 7px;
        display: flex;
        align-items: flex-start;
        gap: 6px;
    }
    .context-card-badge {
        display: inline-block;
        padding: 2px 7px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        font-family: 'Roboto Mono', monospace;
    }
    .context-footprint-container {
        background: #FFFFFF;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px rgba(60,64,67,0.06);
    }
    .context-bar-segmented {
        display: flex;
        width: 100%;
        height: 14px;
        border-radius: 7px;
        overflow: hidden;
        margin-top: 10px;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# GCP CONTEXT & ARGOLIS LDAP RESOLUTION (DYNAMIC & DE-IDENTIFIED)
# ==========================================
import google.auth


def get_active_gcp_context():
    """Dynamically resolves GCP project ID, Argolis account, and LDAP login without hardcoded values."""
    # 1. Project ID
    project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        try:
            _, detected = google.auth.default()
            if detected:
                project_id = detected
        except Exception:
            pass
    active_project = project_id or "default-project"
    dataset_id = os.environ.get("BQ_DATASET", "token_analytics")

    # 2. Argolis LDAP & Account Resolution
    ldap = os.environ.get("ARGOLIS_LDAP") or os.environ.get("CLOUD_ID")
    account = os.environ.get("ARGOLIS_ACCOUNT") or os.environ.get("USER_EMAIL")

    if not ldap or not account:
        try:
            client = bigquery.Client(project=active_project)
            query = f"SELECT user_email FROM `{active_project}.{dataset_id}.antigravity_token_events` WHERE user_email IS NOT NULL GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 1"
            rows = list(client.query(query).result())
            if rows and rows[0].user_email:
                account = str(rows[0].user_email).strip()
        except Exception:
            pass

    if not account:
        try:
            import subprocess
            res = subprocess.run(["gcloud", "config", "get-value", "account"], capture_output=True, text=True, timeout=1.5)
            if res.returncode == 0 and res.stdout.strip():
                account = res.stdout.strip()
        except Exception:
            pass

    if not ldap and account:
        if "altostrat.com" in account:
            parts = account.split("@")
            if len(parts) > 1:
                ldap = parts[1].split(".")[0]
        elif "@" in account:
            ldap = account.split("@")[0]
        else:
            ldap = account

    if not ldap:
        try:
            import getpass
            u = getpass.getuser()
            if u and u != "root":
                ldap = u
        except Exception:
            pass

    ldap = ldap or "argolis-user"
    account = account or f"{ldap}@altostrat.com"

    return active_project, ldap, account


GCP_PROJECT, CLOUD_ID, ARGOLIS_ACCOUNT = get_active_gcp_context()
DATASET_ID = os.environ.get("BQ_DATASET", "token_analytics")


@st.cache_resource
def get_bq_client():
    return bigquery.Client(project=GCP_PROJECT)


def run_query(query: str) -> pd.DataFrame:
    client = get_bq_client()
    job_config = bigquery.QueryJobConfig(
        labels={"datacloud": "antigravity", "app": "token-dashboard"}
    )
    return client.query(query, job_config=job_config).to_dataframe()


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


# ==========================================
# DATA LOADING FUNCTIONS
# ==========================================
@st.cache_data(ttl=60)
def load_executive_kpis():
    query = f"""
    SELECT
        COUNT(DISTINCT antigravity_project_name) as total_projects,
        COUNT(DISTINCT workspace_name) as total_workspaces,
        COUNT(DISTINCT conversation_id) as total_conversations,
        COUNT(*) as total_steps,
        SUM(total_tokens) as grand_total_tokens,
        SUM(prompt_tokens) as total_prompt_tokens,
        SUM(output_tokens) as total_output_tokens,
        SUM(thinking_tokens) as total_thinking_tokens,
        ROUND(SUM(estimated_cost_usd), 4) as total_spend_usd,
        ROUND(AVG(tokens_per_second), 1) as avg_speed,
        ROUND(AVG(ttft_latency_ms), 0) as avg_ttft_ms
    FROM `{GCP_PROJECT}.{DATASET_ID}.antigravity_token_events`
    """
    return run_query(query).iloc[0]


@st.cache_data(ttl=60)
def load_daily_spend():
    query = f"""
    SELECT
        usage_date,
        antigravity_project_name,
        model,
        active_conversations,
        daily_total_tokens,
        daily_prompt_tokens,
        daily_output_tokens,
        daily_thinking_tokens,
        daily_spend_usd
    FROM `{GCP_PROJECT}.{DATASET_ID}.v_daily_project_spend`
    ORDER BY usage_date ASC
    """
    return run_query(query)


@st.cache_data(ttl=60)
def load_project_portfolio():
    query = f"""
    SELECT
        antigravity_project_name,
        COUNT(DISTINCT conversation_id) as conversations,
        COUNT(*) as total_turns,
        SUM(total_tokens) as total_tokens,
        SUM(prompt_tokens) as prompt_tokens,
        SUM(output_tokens) as output_tokens,
        ROUND(SUM(estimated_cost_usd), 4) as cost_usd,
        ROUND(AVG(tokens_per_second), 1) as avg_tokens_per_second,
        ROUND(AVG(ttft_latency_ms), 0) as avg_ttft_ms
    FROM `{GCP_PROJECT}.{DATASET_ID}.antigravity_token_events`
    GROUP BY 1
    ORDER BY cost_usd DESC
    """
    return run_query(query)


@st.cache_data(ttl=60)
def load_deepdive_projects():
    query = f"""
    SELECT
        antigravity_project_name,
        COUNT(DISTINCT conversation_id) as conversations,
        COUNT(*) as total_turns,
        SUM(total_tokens) as total_tokens,
        SUM(COALESCE(cached_tokens, 0)) as cached_tokens,
        SUM(prompt_tokens) as prompt_tokens,
        SUM(output_tokens) as output_tokens,
        SUM(COALESCE(thinking_tokens, 0)) as thinking_tokens,
        ROUND(SUM(estimated_cost_usd), 4) as cost_usd
    FROM `{GCP_PROJECT}.{DATASET_ID}.antigravity_token_events`
    WHERE antigravity_project_name IS NOT NULL
    GROUP BY 1
    ORDER BY cost_usd DESC
    """
    return run_query(query)


@st.cache_data(ttl=60)
def load_conversations_for_project(project_name: str):
    query = f"""
    SELECT
        conversation_id,
        MIN(timestamp) as start_time,
        MAX(timestamp) as end_time,
        COUNT(*) as turns,
        SUM(COALESCE(cached_tokens, 0) + 
            CASE 
              WHEN prompt_tokens >= COALESCE(cached_tokens, 0) THEN prompt_tokens - COALESCE(cached_tokens, 0)
              ELSE prompt_tokens 
            END + 
            output_tokens) as total_tokens,
        SUM(COALESCE(cached_tokens, 0)) as cached_tokens,
        SUM(CASE 
              WHEN prompt_tokens >= COALESCE(cached_tokens, 0) THEN prompt_tokens - COALESCE(cached_tokens, 0)
              ELSE prompt_tokens 
            END) as uncached_prompt_tokens,
        SUM(prompt_tokens) as prompt_tokens,
        SUM(output_tokens) as output_tokens,
        SUM(COALESCE(thinking_tokens, 0)) as thinking_tokens,
        ROUND(SUM(estimated_cost_usd), 4) as cost_usd,
        ANY_VALUE(model) as primary_model
    FROM `{GCP_PROJECT}.{DATASET_ID}.antigravity_token_events`
    WHERE antigravity_project_name = '{project_name}'
    GROUP BY conversation_id
    ORDER BY start_time DESC
    """
    return run_query(query)


@st.cache_data(ttl=60)
def load_turns_for_conversation(conversation_id: str):
    query = f"""
    SELECT
        step_index,
        timestamp,
        model,
        prompt_tokens,
        COALESCE(cached_tokens, 0) as cached_tokens,
        CASE 
          WHEN prompt_tokens >= COALESCE(cached_tokens, 0) THEN prompt_tokens - COALESCE(cached_tokens, 0)
          ELSE prompt_tokens 
        END as uncached_prompt_tokens,
        output_tokens,
        COALESCE(thinking_tokens, 0) as thinking_tokens,
        GREATEST(0, output_tokens - COALESCE(thinking_tokens, 0)) as content_tokens,
        (COALESCE(cached_tokens, 0) + 
         CASE 
           WHEN prompt_tokens >= COALESCE(cached_tokens, 0) THEN prompt_tokens - COALESCE(cached_tokens, 0)
           ELSE prompt_tokens 
         END + 
         output_tokens) as total_tokens,
        latency_ms,
        tokens_per_second,
        ROUND(estimated_cost_usd, 6) as cost_usd,
        tool_name,
        step_type
    FROM `{GCP_PROJECT}.{DATASET_ID}.antigravity_token_events`
    WHERE conversation_id = '{conversation_id}'
    ORDER BY step_index ASC
    """
    return run_query(query)


@st.cache_data(ttl=60)
def load_telemetry_for_conversation(conversation_id: str):
    query = f"""
    SELECT
        step_index,
        timestamp,
        model,
        prompt_tokens,
        COALESCE(cached_tokens, 0) as cached_tokens,
        CASE 
          WHEN prompt_tokens >= COALESCE(cached_tokens, 0) THEN prompt_tokens - COALESCE(cached_tokens, 0)
          ELSE prompt_tokens 
        END as uncached_prompt_tokens,
        output_tokens,
        COALESCE(thinking_tokens, 0) as thinking_tokens,
        GREATEST(0, output_tokens - COALESCE(thinking_tokens, 0)) as content_tokens,
        (COALESCE(cached_tokens, 0) + 
         CASE 
           WHEN prompt_tokens >= COALESCE(cached_tokens, 0) THEN prompt_tokens - COALESCE(cached_tokens, 0)
           ELSE prompt_tokens 
         END + 
         output_tokens) as total_tokens,
        COALESCE(client_prep_ms, 0) as client_prep_ms,
        COALESCE(ttft_latency_ms, latency_ms, 0) as ttft_latency_ms,
        COALESCE(generation_duration_ms, 0) as generation_duration_ms,
        latency_ms,
        tokens_per_second,
        ROUND(estimated_cost_usd, 6) as cost_usd,
        tool_name,
        step_type,
        context_metadata
    FROM `{GCP_PROJECT}.{DATASET_ID}.antigravity_token_events`
    WHERE conversation_id = '{conversation_id}'
    ORDER BY step_index ASC
    """
    return run_query(query)


# ==========================================
# GITHUB & SETUP GUIDE MODAL DIALOG
# ==========================================
@st.dialog("Antigravity Token Observability — Architecture & Setup Guide", width="large")
def show_github_setup_modal():
    """Modal dialog displaying repository links, architecture, and step-by-step setup guide."""
    st.html(
        """
        <div style="display: flex; align-items: center; justify-content: space-between; background: #F8F9FA; border: 1px solid #DADCE0; border-radius: 8px; padding: 12px 16px; margin-bottom: 12px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <svg height="28" width="28" viewBox="0 0 16 16" fill="#202124">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                <div>
                    <div style="font-weight: 700; font-size: 14px; color: #202124; font-family: 'Google Sans', sans-serif;">pparthas83 / agy_token_observability</div>
                    <div style="font-size: 11px; color: #5F6368; font-family: 'Roboto', sans-serif;">Concept &amp; Ideation: <strong>Pradeep Parthasarathy</strong> (pradeepsarathy@google.com) &bull; Build: Antigravity &amp; Gemini</div>
                </div>
            </div>
            <a href="https://github.com/pparthas83/agy_token_observability" target="_blank" style="text-decoration: none;">
                <button style="display: flex; align-items: center; gap: 6px; background: #1A73E8; color: #FFFFFF; border: none; border-radius: 4px; padding: 7px 16px; font-size: 12px; font-weight: 500; font-family: 'Google Sans', sans-serif; cursor: pointer; box-shadow: 0 1px 2px rgba(60,64,67,0.15);">
                    View on GitHub ↗
                </button>
            </a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px; background: #E8F0FE; border: 1px solid #D2E3FC; border-left: 4px solid #1A73E8; border-radius: 6px; padding: 10px 14px; margin-bottom: 16px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#1A73E8" style="flex-shrink: 0;">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
            </svg>
            <div style="font-size: 12.5px; color: #202124; font-family: 'Google Sans', sans-serif; line-height: 1.45;">
                <strong style="color: #174EA6; font-weight: 600;">Note:</strong> Please follow these steps to get a similar dashboard up and running for your own personal antigravity instance.
            </div>
        </div>
        """
    )

    tab_selfservice, tab_manual, tab_deploy, tab_arch = st.tabs(
        ["⚡ 1-Click Self-Service (Recommended)", "🛠️ Manual Setup", "☁️ Cloud Run Deployment", "🏗️ Architecture & Schema"]
    )

    with tab_selfservice:
        st.markdown("### ⚡ Zero-Touch Self-Service Setup")
        st.markdown(
            """
Run this single command in your workstation terminal. It fully automates local environment setup, registers the Antigravity `Stop` lifecycle hook, and provisions the BigQuery fact table and views in **your own Google Cloud project**:
            """
        )
        st.code(
            """curl -sSL https://raw.githubusercontent.com/pparthas83/agy_token_observability/main/install.sh | bash""",
            language="bash",
        )

        st.markdown("#### What This Single Command Does Automatically:")
        st.markdown(
            """
1. **Detects Your Google Cloud Project**: Reads active `gcloud` project configuration and validates Application Default Credentials (`gcloud auth application-default login`).
2. **Provisions BigQuery in Your Cloud Account**: Automatically creates the `token_analytics` dataset, the 26-column **DAY-partitioned & clustered** `antigravity_token_events` fact table, and two analytical views (`v_conversation_rollup`, `v_daily_project_spend`).
3. **Bootstraps Isolated Telemetry Client**: Clones into `~/.antigravity-observability` and builds a hermetic Python virtual environment with fast `uv` or `pip`.
4. **Registers Antigravity Lifecycle Hook**: Idempotently adds the `Stop` hook into `~/.gemini/config/hooks.json` so every coding turn streams telemetry automatically at session completion without slowing down your IDE.
            """
        )

        st.markdown("#### Optional Command-Line Flags:")
        st.code(
            """# Specify custom GCP project or dataset
curl -sSL https://raw.githubusercontent.com/pparthas83/agy_token_observability/main/install.sh | bash -s -- --project=MY_GCP_PROJECT --dataset=token_analytics""",
            language="bash",
        )

        st.markdown("#### Useful Management Commands:")
        st.code(
            """# Test stream extraction with dry-run (no BigQuery write)
~/.antigravity-observability/.venv/bin/python3 ~/.antigravity-observability/stream_to_bq.py --dry-run

# Backfill all existing conversations on your machine into BigQuery
~/.antigravity-observability/.venv/bin/python3 ~/.antigravity-observability/stream_to_bq.py --backfill

# Clean uninstall at any time (removes hook and installation directory)
~/.antigravity-observability/uninstall.sh""",
            language="bash",
        )

    with tab_manual:
        st.markdown("### 1. Prerequisites")
        st.markdown(
            """
- **Python**: Python 3.10+ (with [`uv`](https://github.com/astral-sh/uv) recommended or standard `pip`)
- **Google Cloud SDK**: [`gcloud`](https://cloud.google.com/sdk/docs/install) CLI installed and authenticated
- **GCP Project**: Active project with BigQuery enabled (`YOUR_PROJECT_ID`)
            """
        )

        st.markdown("### 2. Clone Repository & Setup Environment")
        st.code(
            """git clone https://github.com/pparthas83/agy_token_observability.git
cd agy_token_observability

# Install dependencies using uv (fastest)
uv sync

# Or using standard pip
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt""",
            language="bash",
        )

        st.markdown("### 3. Authenticate with Google Cloud ADC & Provision BigQuery")
        st.code(
            """gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID

# Initialize BigQuery dataset, partitioned table, and views
uv run python stream_to_bq.py --init-schema""",
            language="bash",
        )

        st.markdown("### 4. Register Antigravity Lifecycle Hook")
        st.markdown(
            "Add the `Stop` hook to `~/.gemini/config/hooks.json` to stream telemetry at the end of each agent turn:"
        )
        st.code(
            """{
  "token-observability": {
    "enabled": true,
    "Stop": [
      {
        "type": "command",
        "command": "/path/to/agy_token_observability/run_hook.sh",
        "timeout": 30
      }
    ]
  }
}""",
            language="json",
        )

        st.markdown("### 5. Launch Observability Dashboard Locally")
        st.code(
            """cd dashboard
uv run streamlit run app.py""",
            language="bash",
        )

    with tab_deploy:
        st.markdown("### Deploy to Google Cloud Run")
        st.markdown(
            """
Deploy the dashboard container directly to Google Cloud Run for an enterprise-ready, serverless observability portal with automatic autoscaling.
            """
        )
        st.markdown("#### 1. Single-Command Cloud Run Deployment")
        st.code(
            """CLOUDSDK_METRICS_ENVIRONMENT=datacloud.antigravity gcloud run deploy antigravity-token-dashboard \\
  --source dashboard \\
  --region us-central1 \\
  --project YOUR_PROJECT_ID \\
  --allow-unauthenticated""",
            language="bash",
        )

        st.markdown("#### 2. IAM & Service Account Configuration")
        st.markdown(
            "Ensure the Cloud Run default compute service account has BigQuery read and job creation privileges:"
        )
        st.code(
            """# Grant BigQuery Data Viewer and Job User roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \\
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \\
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \\
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \\
  --role="roles/bigquery.jobUser" """,
            language="bash",
        )

    with tab_arch:
        st.markdown("### 3-Tier Enterprise Token Observability Pipeline")
        st.markdown(
            """
```
+------------------------------------+
| Workstation Antigravity Execution  |
| - ~/.gemini/antigravity/           |
| - conversations.db (SQLite)        |
| - Step Transcripts & Tool Telemetry|
+-----------------+------------------+
                  |
                  v
+-----------------+------------------+
| Streaming & FinOps Ingestion Engine|
| - stream_to_bq.py                  |
| - pricing.py (Flash/Pro amortized) |
| - Token Classification (Cache/Think|
+-----------------+------------------+
                  |
                  v
+-----------------+------------------+
| Google BigQuery Data Lakehouse     |
| - YOUR_PROJECT_ID                  |
| - antigravity_tokenomics           |
|   .antigravity_token_events        |
| - Partitioned & Clustered by Date  |
+-----------------+------------------+
                  |
                  v
+-----------------+------------------+
| Google Cloud Run Dashboard         |
| - antigravity-token-dashboard      |
| - Executive Overview (Spend KPIs)  |
| - Tokenomics Deep Dive             |
| - Gantt Sequential Telemetry       |
+------------------------------------+
```
            """
        )

        st.markdown("### Key BigQuery Columns (`antigravity_token_events`)")
        st.markdown(
            """
| Column | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `TIMESTAMP` | UTC event execution timestamp (partition column) |
| `conversation_id` | `STRING` | Antigravity session UUID |
| `step_index` | `INT64` | Sequential execution turn index |
| `antigravity_project_name` | `STRING` | Clean workspace codebase identifier |
| `model` | `STRING` | Gemini model name (e.g., `gemini-2.5-flash`, `gemini-2.5-pro`) |
| `total_prompt_tokens` | `INT64` | Total input context window tokens |
| `cached_tokens` | `INT64` | Context cache hits (95% discounted input) |
| `fresh_input_tokens` | `INT64` | Fresh non-cached input tokens |
| `output_tokens` | `INT64` | Total generated tokens (thinking + content) |
| `thinking_tokens` | `INT64` | Internal chain-of-thought reasoning tokens |
| `content_tokens` | `INT64` | User-facing answer / code generation tokens |
| `estimated_cost_usd` | `FLOAT64` | Exact blended API cost calculated via official pricing |
| `cached_savings_usd` | `FLOAT64` | Net dollars saved by context caching |
| `ttft_latency_ms` | `INT64` | Time-to-First-Token prefill latency |
| `generation_duration_ms` | `INT64` | Output generation duration in milliseconds |
            """
        )


# ==========================================
# LEFT NAVIGATION PANEL
# ==========================================
with st.sidebar:
    # 1. Antigravity Official Brand Header
    st.html(
        f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 4px 0 14px 0; border-bottom: 1px solid #DADCE0; margin-bottom: 14px;">
            <img src="{LOGO_URI}" width="32" height="32" style="object-fit: contain;" alt="Antigravity Logo" />
            <div style="font-size: 14px; font-weight: 700; color: #202124; font-family: 'Google Sans', sans-serif; line-height: 1.25;">
                My Antigravity<br/>Token Analytics
            </div>
        </div>
        """
    )

    # 3. Project Scope Card (Mentions Cloud Project & Cloud Account in uniform styling)
    st.html(
        f"""
        <div style="background: #F8F9FA; border: 1px solid #DADCE0; border-radius: 6px; padding: 10px 12px; margin-bottom: 14px; font-size: 12px;">
            <div style="color: #5F6368; font-size: 10px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.6px; margin-bottom: 8px; font-family: 'Google Sans', sans-serif;">
                PROJECT SCOPE
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #5F6368; font-size: 11px; font-weight: 500; font-family: 'Google Sans', sans-serif;">Cloud Project:</span>
                    <span style="font-weight: 600; color: #202124; font-family: 'Roboto Mono', monospace; font-size: 11px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{GCP_PROJECT}">{GCP_PROJECT}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #5F6368; font-size: 11px; font-weight: 500; font-family: 'Google Sans', sans-serif;">Cloud Account:</span>
                    <span style="font-weight: 600; color: #202124; font-family: 'Roboto Mono', monospace; font-size: 11px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{ARGOLIS_ACCOUNT}">{ARGOLIS_ACCOUNT}</span>
                </div>
            </div>
        </div>
        """
    )

    st.html('<div style="font-size: 10px; font-weight: 700; color: #5F6368; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; padding-left: 2px; font-family: \'Google Sans\', sans-serif;">NAVIGATION</div>')

    # 2. Navigation Menus aligned to top-left
    selected_nav = st.radio(
        "NAVIGATION",
        [
            "📊  Executive Overview",
            "🔬  Tokenomics Deep Dive",
            "⚡  Token Telemetry",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
    if st.button("Refresh Tokenomics Cache", icon=":material/refresh:", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # 4. Attribution & Creator Badge
    st.html(
        """
        <div style="margin-top: 24px; padding-top: 14px; border-top: 1px solid #DADCE0;">
            <div style="background: #F8F9FA; border: 1px solid #DADCE0; border-radius: 6px; padding: 10px 12px; display: flex; flex-direction: column; gap: 8px;" title="Concept &amp; Ideation by Pradeep Parthasarathy (pradeepsarathy@google.com) • Build by Antigravity and Gemini">
                <div style="display: flex; align-items: flex-start; gap: 8px;">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="#5F6368" style="margin-top: 2px; flex-shrink: 0;">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                    </svg>
                    <div style="font-size: 11px; color: #5F6368; font-family: 'Google Sans', sans-serif; line-height: 1.35;">
                        Concept &amp; Ideation by <span style="font-weight: 600; color: #202124;">Pradeep Parthasarathy</span> <span style="color: #5F6368; font-family: 'Roboto Mono', monospace; font-size: 10.5px;">(pradeepsarathy@google.com)</span>
                    </div>
                </div>
                <div style="border-top: 1px solid #E8EAED; padding-top: 6px; display: flex; align-items: center; gap: 8px;">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="#1A73E8" style="flex-shrink: 0;">
                        <path d="M19 9l1.25-2.75L23 5l-2.75-1.25L19 1l-1.25 2.75L15 5l2.75 1.25L19 9zm-7.5.5L9 4 6.5 9.5 1 12l5.5 2.5L9 20l2.5-5.5L17 12l-5.5-2.5zM19 15l-1.25 2.75L15 19l2.75 1.25L19 23l1.25-2.75L23 19l-2.75-1.25L19 15z"/>
                    </svg>
                    <div style="font-size: 11px; color: #5F6368; font-family: 'Google Sans', sans-serif; line-height: 1.35;">
                        Build by <strong style="color: #202124; font-weight: 600;">Antigravity</strong> and <strong style="color: #202124; font-weight: 600;">Gemini</strong>
                    </div>
                </div>
            </div>
        </div>
        """
    )


# ==========================================
# MAIN PANEL
# ==========================================
try:
    kpi = load_executive_kpis()
    df_daily = load_daily_spend()
    df_projects = load_project_portfolio()

    # 4. Top Breadcrumb & GitHub Setup Guide Trigger
    nav_title = selected_nav.replace("📊", "").replace("🔬", "").replace("⚡", "").strip()
    col_bread, col_prompt, col_link = st.columns([2.2, 1.7, 1.1], vertical_alignment="center")
    with col_bread:
        st.html(
            f"""
            <div style="display: flex; align-items: center; gap: 8px; font-size: 13px; font-family: 'Google Sans', sans-serif;">
                <span style="color: #5F6368;">My Antigravity Token Analytics</span>
                <span style="color: #DADCE0;">→</span>
                <span style="font-weight: 600; color: #1A73E8;">{nav_title}</span>
            </div>
            """
        )
    with col_prompt:
        st.html(
            """
            <div style="text-align: right; font-size: 11.5px; color: #5F6368; font-family: 'Google Sans', sans-serif; line-height: 1.35;">
                Want to see your Antigravity metrics? Click this button
            </div>
            """
        )
    with col_link:
        if st.button("GitHub & Setup Guide", icon=":material/code:", use_container_width=True):
            show_github_setup_modal()
    st.html("<div style='border-bottom: 1px solid #DADCE0; margin-top: 4px; margin-bottom: 18px;'></div>")

    if "Executive Overview" in selected_nav:
        top_project = df_projects.iloc[0]["antigravity_project_name"]
        top_project_cost = df_projects.iloc[0]["cost_usd"]
        top_project_pct = (top_project_cost / kpi["total_spend_usd"]) * 100.0

        # -------------------------------------------------------------
        # 5. EXECUTIVE SUMMARY (Moved to TOP right below breadcrumbs)
        # -------------------------------------------------------------
        st.html(
            f"""
            <div class="gcp-recommendation-banner">
                <div style="color: #1A73E8; font-size: 22px; margin-top: 1px;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="#1A73E8">
                        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                    </svg>
                </div>
                <div style="flex: 1;">
                    <div class="gcp-recommendation-title">Executive Summary</div>
                    <div class="gcp-recommendation-text">
                        Across <strong>{int(kpi['total_projects'])} active engineering repositories</strong> and <strong>{int(kpi['total_workspaces'])} workspaces</strong>, developer AI workflows have processed <strong>{kpi['grand_total_tokens'] / 1_000_000:.2f}M tokens</strong> across <strong>{int(kpi['total_conversations'])} sessions</strong> ({int(kpi['total_steps']):,} execution turns) for an aggregate investment of <strong>${kpi['total_spend_usd']:,.2f} USD</strong>. 
                        Spend is heavily concentrated in <strong>{top_project}</strong> (${top_project_cost:,.2f}, representing <strong>{top_project_pct:.1f}%</strong> of total cost). Model inference health remains high with a mean streaming speed of <strong>{kpi['avg_speed']} tok/s</strong> and average first-token network latency of <strong>{kpi['avg_ttft_ms']/1000.0:.2f}s</strong>.
                    </div>
                </div>
            </div>
            """
        )

        # -------------------------------------------------------------
        # THE 5 CORE EXECUTIVE READOUTS (Google Cards with SVG Icons)
        # -------------------------------------------------------------
        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            st.html(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Total Projects</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 2px 0;">
                        <div class="kpi-value">{int(kpi['total_projects']):,}</div>
                        <div class="kpi-icon-container" style="background: #E8F0FE; color: #1A73E8;">
                            📁
                        </div>
                    </div>
                    <div style="margin-top: auto; padding-top: 4px;">
                        <span class="pill pill-blue">Active Repos</span>
                    </div>
                </div>
                """
            )

        with c2:
            st.html(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Total Workspaces</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 2px 0;">
                        <div class="kpi-value">{int(kpi['total_workspaces']):,}</div>
                        <div class="kpi-icon-container" style="background: #EEF0F8; color: #3F51B5;">
                            👥
                        </div>
                    </div>
                    <div style="margin-top: auto; padding-top: 4px;">
                        <span class="pill pill-blue">Workstation Dirs</span>
                    </div>
                </div>
                """
            )

        with c3:
            st.html(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Total Conversations</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 2px 0;">
                        <div class="kpi-value">{int(kpi['total_conversations']):,}</div>
                        <div class="kpi-icon-container" style="background: #F3E8FD; color: #8430CE;">
                            💬
                        </div>
                    </div>
                    <div style="margin-top: auto; padding-top: 4px;">
                        <span class="pill pill-purple">{int(kpi['total_steps']):,} Turns</span>
                    </div>
                </div>
                """
            )

        with c4:
            st.html(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Tokens Consumed</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 2px 0;">
                        <div class="kpi-value">{kpi['grand_total_tokens'] / 1_000_000:.2f}M</div>
                        <div class="kpi-icon-container" style="background: #E6F4EA; color: #137333;">
                            🪙
                        </div>
                    </div>
                    <div style="margin-top: auto; padding-top: 4px;">
                        <span class="pill pill-green">96.7% Context In</span>
                    </div>
                </div>
                """
            )

        with c5:
            st.html(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">Total Cost Incurred</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin: 2px 0;">
                        <div class="kpi-value" style="color: #1A73E8;">${kpi['total_spend_usd']:,.2f}</div>
                        <div class="kpi-icon-container" style="background: #FEF7E0; color: #B06000;">
                            💲
                        </div>
                    </div>
                    <div style="margin-top: auto; padding-top: 4px;">
                        <span class="pill pill-amber">Avg ${(kpi['total_spend_usd'] / max(1, kpi['total_projects'])):,.2f} / repo</span>
                    </div>
                </div>
                """
            )

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # -------------------------------------------------------------
        # CHARTS ROW (Side by Side White Cards)
        # -------------------------------------------------------------
        chart_col1, chart_col2 = st.columns([1.6, 1.0])

        with chart_col1:
            st.html(
                """
                <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; padding: 20px 20px 10px 20px; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.1);">
                    <div style="font-family: 'Google Sans', sans-serif; font-size: 15px; font-weight: 600; color: #202124; margin-bottom: 2px;">
                        Daily Spend by Project ($ USD)
                    </div>
                    <div style="font-size: 12px; color: #5F6368; margin-bottom: 8px;">
                        Stacked daily financial cost by repository
                    </div>
                </div>
                """
            )

            if not df_daily.empty:
                df_daily["usage_date"] = pd.to_datetime(df_daily["usage_date"])
                daily_agg = (
                    df_daily.groupby(["usage_date", "antigravity_project_name"])[
                        ["daily_spend_usd", "daily_total_tokens"]
                    ]
                    .sum()
                    .reset_index()
                )

                google_colors = ["#1A73E8", "#12B5CB", "#FBBC04", "#34A853", "#EA4335", "#9334E6", "#70757A"]

                fig_spend = px.bar(
                    daily_agg,
                    x="usage_date",
                    y="daily_spend_usd",
                    color="antigravity_project_name",
                    labels={
                        "usage_date": "Date",
                        "daily_spend_usd": "Spend ($ USD)",
                        "antigravity_project_name": "Project",
                    },
                    color_discrete_sequence=google_colors,
                    barmode="stack",
                    template="plotly_white",
                )
                fig_spend.update_layout(
                    height=320,
                    margin=dict(l=60, r=10, t=10, b=10),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.22,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11, family="Roboto", color="#3C4043"),
                    ),
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    xaxis=dict(
                        showgrid=False,
                        linecolor="#DADCE0",
                        tickfont=dict(size=11, color="#5F6368"),
                    ),
                    yaxis=dict(
                        automargin=True,
                        showgrid=True,
                        gridcolor="#F1F3F4",
                        linecolor="#DADCE0",
                        tickprefix="$",
                        tickfont=dict(size=11, color="#5F6368"),
                    ),
                )
                fig_spend.update_traces(marker=dict(line=dict(width=0)))
                st.plotly_chart(fig_spend, use_container_width=True, theme=None)

        with chart_col2:
            st.html(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; padding: 20px 20px 10px 20px; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.1);">
                    <div style="font-family: 'Google Sans', sans-serif; font-size: 15px; font-weight: 600; color: #202124; margin-bottom: 2px;">
                        Token Composition
                    </div>
                    <div style="font-size: 12px; color: #5F6368; margin-bottom: 8px;">
                        Anatomy of {kpi['grand_total_tokens'] / 1_000_000:.2f}M tokens processed
                    </div>
                </div>
                """
            )

            token_pie = pd.DataFrame(
                {
                    "Role": ["Prompt Context", "Generated Output", "Thinking / Reasoning"],
                    "Tokens": [
                        kpi["total_prompt_tokens"],
                        kpi["total_output_tokens"] - kpi["total_thinking_tokens"],
                        kpi["total_thinking_tokens"],
                    ],
                }
            )
            fig_pie = px.pie(
                token_pie,
                names="Role",
                values="Tokens",
                hole=0.66,
                color_discrete_sequence=["#1A73E8", "#34A853", "#FBBC04"],
                template="plotly_white",
            )
            fig_pie.update_layout(
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.22,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11, family="Roboto", color="#3C4043"),
                ),
                plot_bgcolor="#FFFFFF",
                paper_bgcolor="#FFFFFF",
                annotations=[
                    dict(
                        text=f"<b>{kpi['grand_total_tokens'] / 1_000_000:.2f}M</b><br><span style='font-size:11px;color:#5F6368;font-weight:normal;'>Tokens</span>",
                        x=0.5,
                        y=0.5,
                        font=dict(size=18, family="Google Sans", color="#202124"),
                        showarrow=False,
                    )
                ],
            )
            fig_pie.update_traces(textposition="none", marker=dict(line=dict(color="#FFFFFF", width=2)))
            st.plotly_chart(fig_pie, use_container_width=True, theme=None)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # -------------------------------------------------------------
        # CUSTOM GOOGLE CLOUD CONSOLE PORTFOLIO DATA TABLE
        # -------------------------------------------------------------
        max_cost = df_projects["cost_usd"].max() if not df_projects.empty else 1.0

        table_rows_list = []
        for _, row in df_projects.iterrows():
            pct = (row["cost_usd"] / max_cost) * 100.0 if max_cost > 0 else 0
            tokens_str = f"{row['total_tokens'] / 1_000_000:.2f} M" if row['total_tokens'] >= 1_000_000 else f"{row['total_tokens']:,}"
            
            table_rows_list.append(
                f"""<tr>
<td style="font-weight: 600; color: #1A73E8; font-family: 'Google Sans';">{row['antigravity_project_name']}</td>
<td style="font-family: 'Roboto';"><strong>${row['cost_usd']:,.2f}</strong><div class="progress-bar-bg"><div class="progress-bar-fill" style="width: {pct:.1f}%;"></div></div></td>
<td style="font-family: monospace; color: #3C4043;">{tokens_str}</td>
<td style="font-family: 'Roboto'; color: #5F6368;">{int(row['conversations']):,} sessions ({int(row['total_turns']):,} turns)</td>
<td><span class="pill pill-green">{row['avg_tokens_per_second']:.1f} tok/s</span></td>
<td style="color: #5F6368; font-family: monospace;">{int(row['avg_ttft_ms']):,} ms</td>
</tr>"""
            )

        table_rows_joined = "\n".join(table_rows_list)

        portfolio_table_html = f"""
<div class="gcp-table-container">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
<div>
<div style="font-family: 'Google Sans', sans-serif; font-size: 15px; font-weight: 600; color: #202124;">
Project Portfolio Financials & Consumption
</div>
<div style="font-size: 12px; color: #5F6368;">
Ranked breakdown across all {int(kpi['total_projects'])} workspace codebases
</div>
</div>
<span class="pill pill-blue">Sorted by Spend</span>
</div>
<table class="gcp-table">
<thead>
<tr>
<th>Repository / Codebase</th>
<th>Financial Spend ($ USD)</th>
<th>Total Tokens</th>
<th>Session Volume</th>
<th>Throughput</th>
<th>Cloud TTFT</th>
</tr>
</thead>
<tbody>
{table_rows_joined}
</tbody>
</table>
</div>
"""
        st.html(portfolio_table_html)

    elif "Tokenomics Deep Dive" in selected_nav:
        # Load available projects for drilldown
        df_deep_projects = load_deepdive_projects()

        if df_deep_projects.empty:
            st.warning("No project telemetry found in BigQuery.")
        else:
            project_names = df_deep_projects["antigravity_project_name"].tolist()
            default_proj_idx = project_names.index("token_observability") if "token_observability" in project_names else 0

            # --- DRILLDOWN FILTER BAR (GCP Styled) ---
            st.html(
                """
                <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 1px 2px rgba(60,64,67,0.06);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 15px; font-weight: 700; color: #202124; font-family: 'Google Sans', sans-serif;">
                                Granular Tokenomics & Context Drilldown
                            </div>
                            <div style="font-size: 12px; color: #5F6368; font-family: 'Roboto', sans-serif; margin-top: 2px;">
                                Inspect token anatomy (Prompt, Thinking, Output) and cache absorption across projects, sessions, and individual execution turns.
                            </div>
                        </div>
                        <span class="pill pill-blue">Multi-Level Drilldown</span>
                    </div>
                </div>
                """
            )

            # Two selectboxes for Project and Conversation
            col_proj, col_conv = st.columns([1, 2])

            with col_proj:
                selected_project = st.selectbox(
                    "📁 Select Project / Repository",
                    project_names,
                    index=default_proj_idx,
                )

            df_convs = load_conversations_for_project(selected_project)

            with col_conv:
                if df_convs.empty:
                    st.info(f"No sessions found for project {selected_project}.")
                    selected_conv_id = None
                else:
                    conv_options = {}
                    for _, row in df_convs.iterrows():
                        cid = row["conversation_id"]
                        short_cid = f"{cid[:8]}...{cid[-4:]}"
                        turns = int(row["turns"])
                        cost = float(row["cost_usd"])
                        st_time = pd.to_datetime(row["start_time"]).strftime("%b %d, %H:%M")
                        cached_k = float(row["cached_tokens"]) / 1000.0
                        tot_k = float(row["total_tokens"]) / 1000.0
                        label = f"Session {short_cid} | {turns} turns | {tot_k:.1f}k tokens ({cached_k:.1f}k cached) | ${cost:.2f} | {st_time}"
                        conv_options[label] = cid

                    selected_label = st.selectbox(
                        "💬 Select Conversation / Session",
                        list(conv_options.keys()),
                        index=0,
                    )
                    selected_conv_id = conv_options[selected_label]

            if selected_conv_id:
                # Fetch granular turn-by-turn data
                df_turns = load_turns_for_conversation(selected_conv_id)

                # Fetch row summary from df_convs
                conv_row = df_convs[df_convs["conversation_id"] == selected_conv_id].iloc[0]

                tot_spend = float(df_turns["cost_usd"].sum()) if not df_turns.empty else float(conv_row["cost_usd"])
                tot_cached = int(df_turns["cached_tokens"].sum()) if not df_turns.empty else int(conv_row["cached_tokens"])
                tot_uncached = int(df_turns["uncached_prompt_tokens"].sum()) if not df_turns.empty else int(conv_row.get("uncached_prompt_tokens", 0))
                tot_thinking = int(df_turns["thinking_tokens"].sum()) if not df_turns.empty else int(conv_row["thinking_tokens"])
                tot_content = int(df_turns["content_tokens"].sum()) if not df_turns.empty else 0
                tot_output = tot_thinking + tot_content
                tot_prompt = tot_cached + tot_uncached
                tot_tokens = tot_cached + tot_uncached + tot_output
                tot_turns = len(df_turns) if not df_turns.empty else int(conv_row["turns"])

                # Cache efficiency: % of prompt tokens that came from cache
                cache_hit_rate = (tot_cached / tot_prompt * 100.0) if tot_prompt > 0 else 0.0

                # Gemini prompt cache discount (e.g. 3.8 Flash: $0.75/M -> $0.075/M, savings = $0.675/M)
                savings_rate = get_cache_savings_rate(str(conv_row.get("model", "gemini-3.8-flash")))
                dollars_saved = (tot_cached / 1_000_000.0) * savings_rate

                # Peak context window reached (max prompt in any turn: cached + uncached prompt)
                max_prompt_reached = int((df_turns["cached_tokens"] + df_turns["uncached_prompt_tokens"]).max()) if not df_turns.empty else 0
                context_saturation_pct = (max_prompt_reached / 1_048_576.0) * 100.0

                # Formatted values for identical card sizing
                spend_str = f"${tot_spend:,.2f}"
                avg_turn_str = f"Avg ${tot_spend/max(1, tot_turns):.2f}/turn"
                tokens_str = f"{tot_tokens/1_000_000.0:,.2f}M" if tot_tokens >= 1_000_000 else f"{tot_tokens/1000.0:,.1f}k"
                cached_pill_text = f"{tot_cached/1_000_000.0:,.1f}M Cached" if tot_cached >= 1_000_000 else f"{tot_cached/1000.0:,.0f}k Cached"
                cache_pill_class = "pill-green" if cache_hit_rate >= 50 else "pill-amber"
                saved_str = f"+${dollars_saved:,.2f}"
                max_ctx_str = f"{max_prompt_reached/1000.0:,.1f}k" if max_prompt_reached < 1_000_000 else f"{max_prompt_reached/1_000_000.0:,.2f}M"

                # --- 5 MACRO KPI CARDS FOR SELECTED CONVERSATION ---
                k1, k2, k3, k4, k5 = st.columns(5)
                with k1:
                    st.html(
                        f"""
                        <div class="kpi-card">
                            <div>
                                <div class="kpi-title">Session Spend</div>
                                <div class="kpi-value" style="color: #1A73E8;">{spend_str}</div>
                            </div>
                            <div style="margin-top: auto; padding-top: 6px;">
                                <span class="pill pill-blue">{avg_turn_str}</span>
                            </div>
                        </div>
                        """
                    )
                with k2:
                    st.html(
                        f"""
                        <div class="kpi-card">
                            <div>
                                <div class="kpi-title">Total Tokens</div>
                                <div class="kpi-value">{tokens_str}</div>
                            </div>
                            <div style="margin-top: auto; padding-top: 6px;">
                                <span class="pill pill-purple">{tot_turns:,} Execution Turns</span>
                            </div>
                        </div>
                        """
                    )
                with k3:
                    st.html(
                        f"""
                        <div class="kpi-card">
                            <div>
                                <div class="kpi-title">Cache Hit Rate</div>
                                <div class="kpi-value" style="color: #137333;">{cache_hit_rate:.1f}%</div>
                            </div>
                            <div style="margin-top: auto; padding-top: 6px;">
                                <span class="pill {cache_pill_class}">{cached_pill_text}</span>
                            </div>
                        </div>
                        """
                    )
                with k4:
                    st.html(
                        f"""
                        <div class="kpi-card">
                            <div>
                                <div class="kpi-title">Cost Saved (Cache)</div>
                                <div class="kpi-value" style="color: #137333;">{saved_str}</div>
                            </div>
                            <div style="margin-top: auto; padding-top: 6px;">
                                <span class="pill pill-green">75% Cache Discount</span>
                            </div>
                        </div>
                        """
                    )
                with k5:
                    st.html(
                        f"""
                        <div class="kpi-card">
                            <div>
                                <div class="kpi-title">Max Context Reached</div>
                                <div class="kpi-value">{max_ctx_str}</div>
                            </div>
                            <div style="margin-top: auto; padding-top: 6px;">
                                <span class="pill pill-blue">{context_saturation_pct:.1f}% of 1M Window</span>
                            </div>
                        </div>
                        """
                    )

                st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

                # --- VISUALIZATIONS ROW 1: TURN-BY-TURN TOKEN PROGRESSION (STACKED BAR - 20 TURNS WINDOW) ---
                total_turns_count = len(df_turns)
                window_size = 20

                conv_chart_key = f"chart_turn_offset_{selected_conv_id}"
                if conv_chart_key not in st.session_state:
                    st.session_state[conv_chart_key] = max(0, total_turns_count - window_size)

                # Clamp offset
                curr_offset = st.session_state[conv_chart_key]
                curr_offset = max(0, min(curr_offset, max(0, total_turns_count - window_size)))
                st.session_state[conv_chart_key] = curr_offset

                start_turn_idx = curr_offset
                end_turn_idx = min(start_turn_idx + window_size, total_turns_count)
                df_plot = df_turns.iloc[start_turn_idx:end_turn_idx].copy()
                df_plot["step_label"] = "Turn<br>#" + df_plot["step_index"].astype(str)
                df_plot["step_str"] = df_plot["step_index"].astype(str)

                st.html(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; padding: 20px 22px 14px 22px; box-shadow: 0 1px 2px rgba(60,64,67,0.06); margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
                            <div>
                                <span style="font-family: 'Google Sans', sans-serif; font-size: 15px; font-weight: 600; color: #202124;">
                                    Turn-by-Turn Token Progression & Anatomy
                                </span>
                                <span style="font-size: 12px; color: #5F6368; margin-left: 8px;">
                                    Displaying 20 turns per window (Turns {start_turn_idx + 1}–{end_turn_idx} of {total_turns_count:,})
                                </span>
                            </div>
                            <div style="display: flex; gap: 6px;">
                                <span class="pill pill-green">Cached Context</span>
                                <span class="pill pill-blue">New Prompt</span>
                                <span class="pill pill-purple">Reasoning / Thinking</span>
                                <span class="pill pill-amber">Output Content</span>
                            </div>
                        </div>
                    """
                )

                # Navigation controls if more than 20 turns exist
                if total_turns_count > window_size:
                    c_btn1, c_btn2, c_info, c_btn3, c_btn4 = st.columns([1, 1, 2.5, 1, 1])
                    with c_btn1:
                        if st.button("⏮ First 20", disabled=(curr_offset <= 0), key=f"btn_first_{selected_conv_id}", use_container_width=True):
                            st.session_state[conv_chart_key] = 0
                            st.rerun()
                    with c_btn2:
                        if st.button("◀ Earlier 20", disabled=(curr_offset <= 0), key=f"btn_prev_{selected_conv_id}", use_container_width=True):
                            st.session_state[conv_chart_key] = max(0, curr_offset - window_size)
                            st.rerun()
                    with c_info:
                        st.markdown(
                            f"<div style='text-align: center; padding-top: 6px; font-size: 13px; font-weight: 500; color: #202124;'>"
                            f"Viewing Turns <strong>{start_turn_idx + 1} – {end_turn_idx}</strong> of <strong>{total_turns_count:,}</strong>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with c_btn3:
                        if st.button("Later 20 ▶", disabled=(end_turn_idx >= total_turns_count), key=f"btn_next_{selected_conv_id}", use_container_width=True):
                            st.session_state[conv_chart_key] = min(total_turns_count - window_size, curr_offset + window_size)
                            st.rerun()
                    with c_btn4:
                        if st.button("Latest 20 ⏭", disabled=(end_turn_idx >= total_turns_count), key=f"btn_latest_{selected_conv_id}", use_container_width=True):
                            st.session_state[conv_chart_key] = max(0, total_turns_count - window_size)
                            st.rerun()

                if not df_plot.empty:
                    fig_prog = go.Figure()

                    # 1. Cached Prompt Tokens (Green)
                    fig_prog.add_trace(go.Bar(
                        x=df_plot["step_label"],
                        y=df_plot["cached_tokens"],
                        name="Cached Prompt",
                        customdata=df_plot["step_str"],
                        marker_color="#34A853",
                        hovertemplate="<b>Turn #%{customdata}</b><br>Cached Context: %{y:,} tokens<extra></extra>",
                    ))

                    # 2. Uncached Prompt Tokens (Blue)
                    fig_prog.add_trace(go.Bar(
                        x=df_plot["step_label"],
                        y=df_plot["uncached_prompt_tokens"],
                        name="New Prompt",
                        customdata=df_plot["step_str"],
                        marker_color="#1A73E8",
                        hovertemplate="<b>Turn #%{customdata}</b><br>New Prompt Context: %{y:,} tokens<extra></extra>",
                    ))

                    # 3. Thinking / Reasoning Tokens (Purple)
                    fig_prog.add_trace(go.Bar(
                        x=df_plot["step_label"],
                        y=df_plot["thinking_tokens"],
                        name="Thinking (Reasoning)",
                        customdata=df_plot["step_str"],
                        marker_color="#9334E6",
                        hovertemplate="<b>Turn #%{customdata}</b><br>Thinking Tokens: %{y:,} tokens<extra></extra>",
                    ))

                    # 4. Output Content Tokens (Amber/Coral)
                    fig_prog.add_trace(go.Bar(
                        x=df_plot["step_label"],
                        y=df_plot["content_tokens"],
                        name="Output Content",
                        customdata=df_plot["step_str"],
                        marker_color="#F2994A",
                        hovertemplate="<b>Turn #%{customdata}</b><br>Output Content: %{y:,} tokens<extra></extra>",
                    ))

                    fig_prog.update_layout(
                        barmode="stack",
                        height=360,
                        margin=dict(l=75, r=20, t=10, b=50),
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#FFFFFF",
                        bargap=0.25,
                        font=dict(family="Roboto, sans-serif", size=12, color="#5F6368"),
                        xaxis=dict(
                            showgrid=False,
                            linecolor="#DADCE0",
                            tickangle=0,
                            tickfont=dict(family="Roboto Mono, monospace", size=11, color="#3C4043"),
                        ),
                        yaxis=dict(
                            automargin=True,
                            showgrid=True,
                            gridcolor="#F1F3F4",
                            linecolor="#DADCE0",
                            title=dict(
                                text="Tokens Consumed",
                                standoff=14,
                                font=dict(family="Google Sans, sans-serif", size=12, color="#3C4043"),
                            ),
                            tickfont=dict(family="Roboto Mono, monospace", size=11, color="#3C4043"),
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1,
                            font=dict(size=11, color="#3C4043"),
                        ),
                    )
                    st.plotly_chart(fig_prog, use_container_width=True, theme=None)
                st.html("</div>")

                # --- VISUALIZATIONS ROW 2: DONUT SPLIT & CUMULATIVE COST TRAJECTORY ---
                c_left, c_right = st.columns([1, 1])

                with c_left:
                    st.html(
                        """
                        <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; padding: 20px 22px 14px 22px; box-shadow: 0 1px 2px rgba(60,64,67,0.06);">
                            <div style="font-family: 'Google Sans', sans-serif; font-size: 15px; font-weight: 600; color: #202124; margin-bottom: 4px;">
                                Aggregate Token Composition
                            </div>
                            <div style="font-size: 12px; color: #5F6368; margin-bottom: 12px;">
                                Breakdown of cached context, new input, reasoning, and visible output
                            </div>
                        """
                    )
                    def _fmt_tok_short(n):
                        if n >= 1_000_000:
                            return f"{n/1_000_000.0:.2f}M"
                        elif n >= 1_000:
                            return f"{n/1000.0:.1f}k"
                        return f"{int(n):,}"

                    tot_all_pie = max(1, tot_tokens)
                    pct_cached = (tot_cached / tot_all_pie) * 100.0
                    pct_uncached = (tot_uncached / tot_all_pie) * 100.0
                    pct_thinking = (tot_thinking / tot_all_pie) * 100.0
                    pct_content = (tot_content / tot_all_pie) * 100.0

                    labels = [
                        f"Cached Prompt: {_fmt_tok_short(tot_cached)} ({pct_cached:.1f}%)",
                        f"New Prompt: {_fmt_tok_short(tot_uncached)} ({pct_uncached:.1f}%)",
                        f"Thinking: {_fmt_tok_short(tot_thinking)} ({pct_thinking:.1f}%)",
                        f"Output Content: {_fmt_tok_short(tot_content)} ({pct_content:.1f}%)",
                    ]
                    values = [tot_cached, tot_uncached, tot_thinking, tot_content]
                    colors = ["#34A853", "#1A73E8", "#9334E6", "#F2994A"]

                    fig_pie = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        domain=dict(x=[0.0, 0.46], y=[0.0, 1.0]),
                        hole=0.62,
                        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                        textinfo="none",
                        hoverinfo="label+value+percent",
                        hovertemplate="<b>%{label}</b><br>Tokens: %{value:,}<br>Share: %{percent}<extra></extra>",
                        title=dict(
                            text=f"<b>{tokens_str}</b><br><span style='font-size:12px;color:#5F6368;'>Total</span>",
                            position="middle center",
                            font=dict(family="Google Sans, sans-serif", size=17, color="#202124"),
                        ),
                        sort=False,
                    )])
                    fig_pie.update_layout(
                        height=320,
                        margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor="#FFFFFF",
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            x=0.48,
                            y=0.5,
                            yanchor="middle",
                            xanchor="left",
                            font=dict(size=12, family="Roboto, sans-serif", color="#202124"),
                            itemclick=False,
                            itemdoubleclick=False,
                        ),
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, theme=None)
                    st.html("</div>")

                with c_right:
                    st.html(
                        """
                        <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; padding: 20px 22px 14px 22px; box-shadow: 0 1px 2px rgba(60,64,67,0.06);">
                            <div style="font-family: 'Google Sans', sans-serif; font-size: 15px; font-weight: 600; color: #202124; margin-bottom: 4px;">
                                Financial Cost Trajectory & Cache Savings
                            </div>
                            <div style="font-size: 12px; color: #5F6368; margin-bottom: 12px;">
                                Cumulative spend vs. hypothetical baseline without prompt caching ($ USD)
                            </div>
                        """
                    )
                    if not df_turns.empty:
                        df_cost = df_turns.copy()
                        if "model" in df_cost.columns:
                            df_cost["turn_saved"] = df_cost.apply(
                                lambda row: (row["cached_tokens"] / 1_000_000.0) * get_cache_savings_rate(str(row.get("model", ""))),
                                axis=1
                            )
                        else:
                            df_cost["turn_saved"] = (df_cost["cached_tokens"] / 1_000_000.0) * 0.675
                        df_cost["cum_baseline_cost"] = df_cost["cum_actual_cost"] + df_cost["turn_saved"].cumsum()

                        first_turn_no = int(df_cost["step_index"].iloc[0])
                        curr_turn_no = int(df_cost["step_index"].iloc[-1])

                        fig_cost = go.Figure()

                        # Baseline line (Grey dashed)
                        fig_cost.add_trace(go.Scatter(
                            x=df_cost["step_index"],
                            y=df_cost["cum_baseline_cost"],
                            name="Without Caching",
                            mode="lines",
                            line=dict(color="#80868B", width=2, dash="dash"),
                            hovertemplate="<b>Turn #%{x}</b><br>Without Caching: $%{y:.2f}<extra></extra>",
                        ))

                        # Actual spend line (Google Blue)
                        fig_cost.add_trace(go.Scatter(
                            x=df_cost["step_index"],
                            y=df_cost["cum_actual_cost"],
                            name="Actual Invoiced Spend",
                            mode="lines",
                            line=dict(color="#1A73E8", width=3),
                            fill="tonexty",
                            fillcolor="rgba(52, 168, 83, 0.12)",
                            hovertemplate="<b>Turn #%{x}</b><br>Actual Spend: $%{y:.2f}<extra></extra>",
                        ))

                        fig_cost.update_layout(
                            height=320,
                            margin=dict(l=75, r=25, t=10, b=45),
                            paper_bgcolor="#FFFFFF",
                            plot_bgcolor="#FFFFFF",
                            font=dict(family="Roboto, sans-serif", size=12, color="#5F6368"),
                            xaxis=dict(
                                showgrid=False,
                                showticklabels=False,
                                linecolor="#DADCE0",
                                ticks="outside",
                                ticklen=4,
                                tickcolor="#DADCE0",
                                tickmode="array",
                                tickvals=[first_turn_no, curr_turn_no],
                                zeroline=False,
                            ),
                            yaxis=dict(
                                automargin=True,
                                showgrid=True,
                                gridcolor="#F1F3F4",
                                linecolor="#DADCE0",
                                title=dict(
                                    text="Cumulative USD ($)",
                                    standoff=14,
                                    font=dict(family="Google Sans, sans-serif", size=12, color="#3C4043"),
                                ),
                                tickprefix="$",
                                tickformat=".2f",
                                tickfont=dict(family="Roboto Mono, monospace", size=11, color="#3C4043"),
                            ),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=11, color="#3C4043")),
                            annotations=[
                                dict(
                                    xref="paper",
                                    yref="paper",
                                    x=0.0,
                                    y=-0.08,
                                    xanchor="left",
                                    yanchor="top",
                                    text=f"First Turn (#{first_turn_no})",
                                    showarrow=False,
                                    font=dict(size=11, family="Google Sans, sans-serif", color="#3C4043"),
                                ),
                                dict(
                                    xref="paper",
                                    yref="paper",
                                    x=1.0,
                                    y=-0.08,
                                    xanchor="right",
                                    yanchor="top",
                                    text=f"Current Turn (#{curr_turn_no})",
                                    showarrow=False,
                                    font=dict(size=11, family="Google Sans, sans-serif", color="#3C4043"),
                                ),
                            ],
                        )
                        st.plotly_chart(fig_cost, use_container_width=True, theme=None)
                    st.html("</div>")

                st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

                # --- TURN-BY-TURN GRANULAR TELEMETRY TABLE (PAGINATED 100 TURNS) ---
                table_limit_key = f"table_limit_{selected_conv_id}"
                if table_limit_key not in st.session_state:
                    st.session_state[table_limit_key] = 100

                current_limit = st.session_state[table_limit_key]
                df_table = df_turns.tail(current_limit).copy()

                table_rows = []
                for _, tr in df_table.iterrows():
                    s_idx = int(tr["step_index"])
                    model_lbl = str(tr["model"])
                    tot_tok = int(tr["total_tokens"])
                    uncached_p = int(tr["uncached_prompt_tokens"])
                    cached_t = int(tr["cached_tokens"])
                    thk_t = int(tr["thinking_tokens"])
                    out_t = int(tr["content_tokens"])
                    lat_ms = int(tr["latency_ms"]) if pd.notnull(tr["latency_ms"]) else "-"
                    speed = f"{float(tr['tokens_per_second']):.1f} tok/s" if pd.notnull(tr["tokens_per_second"]) and tr["tokens_per_second"] > 0 else "-"
                    step_c = float(tr["cost_usd"])
                    step_c_disp, step_c_tip = format_step_cost(step_c)

                    cached_badge = f'<span class="pill pill-green">{cached_t:,}</span>' if cached_t > 0 else '<span style="color:#BDC1C6;">0</span>'
                    thinking_badge = f'<span class="pill pill-purple">{thk_t:,}</span>' if thk_t > 0 else '<span style="color:#BDC1C6;">0</span>'

                    table_rows.append(f"""
                    <tr>
                        <td style="font-weight: 600; color: #1A73E8; font-family: 'Roboto Mono', monospace;">Turn #{s_idx}</td>
                        <td style="font-size: 11px; color: #5F6368; font-family: 'Roboto Mono', monospace;">{model_lbl}</td>
                        <td style="font-weight: 600; font-family: 'Roboto Mono', monospace;">{tot_tok:,}</td>
                        <td style="font-family: 'Roboto Mono', monospace; color: #202124;">{uncached_p:,}</td>
                        <td>{cached_badge}</td>
                        <td>{thinking_badge}</td>
                        <td style="font-family: 'Roboto Mono', monospace; color: #202124;">{out_t:,}</td>
                        <td style="font-size: 11px; color: #5F6368; font-family: 'Roboto Mono', monospace;">{lat_ms} ms</td>
                        <td style="font-size: 11px; color: #5F6368; font-family: 'Roboto Mono', monospace;">{speed}</td>
                        <td title="{step_c_tip}" style="font-weight: 600; color: #202124; font-family: 'Roboto Mono', monospace; cursor: help;">{step_c_disp}</td>
                    </tr>
                    """)

                joined_turns = "\n".join(table_rows)

                st.html(
                    f"""
                    <div class="gcp-table-container">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <div>
                                <div style="font-family: 'Google Sans', sans-serif; font-size: 15px; font-weight: 600; color: #202124;">
                                    Turn-by-Turn Granular Telemetry Trace
                                </div>
                                <div style="font-size: 12px; color: #5F6368;">
                                    Displaying last {len(df_table):,} of {total_turns_count:,} sequential execution turns for Session {selected_conv_id[:8]}
                                </div>
                            </div>
                            <span class="pill pill-blue">Last {len(df_table):,} Turns</span>
                        </div>
                        <details class="cost-guide-drawer" style="margin-bottom: 14px; background: #F8F9FA; border: 1px solid #DADCE0; border-radius: 8px; padding: 10px 14px; font-family: 'Roboto', sans-serif; font-size: 12px; color: #3C4043;">
                            <summary style="font-family: 'Google Sans', sans-serif; font-weight: 600; font-size: 12.5px; color: #1A73E8; cursor: pointer; display: flex; align-items: center; gap: 6px; user-select: none;">
                                <span>ℹ️ How Step Cost &amp; Cache Savings Are Calculated</span>
                                <span style="font-size: 11px; font-weight: 400; color: #5F6368;">(Click to view formula, model rate cards &amp; cache economics)</span>
                            </summary>
                            <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid #E8EAED; line-height: 1.6;">
                                <div style="font-weight: 600; color: #202124; margin-bottom: 4px;">1. Mathematical Formula:</div>
                                <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 4px; padding: 6px 12px; font-family: 'Roboto Mono', monospace; font-size: 11.5px; margin-bottom: 10px; color: #202124;">
                                    Step Cost ($ USD) = (Prompt Tokens / 1,000,000 &times; Prompt Rate) + (Output Tokens / 1,000,000 &times; Output Rate)
                                </div>
                                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; margin-bottom: 10px;">
                                    <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 6px; padding: 8px 12px;">
                                        <div style="font-weight: 600; color: #1A73E8; font-size: 11.5px; margin-bottom: 4px;">Official Rate Cards (per 1M Tokens)</div>
                                        <ul style="margin: 0; padding-left: 18px; font-size: 11px; color: #3C4043;">
                                            <li><strong>Gemini 3.8 Flash</strong>: $0.75 prompt / $3.75 output (cached: $0.075)</li>
                                            <li><strong>Gemini 2.5 Flash</strong>: $0.30 prompt / $2.50 output (cached: $0.030)</li>
                                            <li><strong>Gemini 2.0 Flash</strong>: $0.15 prompt / $0.60 output (cached: $0.0375)</li>
                                            <li><strong>Gemini Flash-Lite</strong>: $0.075 prompt / $0.30 output</li>
                                            <li><strong>Gemini 2.5 Pro</strong>: $1.25 prompt / $10.00 output (cached: $0.125)</li>
                                            <li><strong>Claude 3.7 Sonnet</strong>: $3.00 prompt / $15.00 output</li>
                                        </ul>
                                    </div>
                                    <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 6px; padding: 8px 12px;">
                                        <div style="font-weight: 600; color: #1E8E3E; font-size: 11.5px; margin-bottom: 4px;">Context Caching Economics &amp; Precision</div>
                                        <div style="font-size: 11px; color: #3C4043;">
                                            &bull; <strong>Cache Hits</strong>: Cached prefix tokens are discounted by 90% (Gemini 3.8/2.5) down to $0.075/M, dropping turn costs from ~$0.05 to ~$0.0022.<br>
                                            &bull; <strong>Adaptive Precision</strong>: Costs &ge; $0.01 show 2 decimals ($0.05); sub-cent micro-costs show 4 decimals ($0.0022). Hover over any cell to see exact 6-decimal rate.
                                        </div>
                                    </div>
                                </div>
                                <div style="font-size: 11px; color: #5F6368;">
                                    <strong>Cache Savings Formula:</strong> Cumulative Cache Savings = Gross Cost (all prompt tokens billed at uncached rate) &minus; Net Actual Spend.
                                </div>
                            </div>
                        </details>
                        <div class="gcp-scrollable-table">
                            <table class="gcp-table">
                                <thead>
                                    <tr>
                                        <th>Turn / Step</th>
                                        <th>Model</th>
                                        <th>Total Tokens</th>
                                        <th>New Prompt</th>
                                        <th>Cached Prompt</th>
                                        <th>Thinking Tokens</th>
                                        <th>Output Tokens</th>
                                        <th>Latency (TTFT)</th>
                                        <th>Throughput</th>
                                        <th title="Exact blended cost per turn. Sub-cent micro-costs formatted with 4 decimals; hover to view exact 6-decimal rate.">Step Cost ($ USD)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {joined_turns}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    """
                )

                # Pagination controls for table
                if total_turns_count > 100:
                    c_p1, c_p2, c_p3 = st.columns([1.5, 1.5, 3])
                    has_more = current_limit < total_turns_count
                    with c_p1:
                        if st.button("⬇ Load More (+100 Turns)", disabled=not has_more, key=f"btn_more_{selected_conv_id}", use_container_width=True):
                            st.session_state[table_limit_key] = min(total_turns_count, current_limit + 100)
                            st.rerun()
                    with c_p2:
                        if current_limit > 100:
                            if st.button("↺ Reset to Last 100", key=f"btn_reset_{selected_conv_id}", use_container_width=True):
                                st.session_state[table_limit_key] = 100
                                st.rerun()
                        elif has_more:
                            if st.button(f"⬇ Load All ({total_turns_count:,} Turns)", key=f"btn_all_{selected_conv_id}", use_container_width=True):
                                st.session_state[table_limit_key] = total_turns_count
                                st.rerun()
                    with c_p3:
                        st.markdown(
                            f"<div style='font-size: 12px; color: #5F6368; padding-top: 8px; text-align: right;'>"
                            f"Showing <strong>{len(df_table):,}</strong> of <strong>{total_turns_count:,}</strong> sequential turns"
                            f"</div>",
                            unsafe_allow_html=True
                        )

    elif "Token Telemetry" in selected_nav:
        # Load project list
        df_p_list = load_deepdive_projects()
        if df_p_list.empty:
            st.warning("No projects found in BigQuery telemetry.")
            st.stop()

        # 1. Project & Conversation Selectors
        c_p, c_c = st.columns([1, 1.8])
        with c_p:
            proj_names = df_p_list["antigravity_project_name"].tolist()
            def_proj_idx = 0
            for i, p in enumerate(proj_names):
                if "token_observability" in p.lower() or "project_4" in p.lower():
                    def_proj_idx = i
                    break
            selected_project = st.selectbox(
                "PROJECT SCOPE", proj_names, index=def_proj_idx, key="telem_proj_select"
            )

        with c_c:
            df_c_list = load_conversations_for_project(selected_project)
            if df_c_list.empty:
                st.info("No conversations found for selected project.")
                st.stop()
            conv_map = {}
            for _, crow in df_c_list.iterrows():
                cid = str(crow["conversation_id"])
                lbl = f"{cid[:8]}... ({int(crow['turns']):,} turns | ${float(crow['cost_usd']):,.2f} | {crow['start_time'].strftime('%b %d %H:%M')})"
                conv_map[lbl] = cid
            selected_conv_lbl = st.selectbox(
                "AGENT SESSION (CONVERSATION ID)", list(conv_map.keys()), index=0, key="telem_conv_select"
            )
            selected_conv_id = conv_map[selected_conv_lbl]

        # 2. Load Telemetry Data
        df_telem = load_telemetry_for_conversation(selected_conv_id)
        if df_telem.empty:
            st.info("No telemetry events found for this conversation session.")
            st.stop()

        total_turns_count = len(df_telem)
        step_indices = df_telem["step_index"].tolist()
        min_step = int(df_telem["step_index"].min())
        max_step = int(df_telem["step_index"].max())

        # 3. Turn Window Controls (default last 20 turns)
        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        c_w1, c_w2 = st.columns([3, 1])
        with c_w1:
            if len(step_indices) > 20:
                default_start = step_indices[max(0, len(step_indices) - 20)]
                turn_range = st.slider(
                    "Sequential Turn Window (Displaying last 20 by default; drag to scrub earlier turns)",
                    min_value=min_step,
                    max_value=max_step,
                    value=(default_start, max_step),
                    key=f"telem_slider_{selected_conv_id}",
                )
            else:
                turn_range = (min_step, max_step)
        with c_w2:
            st.markdown(
                f"<div style='font-size: 11px; color: #5F6368; padding-top: 24px; text-align: right;'>"
                f"Total Session: <strong>{total_turns_count:,}</strong> sequential turns"
                f"</div>",
                unsafe_allow_html=True,
            )

        df_window = df_telem[
            (df_telem["step_index"] >= turn_range[0]) & (df_telem["step_index"] <= turn_range[1])
        ].copy()
        if df_window.empty:
            df_window = df_telem.tail(20).copy()

        # 4. Sequential Gantt Waterfall Trace (Plotly)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                <div>
                    <span style="font-size: 15px; font-weight: 700; color: #202124; font-family: 'Google Sans';">
                        ⚡ Sequential Gantt Waterfall Trace
                    </span>
                    <span style="font-size: 12px; color: #5F6368; margin-left: 8px;">
                        (Client Prep → TTFT Server Prefill → Thinking Reasoning → Streaming Output)
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Prepare latency segments & accurate prompt context totals
        df_window["total_prompt_tokens"] = df_window["cached_tokens"] + df_window["uncached_prompt_tokens"]
        df_window["client_prep_s"] = (df_window["client_prep_ms"] / 1000.0).clip(lower=0.0)
        df_window["ttft_s"] = (df_window["ttft_latency_ms"] / 1000.0).clip(lower=0.0)

        # Calculate thinking vs streaming duration
        gen_duration_s = (df_window["generation_duration_ms"] / 1000.0).clip(lower=0.0)
        out_tokens = df_window["output_tokens"].replace(0, 1)
        thk_tokens = df_window["thinking_tokens"].fillna(0)
        thk_ratio = (thk_tokens / out_tokens).clip(0.0, 1.0)

        df_window["thinking_s"] = gen_duration_s * thk_ratio
        df_window["streaming_s"] = (gen_duration_s - df_window["thinking_s"]).clip(lower=0.0)
        df_window["total_latency_s"] = (
            df_window["client_prep_s"] + df_window["ttft_s"] + gen_duration_s
        )

        turn_labels = [f"Turn #{s}" for s in df_window["step_index"]]

        fig_waterfall = go.Figure()

        # 1. Client Prep (Slate)
        fig_waterfall.add_trace(
            go.Bar(
                y=turn_labels,
                x=df_window["client_prep_s"],
                name="Client Prep",
                orientation="h",
                marker=dict(color="#5F6368"),
                customdata=df_window[["client_prep_ms", "step_index", "model"]],
                hovertemplate="<b>%{y}</b><br>Client Prep: %{customdata[0]:,} ms<br>Context assembly & tool ingestion<extra></extra>",
            )
        )

        # 2. TTFT Server Prefill (Amber)
        fig_waterfall.add_trace(
            go.Bar(
                y=turn_labels,
                x=df_window["ttft_s"],
                name="TTFT (Prefill)",
                orientation="h",
                marker=dict(color="#FBBC04"),
                customdata=df_window[["ttft_latency_ms", "total_prompt_tokens", "cached_tokens"]],
                hovertemplate="<b>%{y}</b><br>TTFT: %{customdata[0]:,} ms<br>Prompt: %{customdata[1]:,} tok (%{customdata[2]:,} cached)<extra></extra>",
            )
        )

        # 3. Thinking Phase (Purple)
        fig_waterfall.add_trace(
            go.Bar(
                y=turn_labels,
                x=df_window["thinking_s"],
                name="Thinking Reasoning",
                orientation="h",
                marker=dict(color="#A142F4"),
                customdata=df_window[["thinking_tokens", "thinking_s"]],
                hovertemplate="<b>%{y}</b><br>Thinking: %{x:.2f}s<br>Reasoning Tokens: %{customdata[0]:,}<extra></extra>",
            )
        )

        # 4. Streaming Output (Google Blue)
        fig_waterfall.add_trace(
            go.Bar(
                y=turn_labels,
                x=df_window["streaming_s"],
                name="Output Streaming",
                orientation="h",
                marker=dict(color="#1A73E8"),
                customdata=df_window[["content_tokens", "tokens_per_second", "total_latency_s"]],
                hovertemplate="<b>%{y}</b><br>Streaming: %{x:.2f}s<br>Content Tokens: %{customdata[0]:,}<br>Speed: %{customdata[1]:.1f} tok/s<br><b>Total Turn Time: %{customdata[2]:.2f}s</b><extra></extra>",
            )
        )

        waterfall_height = max(340, len(df_window) * 26 + 90)

        fig_waterfall.update_layout(
            barmode="stack",
            height=waterfall_height,
            margin=dict(l=80, r=20, t=30, b=30),
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font=dict(family="Roboto, sans-serif", size=12, color="#202124"),
            xaxis=dict(
                title=dict(text="Turn Execution Duration (Seconds)", font=dict(size=12, color="#5F6368")),
                gridcolor="#F1F3F4",
                linecolor="#DADCE0",
                showline=True,
                zeroline=False,
                tickfont=dict(size=11, color="#5F6368"),
            ),
            yaxis=dict(
                autorange="reversed",  # Sequential waterfall flowing top to bottom
                automargin=True,
                showline=True,
                linecolor="#DADCE0",
                gridcolor="#F8F9FA",
                tickfont=dict(family="Roboto Mono, monospace", size=11, color="#3C4043"),
                ticks="outside",
                ticklen=4,
                tickcolor="#DADCE0",
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=11, color="#3C4043"),
            ),
        )

        st.plotly_chart(fig_waterfall, use_container_width=True, theme=None)

        # 5. Interactive Turn Selector for Context Inspector
        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
        turn_options = df_window["step_index"].tolist()
        def_turn_idx = len(turn_options) - 1

        c_t1, c_t2 = st.columns([2, 1])
        with c_t1:
            st.markdown(
                """
                <div style="font-size: 16px; font-weight: 700; color: #202124; font-family: 'Google Sans';">
                    🔍 Structural Context Inspector (Context Map)
                </div>
                <div style="font-size: 12px; color: #5F6368; margin-top: 2px;">
                    Select any turn above to inspect the exact architectural building blocks that formed the model's prompt.
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c_t2:
            selected_step = st.selectbox(
                "SELECT TURN TO INSPECT",
                turn_options,
                index=def_turn_idx,
                key="selected_telemetry_turn",
                format_func=lambda s: f"Turn #{s} ({df_window.loc[df_window['step_index']==s, 'total_tokens'].values[0]:,} tokens | {format_step_cost(float(df_window.loc[df_window['step_index']==s, 'cost_usd'].values[0]))[0]})",
            )


        # 6. Extract metrics for selected turn
        turn_row = df_window[df_window["step_index"] == selected_step].iloc[0]
        prep_ms = int(turn_row["client_prep_ms"])
        ttft_ms = int(turn_row["ttft_latency_ms"])
        gen_ms = int(turn_row["generation_duration_ms"])
        tot_s = float(turn_row["total_latency_s"])
        c_tok = int(turn_row["cached_tokens"])
        fresh_tok = int(turn_row["uncached_prompt_tokens"])
        tot_turn_prompt = c_tok + fresh_tok
        if tot_turn_prompt > 0:
            cache_pct = round((c_tok / tot_turn_prompt) * 100.0, 1)
            fresh_pct = round(100.0 - cache_pct, 1)
        else:
            cache_pct = 0.0
            fresh_pct = 100.0
        thk_tok = int(turn_row["thinking_tokens"])
        cnt_tok = int(turn_row["content_tokens"])
        speed = (
            float(turn_row["tokens_per_second"])
            if pd.notnull(turn_row["tokens_per_second"])
            else 0.0
        )
        model_name = str(turn_row["model"])

        # 7. Turn Summary KPI Cards (Matching Exact 110px Height)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        tk1, tk2, tk3, tk4 = st.columns(4)

        with tk1:
            st.html(
                f"""
                <div class="telemetry-kpi-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #5F6368; letter-spacing: 0.5px;">TURN LATENCY</span>
                        <div class="kpi-icon-container" style="background: #E8F0FE; color: #1A73E8;">⏱️</div>
                    </div>
                    <div>
                        <div style="font-size: 1.45rem; font-weight: 700; color: #202124; font-family: 'Google Sans', sans-serif;">{tot_s:.2f}s</div>
                        <div style="font-size: 11px; color: #5F6368; margin-top: 2px;">TTFT: {ttft_ms/1000.0:.2f}s | Stream: {gen_ms/1000.0:.2f}s</div>
                    </div>
                </div>
                """
            )

        with tk2:
            st.html(
                f"""
                <div class="telemetry-kpi-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #5F6368; letter-spacing: 0.5px;">PROMPT CONTEXT</span>
                        <div class="kpi-icon-container" style="background: #E6F4EA; color: #137333;">💾</div>
                    </div>
                    <div>
                        <div style="font-size: 1.45rem; font-weight: 700; color: #202124; font-family: 'Google Sans', sans-serif;">{fmt_tok(tot_turn_prompt)}</div>
                        <div style="font-size: 11px; color: #5F6368; margin-top: 2px;">{cache_pct}% Cached | {fresh_pct}% Fresh</div>
                    </div>
                </div>
                """
            )

        with tk3:
            st.html(
                f"""
                <div class="telemetry-kpi-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #5F6368; letter-spacing: 0.5px;">GENERATION FOOTPRINT</span>
                        <div class="kpi-icon-container" style="background: #F3E8FD; color: #8430CE;">🧠</div>
                    </div>
                    <div>
                        <div style="font-size: 1.45rem; font-weight: 700; color: #202124; font-family: 'Google Sans', sans-serif;">{int(turn_row['output_tokens']):,} tok</div>
                        <div style="font-size: 11px; color: #5F6368; margin-top: 2px;">Thinking: {thk_tok:,} | Content: {cnt_tok:,}</div>
                    </div>
                </div>
                """
            )

        with tk4:
            st.html(
                f"""
                <div class="telemetry-kpi-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <span style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: #5F6368; letter-spacing: 0.5px;">STREAMING VELOCITY</span>
                        <div class="kpi-icon-container" style="background: #FEF7E0; color: #B06000;">⚡</div>
                    </div>
                    <div>
                        <div style="font-size: 1.45rem; font-weight: 700; color: #202124; font-family: 'Google Sans', sans-serif;">{speed:.1f} tok/s</div>
                        <div style="font-size: 11px; color: #5F6368; margin-top: 2px;">Model: {model_name}</div>
                    </div>
                </div>
                """
            )

        # 8. Directional Context Footprint Bar
        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        cache_status_badge = (
            '<span class="context-card-badge" style="background: #E6F4EA; color: #137333;">🟢 HIGH CACHE EFFICIENCY</span>'
            if cache_pct >= 70
            else '<span class="context-card-badge" style="background: #FEF7E0; color: #B06000;">🟡 MODERATE CACHE</span>'
            if cache_pct >= 30
            else '<span class="context-card-badge" style="background: #FCE8E6; color: #C5221F;">🔴 COLD PREFILL (CACHE MISS)</span>'
        )

        st.html(
            f"""
            <div class="context-footprint-container">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 13px; font-weight: 700; color: #202124; font-family: 'Google Sans', sans-serif;">
                            🗺️ Directional Context Footprint: Turn #{selected_step}
                        </span>
                        <span style="font-size: 12px; color: #5F6368; margin-left: 8px;">
                            (Total Prompt: {tot_turn_prompt:,} tokens)
                        </span>
                    </div>
                    <div>{cache_status_badge}</div>
                </div>
                <div class="context-bar-segmented">
                    <div style="width: {cache_pct}%; background-color: #34A853; height: 100%;" title="Cached Memory: {c_tok:,} tokens ({cache_pct}%)"></div>
                    <div style="width: {fresh_pct}%; background-color: #FBBC04; height: 100%;" title="Fresh Working Injections: {fresh_tok:,} tokens ({fresh_pct}%)"></div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: #5F6368;">
                    <span>🟢 <strong>{cache_pct}% Cached Memory</strong> ({c_tok:,} tokens from session checkpoint & earlier turns)</span>
                    <span>🟠 <strong>{fresh_pct}% Fresh Injections</strong> ({fresh_tok:,} tokens from latest tool outputs & user prompt)</span>
                </div>
            </div>
            """
        )

        # 9. Extract Structural Context Metadata
        cm_raw = turn_row.get("context_metadata")
        cm = None
        if pd.notnull(cm_raw) and str(cm_raw).strip() not in ("", "None", "NULL"):
            try:
                cm = json.loads(str(cm_raw))
            except Exception:
                pass

        if cm is None and context_extractor:
            try:
                cm = context_extractor.extract_turn_context_metadata(
                    conversation_id=selected_conv_id,
                    step_index=int(selected_step),
                    prompt_tokens=tot_turn_prompt,
                    cached_tokens=c_tok,
                )
            except Exception:
                pass

        if cm is None:
            if context_extractor:
                cm = context_extractor.generate_fallback_context(
                    step_index=int(selected_step),
                    prompt_tokens=tot_turn_prompt,
                    cached_tokens=c_tok,
                    tool_name=str(turn_row.get("tool_name", "")),
                )
            else:
                cm = {
                    "user_request_preview": "User prompt and task directives",
                    "timestamp": "",
                    "has_media": False,
                    "media_files": [],
                    "checkpoint_active": cache_pct > 50,
                    "checkpoint_step_index": 0 if cache_pct > 50 else None,
                    "working_injections": {
                        "command_runs": 1,
                        "file_reads": 1,
                        "file_edits": 0,
                        "web_searches": 0,
                        "recent_commands": [],
                        "recent_files": [],
                        "intermediate_tools": [],
                    },
                    "static_scope": {
                        "native_tools_count": 14,
                        "native_tools_sample": ["run_command", "view_file", "replace_file_content"],
                        "mcp_servers": ["cloudrun", "gmp-code-assist", "sequential-thinking"],
                        "skills_count": 42,
                        "rules_count": 0,
                        "persona": "Antigravity Autonomous Pair Programmer",
                        "os": "Linux x86_64",
                    },
                }

        scope = cm.get("static_scope", {})
        working = cm.get("working_injections", {})
        chk_active = cm.get("checkpoint_active", False)
        chk_idx = cm.get("checkpoint_step_index")
        has_media = cm.get("has_media", False)
        media_list = cm.get("media_files", [])

        # 10. The 5 Structural Context Cards (2-Row Uniform Grid)
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

        # Row 1: Static Directives, Tool Registry, Skills in Scope (3 Columns)
        c_sc1, c_sc2, c_sc3 = st.columns(3)

        with c_sc1:
            st.html(
                f"""
                <div class="context-card">
                    <div class="context-card-header">
                        <span style="font-size: 15px;">🏛️</span>
                        <span>1. Static Directives & Persona</span>
                    </div>
                    <div class="context-card-item">
                        <span>🤖</span>
                        <div><strong>Role:</strong> {scope.get('persona', 'Antigravity AI Pair Programmer')}</div>
                    </div>
                    <div class="context-card-item">
                        <span>💻</span>
                        <div><strong>Host OS:</strong> {scope.get('os', 'Linux x86_64')}</div>
                    </div>
                    <div class="context-card-item">
                        <span>📋</span>
                        <div><strong>Global & Project Rules:</strong> {scope.get('rules_count', 0)} active</div>
                    </div>
                    <div style="margin-top: 10px; font-size: 11px; color: #5F6368; border-top: 1px dashed #E8EAED; padding-top: 6px;">
                        Fixed base system envelope (~1,200 tokens)
                    </div>
                </div>
                """
            )

        with c_sc2:
            mcp_badges = " ".join(
                [f'<span class="context-card-badge" style="background: #E8F0FE; color: #1967D2;">{s}</span>' for s in scope.get('mcp_servers', [])]
            )
            st.html(
                f"""
                <div class="context-card">
                    <div class="context-card-header">
                        <span style="font-size: 15px;">🛠️</span>
                        <span>2. Capabilities & Tool Registry</span>
                    </div>
                    <div class="context-card-item">
                        <span>⚙️</span>
                        <div><strong>Native Tools:</strong> {scope.get('native_tools_count', 14)} declared</div>
                    </div>
                    <div class="context-card-item" style="flex-wrap: wrap;">
                        <span>🔌</span>
                        <div><strong>Active MCP Servers:</strong><br><div style="margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap;">{mcp_badges}</div></div>
                    </div>
                    <div style="margin-top: 10px; font-size: 11px; color: #5F6368; border-top: 1px dashed #E8EAED; padding-top: 6px;">
                        Full function calling JSON schemas (~5,500 tokens)
                    </div>
                </div>
                """
            )

        with c_sc3:
            st.html(
                f"""
                <div class="context-card">
                    <div class="context-card-header">
                        <span style="font-size: 15px;">🧩</span>
                        <span>3. Skills in Scope</span>
                    </div>
                    <div class="context-card-item">
                        <span>📚</span>
                        <div><strong>Registered Skills:</strong> {scope.get('skills_count', 42)} skills</div>
                    </div>
                    <div class="context-card-item">
                        <span>⚡</span>
                        <div><strong>Disclosure Mode:</strong> <span class="context-card-badge" style="background: #E6F4EA; color: #137333;">Progressive</span></div>
                    </div>
                    <div class="context-card-item">
                        <span>🎯</span>
                        <div><strong>Categories:</strong> Cloud, Data, Frontend, Science</div>
                    </div>
                    <div style="margin-top: 10px; font-size: 11px; color: #5F6368; border-top: 1px dashed #E8EAED; padding-top: 6px;">
                        Lightweight catalog in prompt; full skill loaded on-demand
                    </div>
                </div>
                """
            )

        # Row 2: Working Injections, User Request & Media (2 Columns)
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        c_sc4, c_sc5 = st.columns([1.3, 1])

        with c_sc4:
            chk_label = (
                f'<span class="context-card-badge" style="background: #E8F0FE; color: #1967D2;">Active Checkpoint (Step #{chk_idx})</span>'
                if chk_active
                else '<span class="context-card-badge" style="background: #F1F3F4; color: #5F6368;">Raw Trajectory Window</span>'
            )
            recent_cmds = working.get("recent_commands", [])
            recent_files = working.get("recent_files", [])

            cmd_html = (
                f'<div style="font-family: \'Roboto Mono\', monospace; font-size: 11px; color: #202124; background: #F8F9FA; padding: 4px 8px; border-radius: 4px; margin-top: 4px;">$ {recent_cmds[0]}</div>'
                if recent_cmds
                else '<span style="color: #80868B; font-size: 11px;">None</span>'
            )
            file_html = (
                ", ".join([f'<code>{f}</code>' for f in recent_files])
                if recent_files
                else '<span style="color: #80868B; font-size: 11px;">None</span>'
            )

            st.html(
                f"""
                <div class="context-card">
                    <div class="context-card-header">
                        <span style="font-size: 15px;">📥</span>
                        <span>4. Working Injections (Preceding Tool Payloads)</span>
                    </div>
                    <div class="context-card-item">
                        <span>🧠</span>
                        <div><strong>Memory State:</strong> {chk_label}</div>
                    </div>
                    <div class="context-card-item">
                        <span>💻</span>
                        <div><strong>Command Outputs:</strong> {working.get('command_runs', 0)} executed {cmd_html}</div>
                    </div>
                    <div class="context-card-item">
                        <span>📄</span>
                        <div><strong>File Injections:</strong> {working.get('file_reads', 0)} reads {file_html}</div>
                    </div>
                    <div style="margin-top: 10px; font-size: 11px; color: #5F6368; border-top: 1px dashed #E8EAED; padding-top: 6px;">
                        Intermediate execution payloads that fed directly into this turn
                    </div>
                </div>
                """
            )

        with c_sc5:
            prompt_snip = cm.get("user_request_preview", "User prompt in scope")
            ts_label = cm.get("timestamp") or str(turn_row["timestamp"])[:19]
            media_badge = (
                f'<span class="context-card-badge" style="background: #E8F0FE; color: #1967D2;">📸 {len(media_list)} Image(s) Attached</span>'
                if has_media
                else '<span class="context-card-badge" style="background: #F1F3F4; color: #80868B;">No Media</span>'
            )

            st.html(
                f"""
                <div class="context-card">
                    <div class="context-card-header">
                        <span style="font-size: 15px;">💬</span>
                        <span>5. User Request & Multimodal</span>
                    </div>
                    <div class="context-card-item">
                        <span>🕒</span>
                        <div><strong>Dispatched:</strong> {ts_label}</div>
                    </div>
                    <div class="context-card-item">
                        <span>🖼️</span>
                        <div><strong>Multimodal:</strong> {media_badge}</div>
                    </div>
                    <div class="context-card-item" style="flex-direction: column;">
                        <span style="font-weight: 600; font-size: 11px; color: #5F6368; margin-bottom: 2px;">USER DIRECTIVE:</span>
                        <div style="background: #F8F9FA; border-left: 3px solid #1A73E8; padding: 6px 10px; font-size: 11px; color: #202124; line-height: 1.4; border-radius: 0 4px 4px 0; max-height: 70px; overflow-y: auto;">
                            "{prompt_snip}"
                        </div>
                    </div>
                </div>
                """
            )

except Exception as e:
    st.error(f"Error loading Token Observability dashboard: {e}")
    st.info(
        f"Make sure Cloud Run service account has BigQuery read permissions on {GCP_PROJECT}.{DATASET_ID}."
    )

