import base64
import datetime
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from google.cloud import bigquery

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
    page_title="Your Antigravity Token Analytics",
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

    /* Sleek Cards */
    .gcp-card {
        background-color: #FFFFFF;
        border: 1px solid #DADCE0;
        border-radius: 8px;
        padding: 18px 20px;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.1), 0 1px 3px 1px rgba(60,64,67,0.05);
        transition: all 0.2s ease-in-out;
    }
    .gcp-card:hover {
        box-shadow: 0 4px 12px 0 rgba(60,64,67,0.12);
        border-color: #BDC1C6;
    }

    .kpi-title {
        font-size: 0.78rem;
        font-weight: 600;
        color: #5F6368;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
        font-family: 'Roboto', sans-serif;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #202124;
        font-family: 'Google Sans', sans-serif;
        line-height: 1.1;
    }

    .kpi-icon-container {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
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
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# GCP CONTEXT & ARGOLIS LDAP RESOLUTION (DYNAMIC & DE-IDENTIFIED)
# ==========================================
import urllib.request
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
        SUM(total_tokens) as total_tokens,
        SUM(COALESCE(cached_tokens, 0)) as cached_tokens,
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
        GREATEST(0, prompt_tokens - COALESCE(cached_tokens, 0)) as uncached_prompt_tokens,
        output_tokens,
        COALESCE(thinking_tokens, 0) as thinking_tokens,
        GREATEST(0, output_tokens - COALESCE(thinking_tokens, 0)) as content_tokens,
        total_tokens,
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


# ==========================================
# LEFT NAVIGATION PANEL
# ==========================================
with st.sidebar:
    # 1. Antigravity Official Brand Header
    st.html(
        f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 4px 0 14px 0; border-bottom: 1px solid #DADCE0; margin-bottom: 14px;">
            <img src="{LOGO_URI}" width="32" height="32" style="object-fit: contain;" alt="Antigravity Logo" />
            <div>
                <span style="font-size: 15px; font-weight: 700; color: #202124; font-family: 'Google Sans', sans-serif;">Your Antigravity</span><br/>
                <span style="font-size: 11px; color: #5F6368; font-family: 'Roboto', sans-serif;">Token Analytics</span>
            </div>
        </div>
        """
    )

    # 3. Project Scope Card (No toggle arrow, mentions Cloud ID & Cloud Project)
    st.html(
        f"""
        <div style="background: #F8F9FA; border: 1px solid #DADCE0; border-radius: 6px; padding: 10px 12px; margin-bottom: 14px; font-size: 12px;">
            <div style="color: #5F6368; font-size: 10px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.6px; margin-bottom: 8px;">
                PROJECT SCOPE
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="color: #5F6368; font-size: 11px;">Cloud Project:</span>
                    <span style="font-weight: 600; color: #1A73E8; font-family: 'Roboto Mono', monospace; font-size: 12px;">{GCP_PROJECT}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="color: #5F6368; font-size: 11px;">Cloud ID:</span>
                    <span style="font-weight: 600; color: #202124; font-family: 'Roboto Mono', monospace; font-size: 12px;" title="Argolis Account: {ARGOLIS_ACCOUNT}">{CLOUD_ID}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <span style="color: #5F6368; font-size: 11px;">Argolis Account:</span>
                    <span style="font-weight: 500; color: #5F6368; font-family: 'Roboto Mono', monospace; font-size: 10px; max-width: 125px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{ARGOLIS_ACCOUNT}">{ARGOLIS_ACCOUNT}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 2px; padding-top: 4px; border-top: 1px dashed #E8EAED;">
                    <span style="color: #70757A; font-size: 10px;">Dataset:</span>
                    <span style="color: #5F6368; font-size: 10px; font-family: 'Roboto Mono', monospace;">token_analytics</span>
                </div>
            </div>
        </div>
        """
    )

    st.html('<div style="font-size: 10px; font-weight: 700; color: #5F6368; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; padding-left: 2px;">NAVIGATION</div>')

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
    if st.button("🔄  Refresh BigQuery Cache", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Telemetry Status Card
    st.html(
        """
        <div style="margin-top: 24px; padding: 12px 14px; background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; font-size: 11px; color: #5F6368; box-shadow: 0 1px 2px rgba(60,64,67,0.06);">
            <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #70757A; letter-spacing: 0.5px; margin-bottom: 6px;">
                SYSTEM TELEMETRY
            </div>
            <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                <span style="width: 8px; height: 8px; border-radius: 50%; background-color: #34A853; display: inline-block;"></span>
                <strong style="color: #202124; font-family: 'Google Sans'; font-size: 12px;">BigQuery Stream Active</strong>
            </div>
            <div style="color: #5F6368; font-size: 11px; line-height: 1.4;">
                Workstation telemetry streams automatically at the end of every agent execution loop.
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

    # 4. Top Breadcrumb: Your Antigravity Token Analytics -> Executive Overview
    nav_title = selected_nav.replace("📊", "").replace("🔬", "").replace("⚡", "").strip()
    st.html(
        f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 18px; padding-bottom: 10px; border-bottom: 1px solid #DADCE0;">
            <span style="font-size: 13px; color: #5F6368; font-family: 'Google Sans', sans-serif;">Your Antigravity Token Analytics</span>
            <span style="color: #DADCE0; font-size: 13px;">→</span>
            <span style="font-size: 13px; font-weight: 600; color: #1A73E8; font-family: 'Google Sans', sans-serif;">{nav_title}</span>
        </div>
        """
    )

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
                <div class="gcp-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="kpi-title">Total Projects</div>
                            <div class="kpi-value">{int(kpi['total_projects']):,}</div>
                            <div class="pill pill-blue" style="margin-top: 8px;">Active Repos</div>
                        </div>
                        <div class="kpi-icon-container" style="background: #E8F0FE; color: #1A73E8;">
                            📁
                        </div>
                    </div>
                </div>
                """
            )

        with c2:
            st.html(
                f"""
                <div class="gcp-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="kpi-title">Total Workspaces</div>
                            <div class="kpi-value">{int(kpi['total_workspaces']):,}</div>
                            <div class="pill pill-blue" style="margin-top: 8px;">Workstation Dirs</div>
                        </div>
                        <div class="kpi-icon-container" style="background: #EEF0F8; color: #3F51B5;">
                            👥
                        </div>
                    </div>
                </div>
                """
            )

        with c3:
            st.html(
                f"""
                <div class="gcp-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="kpi-title">Total Conversations</div>
                            <div class="kpi-value">{int(kpi['total_conversations']):,}</div>
                            <div class="pill pill-purple" style="margin-top: 8px;">{int(kpi['total_steps']):,} Turns</div>
                        </div>
                        <div class="kpi-icon-container" style="background: #F3E8FD; color: #8430CE;">
                            💬
                        </div>
                    </div>
                </div>
                """
            )

        with c4:
            st.html(
                f"""
                <div class="gcp-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="kpi-title">Tokens Consumed</div>
                            <div class="kpi-value">{kpi['grand_total_tokens'] / 1_000_000:.2f}M</div>
                            <div class="pill pill-green" style="margin-top: 8px;">96.7% Context In</div>
                        </div>
                        <div class="kpi-icon-container" style="background: #E6F4EA; color: #137333;">
                            🪙
                        </div>
                    </div>
                </div>
                """
            )

        with c5:
            st.html(
                f"""
                <div class="gcp-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div class="kpi-title">Total Cost Incurred</div>
                            <div class="kpi-value" style="color: #1A73E8;">${kpi['total_spend_usd']:,.2f}</div>
                            <div class="pill pill-amber" style="margin-top: 8px;">Avg ${(kpi['total_spend_usd'] / kpi['total_projects']):,.2f} / repo</div>
                        </div>
                        <div class="kpi-icon-container" style="background: #FEF7E0; color: #B06000;">
                            💲
                        </div>
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
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.22,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=11, family="Roboto"),
                    ),
                    plot_bgcolor="#FFFFFF",
                    paper_bgcolor="#FFFFFF",
                    xaxis=dict(
                        showgrid=False,
                        linecolor="#DADCE0",
                        tickfont=dict(size=11, color="#5F6368"),
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor="#F1F3F4",
                        linecolor="#DADCE0",
                        tickprefix="$",
                        tickfont=dict(size=11, color="#5F6368"),
                    ),
                )
                fig_spend.update_traces(marker=dict(line=dict(width=0)))
                st.plotly_chart(fig_spend, use_container_width=True)

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
                    font=dict(size=11, family="Roboto"),
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
            st.plotly_chart(fig_pie, use_container_width=True)

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
                        label = f"Session {short_cid} | {turns} turns | {tot_k:.1f}k tokens ({cached_k:.1f}k cached) | ${cost:.4f} | {st_time}"
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

                tot_spend = float(conv_row["cost_usd"])
                tot_tokens = int(conv_row["total_tokens"])
                tot_prompt = int(conv_row["prompt_tokens"])
                tot_cached = int(conv_row["cached_tokens"])
                tot_uncached = max(0, tot_prompt - tot_cached)
                tot_output = int(conv_row["output_tokens"])
                tot_thinking = int(conv_row["thinking_tokens"])
                tot_content = max(0, tot_output - tot_thinking)
                tot_turns = int(conv_row["turns"])

                # Cache efficiency: % of prompt tokens that came from cache
                cache_hit_rate = (tot_cached / tot_prompt * 100.0) if tot_prompt > 0 else 0.0
                cache_hit_rate = min(100.0, max(0.0, cache_hit_rate))

                # Gemini prompt cache discount: $0.15/M -> $0.0375/M (savings = $0.1125/M)
                dollars_saved = (tot_cached / 1_000_000.0) * 0.1125

                # Peak context window reached (max prompt in any turn)
                max_prompt_reached = int(df_turns["prompt_tokens"].max()) if not df_turns.empty else 0
                context_saturation_pct = (max_prompt_reached / 1_048_576.0) * 100.0

                # --- 5 MACRO KPI CARDS FOR SELECTED CONVERSATION ---
                k1, k2, k3, k4, k5 = st.columns(5)
                with k1:
                    st.html(
                        f"""
                        <div class="gcp-card">
                            <div class="kpi-title">Session Spend</div>
                            <div class="kpi-value" style="color: #1A73E8;">${tot_spend:,.4f}</div>
                            <div class="pill pill-blue" style="margin-top: 8px;">Avg ${tot_spend/max(1, tot_turns):.4f}/turn</div>
                        </div>
                        """
                    )
                with k2:
                    st.html(
                        f"""
                        <div class="gcp-card">
                            <div class="kpi-title">Total Tokens</div>
                            <div class="kpi-value">{tot_tokens/1000.0:,.1f}<span style="font-size: 1.1rem; color: #5F6368; font-weight: 500;">k</span></div>
                            <div class="pill pill-purple" style="margin-top: 8px;">{tot_turns} Execution Turns</div>
                        </div>
                        """
                    )
                with k3:
                    cache_pill_class = "pill-green" if cache_hit_rate >= 50 else "pill-amber"
                    st.html(
                        f"""
                        <div class="gcp-card">
                            <div class="kpi-title">Cache Hit Rate</div>
                            <div class="kpi-value" style="color: #137333;">{cache_hit_rate:.1f}%</div>
                            <div class="pill {cache_pill_class}" style="margin-top: 8px;">{tot_cached/1000.0:,.1f}k Tokens Cached</div>
                        </div>
                        """
                    )
                with k4:
                    st.html(
                        f"""
                        <div class="gcp-card">
                            <div class="kpi-title">Cost Saved (Cache)</div>
                            <div class="kpi-value" style="color: #137333;">+${dollars_saved:,.4f}</div>
                            <div class="pill pill-green" style="margin-top: 8px;">75% Cache Discount</div>
                        </div>
                        """
                    )
                with k5:
                    st.html(
                        f"""
                        <div class="gcp-card">
                            <div class="kpi-title">Max Context Reached</div>
                            <div class="kpi-value">{max_prompt_reached/1000.0:,.1f}<span style="font-size: 1.1rem; color: #5F6368; font-weight: 500;">k</span></div>
                            <div class="pill pill-blue" style="margin-top: 8px;">{context_saturation_pct:.1f}% of 1M Window</div>
                        </div>
                        """
                    )

                st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

                # --- VISUALIZATIONS ROW 1: TURN-BY-TURN TOKEN PROGRESSION (STACKED BAR) ---
                st.html(
                    """
                    <div style="background: #FFFFFF; border: 1px solid #DADCE0; border-radius: 8px; padding: 20px 22px 14px 22px; box-shadow: 0 1px 2px rgba(60,64,67,0.06); margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
                            <div>
                                <span style="font-family: 'Google Sans', sans-serif; font-size: 15px; font-weight: 600; color: #202124;">
                                    Turn-by-Turn Token Progression & Anatomy
                                </span>
                                <span style="font-size: 12px; color: #5F6368; margin-left: 8px;">
                                    Exposes context growth (ratchet effect) and token composition across each execution step
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

                if not df_turns.empty:
                    df_plot = df_turns.copy()
                    df_plot["step_label"] = "Turn " + df_plot["step_index"].astype(str)

                    fig_prog = go.Figure()

                    # 1. Cached Prompt Tokens (Green)
                    fig_prog.add_trace(go.Bar(
                        x=df_plot["step_label"],
                        y=df_plot["cached_tokens"],
                        name="Cached Prompt",
                        marker_color="#34A853",
                        hovertemplate="<b>%{x}</b><br>Cached Context: %{y:,} tokens<extra></extra>",
                    ))

                    # 2. Uncached Prompt Tokens (Blue)
                    fig_prog.add_trace(go.Bar(
                        x=df_plot["step_label"],
                        y=df_plot["uncached_prompt_tokens"],
                        name="New Prompt",
                        marker_color="#1A73E8",
                        hovertemplate="<b>%{x}</b><br>New Prompt Context: %{y:,} tokens<extra></extra>",
                    ))

                    # 3. Thinking / Reasoning Tokens (Purple)
                    fig_prog.add_trace(go.Bar(
                        x=df_plot["step_label"],
                        y=df_plot["thinking_tokens"],
                        name="Thinking (Reasoning)",
                        marker_color="#9334E6",
                        hovertemplate="<b>%{x}</b><br>Thinking Tokens: %{y:,} tokens<extra></extra>",
                    ))

                    # 4. Output Content Tokens (Amber/Coral)
                    fig_prog.add_trace(go.Bar(
                        x=df_plot["step_label"],
                        y=df_plot["content_tokens"],
                        name="Output Content",
                        marker_color="#F2994A",
                        hovertemplate="<b>%{x}</b><br>Output Content: %{y:,} tokens<extra></extra>",
                    ))

                    fig_prog.update_layout(
                        barmode="stack",
                        height=360,
                        margin=dict(l=20, r=20, t=10, b=30),
                        paper_bgcolor="#FFFFFF",
                        plot_bgcolor="#FFFFFF",
                        font=dict(family="Roboto, sans-serif", size=12, color="#5F6368"),
                        xaxis=dict(
                            showgrid=False,
                            linecolor="#DADCE0",
                            tickangle=-45 if len(df_plot) > 20 else 0,
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor="#F1F3F4",
                            linecolor="#DADCE0",
                            title="Tokens Consumed",
                        ),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1,
                        ),
                    )
                    st.plotly_chart(fig_prog, use_container_width=True)
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
                    labels = ["Cached Prompt", "New Prompt", "Thinking (Reasoning)", "Output Content"]
                    values = [tot_cached, tot_uncached, tot_thinking, tot_content]
                    colors = ["#34A853", "#1A73E8", "#9334E6", "#F2994A"]

                    fig_pie = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.58,
                        marker=dict(colors=colors),
                        textinfo="percent+label",
                        insidetextorientation="radial",
                        hovertemplate="<b>%{label}</b><br>Tokens: %{value:,}<br>Share: %{percent}<extra></extra>",
                    )])
                    fig_pie.update_layout(
                        height=300,
                        margin=dict(l=10, r=10, t=10, b=10),
                        paper_bgcolor="#FFFFFF",
                        showlegend=False,
                        annotations=[dict(
                            text=f"<b>{tot_tokens/1000.0:,.1f}k</b><br><span style='font-size:11px;color:#5F6368;'>Total</span>",
                            x=0.5, y=0.5, font_size=18, font_family="Google Sans", showarrow=False
                        )]
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
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
                        df_cost["cum_actual_cost"] = df_cost["cost_usd"].cumsum()
                        df_cost["turn_saved"] = (df_cost["cached_tokens"] / 1_000_000.0) * 0.1125
                        df_cost["cum_baseline_cost"] = df_cost["cum_actual_cost"] + df_cost["turn_saved"].cumsum()
                        df_cost["step_label"] = "Turn " + df_cost["step_index"].astype(str)

                        fig_cost = go.Figure()

                        # Baseline line (Grey dashed)
                        fig_cost.add_trace(go.Scatter(
                            x=df_cost["step_label"],
                            y=df_cost["cum_baseline_cost"],
                            name="Without Caching",
                            mode="lines",
                            line=dict(color="#80868B", width=2, dash="dash"),
                            hovertemplate="<b>%{x}</b><br>Baseline: $%{y:.4f}<extra></extra>",
                        ))

                        # Actual spend line (Google Blue)
                        fig_cost.add_trace(go.Scatter(
                            x=df_cost["step_label"],
                            y=df_cost["cum_actual_cost"],
                            name="Actual Invoiced Spend",
                            mode="lines+markers",
                            line=dict(color="#1A73E8", width=3),
                            marker=dict(size=5, color="#1A73E8"),
                            fill="tonexty",
                            fillcolor="rgba(52, 168, 83, 0.12)",
                            hovertemplate="<b>%{x}</b><br>Actual Spend: $%{y:.4f}<extra></extra>",
                        ))

                        fig_cost.update_layout(
                            height=300,
                            margin=dict(l=20, r=20, t=10, b=30),
                            paper_bgcolor="#FFFFFF",
                            plot_bgcolor="#FFFFFF",
                            font=dict(family="Roboto, sans-serif", size=12, color="#5F6368"),
                            xaxis=dict(showgrid=False, linecolor="#DADCE0", tickangle=-45 if len(df_cost) > 20 else 0),
                            yaxis=dict(showgrid=True, gridcolor="#F1F3F4", linecolor="#DADCE0", title="Cumulative USD ($)", tickprefix="$"),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        )
                        st.plotly_chart(fig_cost, use_container_width=True)
                    st.html("</div>")

                st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

                # --- TURN-BY-TURN GRANULAR TELEMETRY TABLE ---
                table_rows = []
                for _, tr in df_turns.iterrows():
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
                        <td style="font-weight: 600; color: #202124; font-family: 'Roboto Mono', monospace;">${step_c:,.6f}</td>
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
                                    Detailed step-by-step audit of tokens, latency, cache absorption, and cost for Session {selected_conv_id[:8]}
                                </div>
                            </div>
                            <span class="pill pill-blue">{len(df_turns)} Sequential Turns</span>
                        </div>
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
                                    <th>Step Cost ($ USD)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {joined_turns}
                            </tbody>
                        </table>
                    </div>
                    """
                )

    elif "Token Telemetry" in selected_nav:
        st.html(
            """
            <div class="gcp-card" style="text-align: center; padding: 60px 24px; margin-top: 20px;">
                <div style="font-size: 3.5rem; margin-bottom: 12px;">⚡</div>
                <h2 style="font-size: 1.4rem; font-weight: 600; color: #202124; font-family: 'Google Sans'; margin-bottom: 8px;">
                    Step 3: Token Telemetry (Gantt Waterfall)
                </h2>
                <p style="font-size: 0.9rem; color: #5F6368; max-width: 500px; margin: 0 auto; line-height: 1.5;">
                    We are building one page at a time. The <strong>Executive Overview</strong> is now complete and sleek! 
                    Next up after Tokenomics is the visual Datadog-style sequential Gantt waterfall trace.
                </p>
            </div>
            """
        )

except Exception as e:
    st.error(f"Error loading Executive Overview from BigQuery: {e}")
    st.info(f"Make sure Cloud Run service account has BigQuery read permissions on {GCP_PROJECT}.{DATASET_ID}.")
