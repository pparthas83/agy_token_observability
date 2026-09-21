# Antigravity Token Observability & FinOps Telemetry Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Author](https://img.shields.io/badge/Author-Pradeep%20Parthasarathy-orange.svg)](mailto:pradeepsarathy@google.com)
[![Engine](https://img.shields.io/badge/Built%20With-Antigravity%20%26%20Gemini-4285F4.svg)](#8-author--attribution)
[![Platform](https://img.shields.io/badge/Platform-Google%20Cloud-34A853.svg)](https://cloud.google.com)

Production-grade token observability, latency tracking, and LLM cost estimation pipeline for Google Antigravity 2.0 and Antigravity IDE, streaming real-time telemetry to Google BigQuery and an enterprise Cloud Run dashboard.

---

## ⚡ 1-Click Automated Setup (Recommended)

Run the self-service installer in your workstation terminal to bootstrap an isolated virtual environment, register the Antigravity `Stop` lifecycle hook, and auto-provision the BigQuery dataset, partitioned & clustered table, and analytical views in your Google Cloud account:

```bash
curl -sSL https://raw.githubusercontent.com/pparthas83/agy_token_observability/main/install.sh | bash
```

### Custom Configuration Options
You can pass custom parameters directly to the installer:
```bash
# Specify target GCP Project or custom BigQuery dataset
curl -sSL https://raw.githubusercontent.com/pparthas83/agy_token_observability/main/install.sh | bash -s -- --project=MY_GCP_PROJECT --dataset=token_analytics

# Non-interactive installation (for automated scripts or devcontainers)
curl -sSL https://raw.githubusercontent.com/pparthas83/agy_token_observability/main/install.sh | bash -s -- --project=MY_GCP_PROJECT --non-interactive
```

### Clean 1-Line Uninstall
To completely remove the telemetry client and unregister lifecycle hooks at any time:
```bash
~/.antigravity-observability/uninstall.sh
```

---

## 1. Architectural Highlights

- **Security & Privacy First**:
  - **Zero Plaintext Secrets**: Uses Google Application Default Credentials (`google.auth.default()`). No service account keys or API tokens are stored on developer workstations.
  - **Data Minimization (GDPR & Compliance Safe)**: Extracts **strictly** numeric token counts (`prompt_tokens`, `output_tokens`, `cached_tokens`, `thinking_tokens`), model strings, latencies, timestamps, and workspace metadata. Prompts, code files, and model responses are **never** captured or transmitted.
  - **Non-Interference Guarantee**: Operates asynchronously at turn completion (`Stop` hook). SQLite databases are read strictly in read-only mode (`?mode=ro`). If BigQuery or the network is unavailable, execution fails silently and logs locally to `~/.gemini/antigravity/log/token_streamer.log` without degrading IDE performance.
- **Zero-Latency Non-Blocking Execution**:
  - Standard output strictly outputs `{}` with exit code 0 to adhere to Antigravity's IDE hook contract, ensuring zero perceived developer lag.
  - **Schema Verification Caching**: Caches BigQuery schema validation state in `~/.gemini/antigravity/.token_sync_state.json` (`_schema_verified_*`), eliminating redundant GCP API roundtrips on successive agent turns.
- **Idempotency & Deduplication**:
  - Every event has a deterministic `event_id` (`{conversation_id}_{step_index}`).
  - BigQuery streaming API inserts enforce server-side `row_ids` deduplication.
  - Atomic cursor tracking prevents duplicate writes during crashes or restarts.
- **Automated Metadata Enrichment**:
  - Decodes Antigravity's internal protobuf index (`agyhub_summaries_proto.pb`) to map conversation UUIDs to human-friendly project names and git repositories automatically.
- **Resource Attribution**:
  - All Google Cloud operations are annotated with FinOps attribution (`datacloud: antigravity`).

---

## 2. Quick Start on Local Workstation

### Prerequisites
- Python 3.10+ (or [`uv`](https://github.com/astral-sh/uv))
- Google Cloud SDK (`gcloud` CLI) authenticated via:
  ```bash
  gcloud auth application-default login
  ```
- Access to your target GCP Project with BigQuery Data Editor permissions on dataset `token_analytics`.

### Installation
```bash
# 1. Create isolated virtual environment
uv venv .venv

# 2. Install dependencies
uv pip install --python .venv/bin/python -r requirements.txt

# 3. Make hook script executable
chmod +x run_hook.sh
```

### Manual CLI Usage
```bash
# Auto-provision BigQuery dataset, table, and analytical views
.venv/bin/python3 stream_to_bq.py --init-schema

# Dry-run test of active conversation (auto-detects project from gcloud ADC or GCP_PROJECT env)
.venv/bin/python3 stream_to_bq.py --dry-run

# Backfill all historical conversation databases on workstation
.venv/bin/python3 stream_to_bq.py --backfill

# Sync a specific conversation
.venv/bin/python3 stream_to_bq.py --conversation <CONVERSATION_UUID>
```

---

## 3. Automated Lifecycle Hook Setup

To automatically stream token counts at the end of every agent turn:

### Global Workstation Configuration
Add or update `~/.gemini/config/hooks.json`:
```json
{
  "token-observability": {
    "enabled": true,
    "Stop": [
      {
        "type": "command",
        "command": "/path/to/token_observability/run_hook.sh",
        "timeout": 30
      }
    ]
  }
}
```

---

## 4. Enterprise Rollout to Other Developers

To deploy this across your engineering organization:

### Method A: Repository-Level Customization (Zero Setup for Developers)
Copy `.agents/hooks.json` and this repository into your team's code repository.
When any developer opens the repository in Antigravity IDE, the hook triggers automatically without any manual installation.

### Method B: Native Antigravity Plugin
Clone or distribute this folder as an Antigravity Plugin located at `~/.gemini/config/plugins/token-observability`:
```bash
git clone https://github.com/pparthas83/agy_token_observability.git ~/.gemini/config/plugins/token-observability
```

### Method C: Central Cloud Workstations / Devcontainers
In your base Dockerfile or workstation provisioning script:
```dockerfile
RUN git clone https://github.com/pparthas83/agy_token_observability.git /etc/antigravity/plugins/token-observability
```

---

## 5. Live Cloud Run FinOps Dashboard

A containerized, self-updating dashboard deployed to Google Cloud Run:
- **Live Endpoint**: [https://antigravity-token-dashboard-832497031659.us-central1.run.app](https://antigravity-token-dashboard-832497031659.us-central1.run.app)
- **Deployment Command**:
  ```bash
  CLOUDSDK_METRICS_ENVIRONMENT=datacloud.antigravity gcloud run deploy antigravity-token-dashboard \
      --source=dashboard \
      --region=us-central1 \
      --allow-unauthenticated \
      --labels=datacloud=antigravity,app=token-dashboard
  ```

### Dashboard Views
1. **Executive Overview**: Spend KPIs, 30-day daily spend trends, top model distribution, and cumulative cache savings.
2. **Tokenomics Deep Dive**: Model-level token consumption breakdown (Prompt, Output, Cached, Thinking), token velocity, and context efficiency.
3. **Token Telemetry**:
   - Turn-by-turn Gantt latency waterfall.
   - **Token Consumption vs. Turn**: Area chart with unclipped `Tokens Consumed` metrics.
   - **Financial Cost Trajectory & Cache Savings**: Continuous trajectory showing Gross vs. Net USD spend with **paper-anchored** `First Turn (#N)` and `Current Turn (#N)` endpoint labels.
   - Expandable turn inspector with raw JSON metadata and status badges.
4. **Interactive Setup Modal**: In-app 1-click self-service commands, architecture diagrams, and uninstall guidance.

---

## 6. BigQuery Telemetry Assets

- **Project**: Target GCP Project (configured via `GCP_PROJECT` or ADC)
- **Dataset**: `token_analytics` (Region: `US`)
- **Fact Table**: `antigravity_token_events`
  - Partitioned by: `DATE(timestamp)`
  - Clustered by: `antigravity_project_name, model, user_email, conversation_id`
- **Analytical Views**:
  - `v_conversation_rollup`: Conversation session duration, token volume, max context window bloat, and session cost.
  - `v_daily_project_spend`: Daily aggregates by project and model for Looker Studio executive reporting.

---

## 7. Design System & UI Anti-Regression Framework

The dashboard is built upon an enterprise **Google Cloud Console Design System** to deliver high data density, zero visual clipping, and responsive aesthetics.

- **Design System Documentation**: See [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) for full layout rules, Google color hex tokens, typography hierarchy, card specs, and Plotly chart geometry.
- **Theme Engine**: Centralized in [`dashboard/theme.py`](dashboard/theme.py) for single-source-of-truth styling across all charts and UI components.
- **Anti-Regression Verification**:
  To ensure that no visual regressions (e.g. truncated axis labels, missing automargins, unpadded containers) are introduced during development, run:
  ```bash
  ./scripts/verify_ui_standards.sh
  ```
  This script executes Python compilation checks, the dedicated 10-point UI styling regression suite ([`tests/test_styling_regression.py`](tests/test_styling_regression.py)), and the complete telemetry test suite before commit or deployment.

---

## 8. Author & Attribution

| Role | Contributor / Tool | Contact |
| :--- | :--- | :--- |
| **Concept & Ideation** | **Pradeep Parthasarathy** | [`pradeepsarathy@google.com`](mailto:pradeepsarathy@google.com) |
| **Autonomous Build** | **Google Antigravity & Gemini** | [Antigravity Documentation](https://antigravity.google) |

### Support & Feedback
If you are deploying this telemetry engine in your team or finding it valuable for your Antigravity FinOps observability:
- **⭐ Star this repository** to bookmark and track updates.
- Reach out to **Pradeep Parthasarathy (`pradeepsarathy@google.com`)** for ideas, feedback, or custom metrics collaborations!

---

## 9. License & Citation

- **License**: Distributed under the [Apache 2.0 License](LICENSE). Copyright © 2026 Pradeep Parthasarathy.
- **Citation**: If you reference or build upon this work, please see the GitHub citation widget or reference [`CITATION.cff`](CITATION.cff).
