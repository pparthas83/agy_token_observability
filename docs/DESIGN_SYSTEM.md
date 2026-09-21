# Antigravity Token Observability — Design System & UI Specification

This document defines the authoritative design system, visual standards, and UI specifications for the **Antigravity Token Observability & FinOps Dashboard**. It serves as the baseline for all layout, typography, color palettes, and data visualization across the application.

---

## 1. Core Design Principles

The dashboard implements the **Google Cloud Console Design Language**:
- **Clarity over Clutter**: High data density with clean borders, structured spacing, and minimal visual noise.
- **Enterprise Hierarchy**: High-level executive KPIs first, followed by aggregate distributions, granular session drilldowns, and turn-level waterfalls.
- **Predictable Geometry**: Consistent 8px border radii, 1px `#DADCE0` borders, subtle box-shadows, and dedicated container padding.
- **Defensive Data Visualization**: Margins and axis labels must never clip or overlap regardless of viewport dimensions or multi-digit data magnitudes.

---

## 2. Color Palette & Design Tokens

All colors are standardized in [`dashboard/theme.py`](../dashboard/theme.py):

| Token | Hex Value | Usage / Semantics |
|---|---|---|
| `COLOR_BG` | `#F8F9FA` | Canvas background for the entire application |
| `COLOR_SURFACE` | `#FFFFFF` | Card backgrounds, tables, modal containers, chart paper |
| `COLOR_BORDER` | `#DADCE0` | Structural card borders, dividers, axis baselines |
| `COLOR_BORDER_LIGHT` | `#F1F3F4` | Grid lines, subtle row separators |
| `COLOR_TEXT_PRIMARY` | `#202124` | Metric values, card titles, section headers |
| `COLOR_TEXT_SECONDARY` | `#5F6368` | Subtitles, helper text, breadcrumbs, muted labels |
| `COLOR_TEXT_CHARCOAL` | `#3C4043` | Axis tick marks, chart legends, table row text |
| `GOOGLE_BLUE` | `#1A73E8` | Primary actions, prompt tokens, invoiced spend lines |
| `GOOGLE_GREEN` | `#1E8E3E` / `#34A853` | Cache savings, thinking tokens, high throughput |
| `GOOGLE_AMBER` | `#FBBC04` / `#F9AB00` | Output tokens, warnings, moderate latency |
| `GOOGLE_RED` | `#D93025` / `#EA4335` | High costs, critical alerts, anomalies |
| `GOOGLE_PURPLE` | `#9334E6` / `#8430CE` | Generation footprint, reasoning tokens |
| `GOOGLE_GREY` | `#80868B` | Uncached baseline, secondary series |

---

## 3. Typography Standards

The typography hierarchy strictly separates display labels, content reading, and numeric telemetry:

1. **Brand & Section Headings**: `Google Sans, sans-serif`
   - Weight: `600` or `700`
   - Usage: App header, page titles, card titles, modal headings, axis titles.
2. **Body & Descriptive Text**: `Roboto, sans-serif`
   - Weight: `400` (Regular) or `500` (Medium)
   - Usage: Descriptions, table text, tooltips, legend items.
3. **Metrics, Numbers & Hashes**: `Roboto Mono, monospace`
   - Weight: `400` or `500`
   - Usage: Token counts (`1,250,400 tok`), USD currency (`$14.49`), latencies (`2,450 ms`), step indices (`#3084`), y-axis tick values.

---

## 4. Component Specifications

### A. Metric / KPI Cards (`.telemetry-kpi-card`)
- **Background**: `#FFFFFF`
- **Border**: `1px solid #DADCE0`
- **Radius**: `8px`
- **Shadow**: `0 1px 2px rgba(60,64,67,0.06)`
- **Padding**: `16px 18px`
- **Height**: Fixed `110px` for consistent grid alignment.
- **Icon Container**: `28px x 28px` rounded circle with `rgba` tint corresponding to metric color.

### B. Data Tables (`.gcp-table-container`, `.gcp-table`)
- **Header Row**: Background `#F8F9FA`, font size `11px`, bold uppercase, color `#5F6368`, letter-spacing `0.5px`.
- **Data Rows**: White background with `#F8F9FA` hover highlight, font size `12px`, padding `10px 14px`.
- **Dividers**: Bottom border `1px solid #DADCE0`.
- **Numeric Columns**: Right-aligned or formatted with `Roboto Mono`.

### C. Status Pills (`.pill`)
- **Base**: `padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; font-family: 'Roboto Mono', monospace;`
- **Pill Types**:
  - `.pill-green`: Background `#E6F4EA`, text `#137333`
  - `.pill-blue`: Background `#E8F0FE`, text `#1A73E8`
  - `.pill-amber`: Background `#FEF7E0`, text `#B06000`
  - `.pill-purple`: Background `#F3E8FD`, text `#8430CE`
  - `.pill-grey`: Background `#F1F3F4`, text `#5F6368`

---

## 5. Plotly Data Visualization Standards

To eliminate label clipping, overlaps, and responsive layout breakage, all Plotly charts must comply with the following rules:

### A. Background & Margins
- **Paper & Plot Background**: Always `#FFFFFF` (`paper_bgcolor="#FFFFFF"`, `plot_bgcolor="#FFFFFF"`).
- **Left Margin (`margin.l`)**:
  - **Continuous Numeric / Currency Y-Axis**: Minimum `75px` (`l=75`).
  - **Categorical / Gantt Horizontal Y-Axis**: Minimum `80px` (`l=80`).
  - **Spend Bar Chart**: Minimum `60px` (`l=60`).
  - **Donut Chart**: `10px` (`l=10`).
- **Right Margin (`margin.r`)**: Minimum `25px` to `40px` to prevent boundary clipping.
- **Bottom Margin (`margin.b`)**: Minimum `40px` to `50px` for charts with x-axis labels.

### B. Y-Axis Configuration
- **Automatic Margin**: `automargin=True` is **mandatory** on all numerical/categorical y-axes.
- **Title Standoff**: When a title is specified, it must be an object with `standoff >= 14`:
  ```python
  title=dict(text="Cumulative USD ($)", standoff=14, font=dict(family="Google Sans, sans-serif", size=12, color="#3C4043"))
  ```
- **Grid & Border**: `gridcolor="#F1F3F4"`, `linecolor="#DADCE0"`.
- **Tick Font**: `tickfont=dict(family="Roboto Mono, monospace", size=11, color="#3C4043")`.

### C. X-Axis Endpoint Labels (Trajectory Charts)
- **Do NOT rely on default tick label centering** for extreme endpoints (e.g. `x = curr_turn_no`). Because the point lies on the bounding box, centered text will overflow the canvas and Plotly's collision detection will hide the label.
- **Approved Implementation**: Use paper-anchored annotations:
  ```python
  annotations=[
      dict(xref="paper", yref="paper", x=0.0, y=-0.08, xanchor="left", yanchor="top",
           text=f"First Turn (#{first_turn_no})", showarrow=False,
           font=dict(size=11, family="Google Sans, sans-serif", color="#3C4043")),
      dict(xref="paper", yref="paper", x=1.0, y=-0.08, xanchor="right", yanchor="top",
           text=f"Current Turn (#{curr_turn_no})", showarrow=False,
           font=dict(size=11, family="Google Sans, sans-serif", color="#3C4043")),
  ]
  ```
  Paired with:
  ```python
  xaxis=dict(showgrid=False, showticklabels=False, linecolor="#DADCE0",
             ticks="outside", ticklen=4, tickcolor="#DADCE0",
             tickmode="array", tickvals=[first_turn_no, curr_turn_no], zeroline=False)
  ```

---

## 6. Page-by-Page Specifications

### 1. Executive Overview (`nav == "📊 Executive Overview"`)
- **KPI Summary Grid**: 5 metric cards across the top:
  1. *Total Invoiced Spend* (`$X.XX USD`)
  2. *Total Token Footprint* (`XX.XX M Tokens`)
  3. *Prompt Cache Efficiency* (`XX.X% Cached`)
  4. *Average Cost per Turn* (`$0.XXXX / turn`)
  5. *Total Sessions Monitored* (`X Sessions`)
- **Charts Grid**:
  - Left Column (2/3): Daily Invoiced Spend (`fig_spend`), stacked bar with Google categorical colors, `margin.l=60`, `automargin=True`.
  - Right Column (1/3): Token Distribution by Model (`fig_pie`), donut chart with center total annotation.
- **Portfolio Table**: Ranked breakdown of codebases by spend with progress bar indicators and throughput pills.

### 2. Tokenomics Deep Dive (`nav == "🔬 Tokenomics Deep Dive"`)
- **Filter Bar**: Workspace codebase selector and Session dropdown inside a white card container.
- **Session KPI Cards**: 4 cards showing Session Cost, Total Tokens, Cache Hit %, and Turn Count.
- **Session Charts Grid 1**:
  - Left (2/3): Token Consumption vs Turn (`fig_prog`), stacked bars (Cached, Fresh, Output), `margin.l=75`, `automargin=True`, `title.standoff=14`.
  - Right (1/3): Session Token Distribution (`fig_pie`), donut with center total.
- **Session Charts Grid 2**:
  - Full Width: Financial Cost Trajectory & Cache Savings (`fig_cost`), dual line (Actual spend vs Without caching), filled green savings delta, `margin.l=75`, `margin.r=25`, `automargin=True`, paper-anchored `First Turn` and `Current Turn` labels.
- **Granular Telemetry Table**: Paginated 100 turns per page with model badge, token breakdown, and per-turn spend.

### 3. Token Telemetry (`nav == "⚡ Token Telemetry"`)
- **Turn Waterfall & Latency Gantt (`fig_waterfall`)**:
  - Stacked horizontal bars showing TTFT (Amber) and Output Streaming (Blue).
  - Reversed autorange (Turn 1 at top, Turn N at bottom).
  - `margin.l=80`, `automargin=True`, outside tick marks with `Roboto Mono`.
- **Turn KPI Cards**: Turn Latency, Prompt Context, Generation Footprint, Generation Speed.
- **Turn Inspector**: Expandable JSON / structured view of raw telemetry.

### 4. Global Architecture & Setup Modal (`show_github_setup_modal`)
- `@st.dialog` modal with 4 tabs:
  1. `⚡ 1-Click Self-Service (Recommended)`: Copy-paste curl installer with live install counter badge.
  2. `📋 Architecture & Data Flow`: Multi-agent telemetry pipeline diagram.
  3. `🔧 Manual Deployment`: Step-by-step BigQuery DDL and Cloud Run commands.
  4. `🗑️ Clean Uninstall`: 1-line uninstall command.

---

## 7. Automated Regression Prevention

To ensure no visual or structural regressions are introduced across the application, the following safeguards are enforced:

1. **Central Theme Engine**: All chart margins, typography, and colors are defined in [`dashboard/theme.py`](../dashboard/theme.py).
2. **Automated Regression Test Suite**: [`tests/test_styling_regression.py`](../tests/test_styling_regression.py) validates:
   - Margin minimums (`l >= 75` for continuous, `l >= 80` for Gantt).
   - Mandatory `automargin=True` on all numerical y-axes.
   - Title standoff `>= 14` on all titled axes.
   - Paper-anchored `First Turn` and `Current Turn` annotations on `fig_cost`.
   - CSS class definitions (`.telemetry-kpi-card`, `.gcp-table`, `.pill-green`, etc.).
3. **Pre-Commit / Pre-Deploy Gate**: The script [`scripts/verify_ui_standards.sh`](../scripts/verify_ui_standards.sh) must pass 100% before any git commit or Cloud Run deployment.
