# Antigravity Token Observability & FinOps Telemetry Engine

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Author](https://img.shields.io/badge/Author-Pradeep%20Parthasarathy-orange.svg)](mailto:pradeepsarathy@google.com)
[![Engine](https://img.shields.io/badge/Built%20With-Antigravity%20%26%20Gemini-4285F4.svg)](#7-author--attribution)
[![Platform](https://img.shields.io/badge/Platform-Google%20Cloud-34A853.svg)](https://cloud.google.com)

Production-grade token observability, latency tracking, and LLM cost estimation pipeline for Google Antigravity 2.0 and Antigravity IDE, streaming real-time telemetry to Google BigQuery and Looker Studio.

---

## 1. Architectural Highlights

- **Security & Privacy First**:
  - **Zero Plaintext Secrets**: Uses Google Application Default Credentials (`google.auth.default()`). No service account keys or API tokens are stored on workstations.
  - **Data Minimization (GDPR & Compliance Safe)**: Extracts **strictly** numeric token counts (`prompt_tokens`, `output_tokens`, `thinking_tokens`, `content_tokens`), model strings, latencies, timestamps, and workspace names. Prompts, user queries, code files, and model responses are **never** captured or transmitted.
  - **Non-Interference Guarantee**: Operates completely asynchronously during agent completion (`Stop` lifecycle hook). SQLite databases are accessed strictly in read-only mode (`?mode=ro`), preventing file locks against Antigravity runtime. If BigQuery is offline, execution fails silently and logs locally to `~/.gemini/antigravity/log/token_streamer.log` without degrading IDE performance.
- **Idempotency & Deduplication**:
  - Every event has a deterministic `event_id` (`{conversation_id}_{step_index}`).
  - BigQuery streaming API inserts use server-side `row_ids` deduplication.
  - Atomic cursor tracking (`~/.gemini/antigravity/.token_sync_state.json`) prevents duplicate writes during crashes.
- **Automated Metadata Enrichment**:
  - Decodes Antigravity's internal protobuf index (`agyhub_summaries_proto.pb`) to map conversation UUIDs to human-friendly project names and git repositories automatically.

---

## 2. Quick Start on Local Workstation

### Prerequisites
- Python 3.10+ (or `uv`)
- `gcloud auth application-default login`
- Access to your GCP Project with BigQuery Data Editor permissions on dataset `token_analytics`.

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

A containerized, self-updating Streamlit dashboard can be deployed to Google Cloud Run:
- **Deployment Command**:
  ```bash
  gcloud run deploy antigravity-token-dashboard \
      --source=dashboard \
      --region=us-central1 \
      --allow-unauthenticated \
      --labels=datacloud=antigravity,app=token-dashboard
  ```
- **Service Name**: `antigravity-token-dashboard`
- **Region**: `us-central1`
- **Features**:
  - Real-time spend counters & token metrics across all developer workstations.
  - Interactive charts for daily spend, token trajectory, and project attribution.
  - Conversation context-window bloat analysis.
  - Real-time event feed querying BigQuery dataset `token_analytics`.

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

For full schema definitions and ER diagrams, see [DATA_MODEL.md](DATA_MODEL.md).

---

## 7. Author & Attribution

| Role | Contributor / Tool | Contact |
| :--- | :--- | :--- |
| **Concept & Ideation** | **Pradeep Parthasarathy** | [`pradeepsarathy@google.com`](mailto:pradeepsarathy@google.com) |
| **Autonomous Build** | **Google Antigravity & Gemini** | [Antigravity Documentation](https://antigravity.google) |

### Support & Feedback
If you are deploying this telemetry engine in your team or finding it valuable for your Antigravity FinOps observability:
- **⭐ Star this repository** to bookmark and track updates.
- Reach out to **Pradeep Parthasarathy (`pradeepsarathy@google.com`)** for ideas, feedback, or custom metrics collaborations!

---

## 8. License & Citation

- **License**: Distributed under the [Apache 2.0 License](LICENSE). Copyright © 2026 Pradeep Parthasarathy.
- **Citation**: If you reference or build upon this work, please see the GitHub citation widget or reference [`CITATION.cff`](CITATION.cff).
