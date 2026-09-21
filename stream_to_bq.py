"""Production BigQuery Token Streaming Engine for Google Antigravity.

Streams token usage, latency, and estimated cost telemetry to BigQuery
using Application Default Credentials (ADC) and atomic state cursors.
"""

import argparse
import datetime
import glob
import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import google.auth
from google.cloud import bigquery

import pricing
import sqlite_extractor

# Configuration Defaults
DEFAULT_PROJECT_ID = os.environ.get("GCP_PROJECT", os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
DEFAULT_DATASET_ID = os.environ.get("BQ_DATASET", "token_analytics")
DEFAULT_TABLE_ID = os.environ.get("BQ_TABLE", "antigravity_token_events")

STATE_FILE = os.path.expanduser("~/.gemini/antigravity/.token_sync_state.json")
LOG_FILE = os.path.expanduser("~/.gemini/antigravity/log/token_streamer.log")

# Setup logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def get_authenticated_user_email(credentials: Any) -> str:
    """Resolves the active user email securely via credentials or gcloud config."""
    # 1. Check credentials service_account_email
    email = getattr(credentials, "service_account_email", None)
    if email and email != "default":
        return email

    # 2. Check gcloud config account
    try:
        res = subprocess.run(
            ["gcloud", "config", "get-value", "account"],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        acc = res.stdout.strip()
        if acc and "@" in acc:
            return acc
    except Exception:
        pass

    # 3. Fallback to OS user
    return f"{os.getenv('USER', 'unknown')}@workstation.local"


def load_sync_state() -> Dict[str, int]:
    """Loads the local conversation sync state cursor."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.warning("Failed to load sync state file, starting fresh: %s", e)
        return {}


def save_sync_state(state: Dict[str, int]) -> None:
    """Atomically saves the sync state using tempfile replacement."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    temp_dir = os.path.dirname(STATE_FILE)
    try:
        with tempfile.NamedTemporaryFile("w", dir=temp_dir, delete=False, encoding="utf-8") as tf:
            json.dump(state, tf, indent=2)
            temp_path = tf.name
        os.replace(temp_path, STATE_FILE)
    except Exception as e:
        logging.error("Failed to save sync state atomically: %s", e)


def build_bigquery_rows(
    raw_records: List[Dict[str, Any]], user_email: str
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Converts raw extracted records into validated BigQuery rows and row_ids."""
    rows: List[Dict[str, Any]] = []
    row_ids: List[str] = []

    for r in raw_records:
        event_id = f"{r['conversation_id']}_{r['step_index']}"
        prompt_tokens = r.get("prompt_tokens", 0)
        output_tokens = r.get("output_tokens", 0)
        total_tokens = r.get("total_tokens", prompt_tokens + output_tokens)
        model_name = r.get("model", "unknown")

        cost = pricing.calculate_cost(prompt_tokens, output_tokens, model_name)

        ts = r["timestamp"]
        ts_str = ts.isoformat() if isinstance(ts, datetime.datetime) else str(ts)

        row = {
            "event_id": event_id,
            "conversation_id": r["conversation_id"],
            "step_index": r["step_index"],
            "timestamp": ts_str,
            "user_email": user_email,
            "antigravity_project_id": r.get("antigravity_project_id") or None,
            "antigravity_project_name": r.get("antigravity_project_name") or None,
            "workspace_name": r.get("workspace_name") or None,
            "workspace_uri": r.get("workspace_uri") or None,
            "surface": r.get("surface", "app"),
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": r.get("cached_tokens", 0),
            "thinking_tokens": r.get("thinking_tokens"),
            "content_tokens": r.get("content_tokens"),
            "total_tokens": total_tokens,
            "latency_ms": r.get("latency_ms"),
            "ttft_latency_ms": r.get("ttft_latency_ms"),
            "client_prep_ms": r.get("client_prep_ms"),
            "generation_duration_ms": r.get("generation_duration_ms"),
            "tokens_per_second": r.get("tokens_per_second"),
            "estimated_cost_usd": str(cost),
            "step_type": r.get("step_type", "PLANNER_RESPONSE"),
            "tool_name": r.get("tool_name"),
            "context_metadata": r.get("context_metadata"),
        }
        rows.append(row)
        row_ids.append(event_id)

    return rows, row_ids


def sync_conversation(
    conversation_id: str,
    client: Optional[bigquery.Client],
    table_ref: Optional[str],
    state: Dict[str, int],
    user_email: str,
    dry_run: bool = False,
) -> int:
    """Extracts and streams un-synced events for a single conversation."""
    last_synced_step = state.get(conversation_id, -1)
    raw_records = sqlite_extractor.extract_conversation_steps(
        conversation_id, last_synced_step=last_synced_step
    )

    if not raw_records:
        return 0

    rows, row_ids = build_bigquery_rows(raw_records, user_email)

    if dry_run or client is None or table_ref is None:
        print(f"[DRY-RUN] Extracted {len(rows)} new rows for conversation {conversation_id}.")
        if rows:
            print(f"Sample row: {json.dumps(rows[0], indent=2)}")
        max_step = max(r["step_index"] for r in raw_records)
        state[conversation_id] = max_step
        return len(rows)

    # Insert rows into BigQuery in chunks of 500 for streaming API stability
    batch_size = 500
    all_errors = []
    for i in range(0, len(rows), batch_size):
        chunk_rows = rows[i : i + batch_size]
        chunk_ids = row_ids[i : i + batch_size]
        errors = client.insert_rows_json(table_ref, chunk_rows, row_ids=chunk_ids)
        if errors:
            all_errors.extend(errors)

    if all_errors:
        logging.error("BigQuery insert errors for %s: %s", conversation_id, all_errors)
        print(f"Error streaming rows to BigQuery: {all_errors}", file=sys.stderr)
        return 0

    max_step = max(r["step_index"] for r in raw_records)
    state[conversation_id] = max_step
    logging.info(
        "Successfully streamed %d rows for conversation %s up to step %d",
        len(rows),
        conversation_id,
        max_step,
    )
    if not sys.stdin.isatty():
        # In hook mode, log to stderr
        print(f"Streamed {len(rows)} rows to BigQuery for conversation {conversation_id}.", file=sys.stderr)
    else:
        print(f"Streamed {len(rows)} rows to BigQuery for conversation {conversation_id}.")
    return len(rows)


def ensure_bigquery_schema(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str = DEFAULT_DATASET_ID,
    table_id: str = DEFAULT_TABLE_ID,
) -> bool:
    """Idempotently ensures the BigQuery dataset, partitioned & clustered table, and analytical views exist."""
    try:
        # 1. Dataset
        dataset_ref = f"{project_id}.{dataset_id}"
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        dataset.labels = {"datacloud": "antigravity"}
        client.create_dataset(dataset, exists_ok=True)
        logging.info("Ensured BigQuery dataset: %s", dataset_ref)

        # 2. Fact Table
        table_ref = f"{project_id}.{dataset_id}.{table_id}"
        schema = [
            bigquery.SchemaField("event_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("conversation_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("step_index", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("user_email", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("antigravity_project_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("antigravity_project_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("workspace_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("workspace_uri", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("surface", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("model", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("prompt_tokens", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("output_tokens", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("cached_tokens", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("thinking_tokens", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("content_tokens", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("total_tokens", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("latency_ms", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("ttft_latency_ms", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("client_prep_ms", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("generation_duration_ms", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("tokens_per_second", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("estimated_cost_usd", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("step_type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("tool_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("context_metadata", "STRING", mode="NULLABLE"),
        ]

        table = bigquery.Table(table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="timestamp",
        )
        table.clustering_fields = [
            "antigravity_project_name",
            "model",
            "user_email",
            "conversation_id",
        ]
        table.labels = {"datacloud": "antigravity"}
        client.create_table(table, exists_ok=True)
        logging.info("Ensured BigQuery table: %s (Partitioned by DAY, Clustered)", table_ref)

        # 3. Analytical Views
        view_rollup_sql = f"""
        CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.v_conversation_rollup` AS
        SELECT
          conversation_id,
          user_email,
          antigravity_project_name,
          workspace_name,
          MIN(timestamp) AS session_start,
          MAX(timestamp) AS session_end,
          COUNT(DISTINCT step_index) AS total_turns,
          ANY_VALUE(model) AS primary_model,
          SUM(prompt_tokens) AS total_prompt_tokens,
          SUM(output_tokens) AS total_output_tokens,
          SUM(COALESCE(thinking_tokens, 0)) AS total_thinking_tokens,
          SUM(total_tokens) AS grand_total_tokens,
          MAX(prompt_tokens) AS max_context_window_reached,
          ROUND(SUM(estimated_cost_usd), 4) AS session_cost_usd
        FROM `{table_ref}`
        GROUP BY conversation_id, user_email, antigravity_project_name, workspace_name
        """
        client.query(view_rollup_sql).result()

        view_spend_sql = f"""
        CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.v_daily_project_spend` AS
        SELECT
          DATE(timestamp) AS usage_date,
          antigravity_project_name,
          model,
          COUNT(DISTINCT conversation_id) AS active_conversations,
          COUNT(DISTINCT user_email) AS active_developers,
          SUM(prompt_tokens) AS daily_prompt_tokens,
          SUM(output_tokens) AS daily_output_tokens,
          SUM(COALESCE(thinking_tokens, 0)) AS daily_thinking_tokens,
          SUM(total_tokens) AS daily_total_tokens,
          ROUND(SUM(estimated_cost_usd), 4) AS daily_spend_usd
        FROM `{table_ref}`
        GROUP BY usage_date, antigravity_project_name, model
        """
        client.query(view_spend_sql).result()
        logging.info("Ensured BigQuery analytical views: v_conversation_rollup, v_daily_project_spend")
        return True
    except Exception as e:
        logging.error("Failed to ensure BigQuery schema for %s: %s", project_id, e)
        print(f"Warning: BigQuery auto-schema provisioning encountered an issue: {e}", file=sys.stderr)
        return False


def handle_hook_execution(client: Optional[bigquery.Client], table_ref: Optional[str], state: Dict[str, int], user_email: str) -> None:
    """Handles invocation from Antigravity's 'Stop' lifecycle hook."""
    conv_id = None
    # Antigravity passes camelCase JSON payload via STDIN
    if not sys.stdin.isatty():
        try:
            payload = json.load(sys.stdin)
            conv_id = payload.get("conversationId") or payload.get("conversation_id")
        except Exception:
            pass

    # If conv_id not in stdin, check the newest conversation database
    if not conv_id:
        db_files = glob.glob(os.path.expanduser("~/.gemini/antigravity/conversations/*.db"))
        if db_files:
            newest_db = max(db_files, key=os.path.getmtime)
            conv_id = os.path.basename(newest_db).replace(".db", "")

    if conv_id and client and table_ref:
        try:
            sync_conversation(conv_id, client, table_ref, state, user_email)
            save_sync_state(state)
        except Exception as e:
            logging.error("Telemetry streaming failed during hook execution: %s", e)
            print(f"Warning: Telemetry streaming failed: {e}", file=sys.stderr)

    # Lifecycle hooks expect a valid JSON response on stdout
    print(json.dumps({}))


def main() -> None:
    parser = argparse.ArgumentParser(description="Antigravity Token Observability Streamer")
    parser.add_argument("--project", default=None, help="GCP Project ID (defaults to ADC or GCP_PROJECT env)")
    parser.add_argument("--dataset", default=DEFAULT_DATASET_ID, help="BigQuery Dataset ID")
    parser.add_argument("--table", default=DEFAULT_TABLE_ID, help="BigQuery Table ID")
    parser.add_argument("--conversation", help="Specific conversation ID to sync")
    parser.add_argument("--backfill", action="store_true", help="Backfill all existing conversations")
    parser.add_argument("--hook", action="store_true", help="Run as Antigravity lifecycle hook")
    parser.add_argument("--dry-run", action="store_true", help="Extract without inserting into BigQuery")
    parser.add_argument("--init-schema", action="store_true", help="Provision dataset, partitioned table, and views in BigQuery")

    args = parser.parse_args()

    # Authenticate via ADC
    credentials, detected_project = google.auth.default()
    active_project = args.project or DEFAULT_PROJECT_ID or detected_project
    if not active_project:
        logging.error("No active GCP project detected. Specify --project or set GCP_PROJECT.")
        if not args.hook:
            print("Error: No GCP Project detected. Specify via --project or GCP_PROJECT environment variable.", file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    user_email = get_authenticated_user_email(credentials)

    client = None
    table_ref = None

    state = load_sync_state()

    if not args.dry_run:
        try:
            # Enforce resource attribution label
            client = bigquery.Client(
                project=active_project,
                credentials=credentials,
                default_query_job_config=bigquery.QueryJobConfig(
                    labels={"datacloud": "antigravity"}
                ),
            )
            table_ref = f"{active_project}.{args.dataset}.{args.table}"

            if args.init_schema:
                print(f"Provisioning BigQuery dataset, table, and views in '{active_project}'...")
                success = ensure_bigquery_schema(client, active_project, args.dataset, args.table)
                if success:
                    schema_cache_key = f"_schema_verified_{active_project}_{args.dataset}_{args.table}"
                    state[schema_cache_key] = True
                    save_sync_state(state)
                    print(f"✔ BigQuery schema successfully initialized: {table_ref}")
                    sys.exit(0)
                else:
                    print("✖ Failed to initialize BigQuery schema.", file=sys.stderr)
                    sys.exit(1)
            else:
                schema_cache_key = f"_schema_verified_{active_project}_{args.dataset}_{args.table}"
                if not state.get(schema_cache_key):
                    try:
                        client.get_table(table_ref)
                        state[schema_cache_key] = True
                        save_sync_state(state)
                    except Exception:
                        # Table does not exist in developer account, auto-provision it!
                        if ensure_bigquery_schema(client, active_project, args.dataset, args.table):
                            state[schema_cache_key] = True
                            save_sync_state(state)
        except Exception as e:
            logging.error("Failed to initialize BigQuery client: %s", e)
            print(f"Warning: Could not connect to BigQuery: {e}", file=sys.stderr)
            sys.exit(0)  # Exit safely to avoid breaking IDE

    try:
        if args.hook:
            handle_hook_execution(client, table_ref, state, user_email)
        elif args.conversation:
            sync_conversation(args.conversation, client, table_ref, state, user_email, dry_run=args.dry_run)
            if not args.dry_run:
                save_sync_state(state)
        elif args.backfill:
            db_files = glob.glob(os.path.expanduser("~/.gemini/antigravity/conversations/*.db"))
            total_synced = 0
            for db_path in db_files:
                cid = os.path.basename(db_path).replace(".db", "")
                total_synced += sync_conversation(cid, client, table_ref, state, user_email, dry_run=args.dry_run)
            if not args.dry_run:
                save_sync_state(state)
            print(f"Backfill complete! Total rows processed: {total_synced}")
        else:
            # Default to syncing the newest conversation
            db_files = glob.glob(os.path.expanduser("~/.gemini/antigravity/conversations/*.db"))
            if db_files:
                newest_db = max(db_files, key=os.path.getmtime)
                cid = os.path.basename(newest_db).replace(".db", "")
                sync_conversation(cid, client, table_ref, state, user_email, dry_run=args.dry_run)
                if not args.dry_run:
                    save_sync_state(state)
    except Exception as e:
        logging.error("Unexpected error during execution: %s", e)
        # Always exit with 0 if invoked as a hook so IDE never hangs
        if args.hook:
            sys.exit(0)
        else:
            raise


if __name__ == "__main__":
    main()
