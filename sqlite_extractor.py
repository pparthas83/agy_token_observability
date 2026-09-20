"""Extracts and decodes token telemetry from Antigravity SQLite conversation databases."""

import datetime
import glob
import json
import os
import re
import sqlite3
from typing import Any, Dict, List, Optional
from google.protobuf.internal import decoder

CONVERSATIONS_DIR = os.path.expanduser("~/.gemini/antigravity/conversations")
CONFIG_PROJECTS_DIR = os.path.expanduser("~/.gemini/config/projects")


def _decode_protobuf_varint_map(buf: bytes) -> Dict[int, Any]:
    """Decodes a protobuf buffer into a dictionary mapping field numbers to values."""
    pos = 0
    fields: Dict[int, Any] = {}
    while pos < len(buf):
        try:
            tag, pos = decoder._DecodeVarint32(buf, pos)
            field_num = tag >> 3
            wire_type = tag & 7
            if wire_type == 0:
                val, pos = decoder._DecodeVarint(buf, pos)
            elif wire_type == 2:
                length, pos = decoder._DecodeVarint32(buf, pos)
                val = buf[pos : pos + length]
                pos += length
            elif wire_type == 1:
                # 64-bit fixed
                val = buf[pos : pos + 8]
                pos += 8
            elif wire_type == 5:
                # 32-bit fixed
                val = buf[pos : pos + 4]
                pos += 4
            else:
                break
            fields[field_num] = val
        except Exception:
            break
    return fields


def get_project_mappings() -> Dict[str, Dict[str, str]]:
    """Loads ~/.gemini/config/projects/*.json to map project IDs to names and paths."""
    mappings: Dict[str, Dict[str, str]] = {}
    for filepath in glob.glob(os.path.join(CONFIG_PROJECTS_DIR, "*.json")):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                proj_id = data.get("id")
                proj_name = data.get("name")
                uri = ""
                resources = data.get("projectResources", {}).get("resources", [])
                if resources:
                    res = resources[0]
                    uri = res.get("folderUri") or res.get("gitFolder", {}).get("folderUri", "")
                if proj_id:
                    mappings[proj_id] = {
                        "name": proj_name or proj_id,
                        "uri": uri,
                    }
        except Exception:
            continue
    return mappings


def extract_model_name(conn: sqlite3.Connection) -> str:
    """Extracts the model name from gen_metadata in the conversation DB."""
    try:
        c = conn.cursor()
        c.execute("SELECT data FROM gen_metadata ORDER BY idx DESC LIMIT 5;")
        rows = c.fetchall()
        for (data,) in rows:
            if not data:
                continue
            # Look for model names (e.g. gemini-3.8-flash, claude-3.7-sonnet)
            matches = re.findall(
                rb"(gemini-[a-zA-Z0-9\.\-_]+|claude-[a-zA-Z0-9\.\-_]+)", data
            )
            if matches:
                # Pick the latest non-placeholder model
                for m in reversed(matches):
                    name = m.decode("utf-8", errors="ignore")
                    if "placeholder" not in name.lower():
                        return name
    except Exception:
        pass
    return "gemini-3.8-flash"


def get_conversation_index() -> Dict[str, Dict[str, str]]:
    """Decodes ~/.gemini/antigravity/agyhub_summaries_proto.pb to map conversation IDs to workspace URIs and project IDs."""
    mapping: Dict[str, Dict[str, str]] = {}
    pb_path = os.path.expanduser("~/.gemini/antigravity/agyhub_summaries_proto.pb")
    if not os.path.exists(pb_path):
        return mapping

    try:
        with open(pb_path, "rb") as f:
            buf = f.read()

        pos = 0
        items = []
        while pos < len(buf):
            tag, pos = decoder._DecodeVarint32(buf, pos)
            fn = tag >> 3
            wt = tag & 7
            if wt == 2:
                l, pos = decoder._DecodeVarint32(buf, pos)
                val = buf[pos : pos + l]
                pos += l
                if fn == 1:
                    items.append(val)
            elif wt == 0:
                _, pos = decoder._DecodeVarint(buf, pos)
            else:
                break

        for it in items:
            p = 0
            cid = None
            while p < len(it):
                t, p = decoder._DecodeVarint32(it, p)
                sfn = t >> 3
                swt = t & 7
                if swt == 2:
                    sl, p = decoder._DecodeVarint32(it, p)
                    val = it[p : p + sl]
                    p += sl
                    if sfn == 1:
                        cid = val.decode("utf-8", errors="ignore")
                    elif sfn == 2:
                        uri_m = re.search(rb"file://[a-zA-Z0-9_\-\./]+", val)
                        uri = uri_m.group(0).decode("utf-8", errors="ignore") if uri_m else ""
                        proj_m = re.findall(
                            rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", val
                        )
                        projs = [pm.decode() for pm in proj_m if pm.decode() != cid]
                        proj_id = projs[-1] if projs else ""
                        if cid:
                            mapping[cid] = {"uri": uri, "project_id": proj_id}
                elif swt == 0:
                    _, p = decoder._DecodeVarint(it, p)
                else:
                    break
    except Exception:
        pass
    return mapping


def extract_conversation_steps(
    conversation_id: str,
    last_synced_step: int = -1,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Reads a conversation DB in read-only mode and returns un-synced token events."""
    if db_path is None:
        db_path = os.path.join(CONVERSATIONS_DIR, f"{conversation_id}.db")

    if not os.path.exists(db_path):
        return []

    # Open SQLite in read-only mode with URI=True to avoid locking the database
    uri_path = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri_path, uri=True)
    c = conn.cursor()

    # 1. Resolve Project and Workspace metadata
    project_mappings = get_project_mappings()
    conv_index = get_conversation_index()
    conv_meta = conv_index.get(conversation_id, {})

    project_id = conv_meta.get("project_id", "")
    workspace_uri = conv_meta.get("uri", "")

    # Fallback to scanning trajectory_meta or steps if not found in index
    if not project_id:
        try:
            c.execute("SELECT trajectory_id FROM trajectory_meta LIMIT 1;")
            row = c.fetchone()
            if row and row[0] and row[0] in project_mappings:
                project_id = str(row[0])
        except Exception:
            pass

    # Map project ID to friendly project name and workspace
    proj_info = project_mappings.get(project_id, {})
    project_name = proj_info.get("name", "")
    if not workspace_uri:
        workspace_uri = proj_info.get("uri", "")

    workspace_name = (
        os.path.basename(workspace_uri.replace("file://", "").rstrip("/"))
        if workspace_uri
        else "Unknown Workspace"
    )
    if not project_name:
        project_name = workspace_name or "Unknown Project"

    # 3. Resolve Model Name
    model_name = extract_model_name(conn)

    # 4. Fetch steps with idx > last_synced_step
    c.execute(
        "SELECT idx, step_type, status, metadata FROM steps WHERE idx > ? AND metadata IS NOT NULL ORDER BY idx ASC;",
        (last_synced_step,),
    )
    rows = c.fetchall()

    extracted_records: List[Dict[str, Any]] = []

    for idx, step_type, status, meta_bytes in rows:
        if not meta_bytes:
            continue

        meta_fields = _decode_protobuf_varint_map(meta_bytes)

        # Field 1: Timestamp (google.protobuf.Timestamp)
        step_dt = datetime.datetime.now(datetime.timezone.utc)
        t1_sec: Optional[float] = None
        if 1 in meta_fields and isinstance(meta_fields[1], bytes):
            ts_sub = _decode_protobuf_varint_map(meta_fields[1])
            sec = ts_sub.get(1, 0)
            nanos = ts_sub.get(2, 0)
            if sec > 0:
                t1_sec = sec + (nanos / 1_000_000_000.0)
                step_dt = datetime.datetime.fromtimestamp(t1_sec, tz=datetime.timezone.utc)

        # Field 6: Cloud Dispatch Timestamp
        t6_sec: Optional[float] = None
        if 6 in meta_fields and isinstance(meta_fields[6], bytes):
            ts_sub = _decode_protobuf_varint_map(meta_fields[6])
            sec = ts_sub.get(1, 0)
            nanos = ts_sub.get(2, 0)
            if sec > 0:
                t6_sec = sec + (nanos / 1_000_000_000.0)

        # Field 7/8/32: Generation Completed Timestamp
        t7_sec: Optional[float] = None
        for f_cand in (7, 8, 32):
            if f_cand in meta_fields and isinstance(meta_fields[f_cand], bytes):
                ts_sub = _decode_protobuf_varint_map(meta_fields[f_cand])
                sec = ts_sub.get(1, 0)
                nanos = ts_sub.get(2, 0)
                if sec > 0:
                    t7_sec = sec + (nanos / 1_000_000_000.0)
                    break

        # Field 11: Latency in ms (Time to First Token)
        latency_ms = meta_fields.get(11)
        ttft_latency_ms = int(latency_ms) if latency_ms is not None else None

        # Timing calculations
        client_prep_ms: Optional[int] = None
        if t6_sec is not None and t1_sec is not None and t6_sec >= t1_sec:
            client_prep_ms = int((t6_sec - t1_sec) * 1000)

        generation_duration_ms: Optional[int] = None
        if t7_sec is not None and t6_sec is not None and t7_sec >= t6_sec:
            generation_duration_ms = int((t7_sec - t6_sec) * 1000)

        # Field 9: Usage Metadata
        if 9 not in meta_fields or not isinstance(meta_fields[9], bytes):
            continue

        usage = _decode_protobuf_varint_map(meta_fields[9])
        prompt_tokens = int(usage.get(2, 0))
        output_tokens = int(usage.get(3, 0))
        cached_tokens = int(usage.get(5, 0)) if 5 in usage else 0
        thinking_tokens = int(usage.get(9, 0)) if 9 in usage else None
        content_tokens = int(usage.get(10, 0)) if 10 in usage else None

        if prompt_tokens == 0 and output_tokens == 0:
            continue

        total_tokens = prompt_tokens + output_tokens

        tokens_per_second: Optional[float] = None
        if generation_duration_ms and generation_duration_ms > 0:
            tokens_per_second = round(output_tokens / (generation_duration_ms / 1000.0), 1)

        record = {
            "conversation_id": conversation_id,
            "step_index": int(idx),
            "timestamp": step_dt,
            "antigravity_project_id": project_id,
            "antigravity_project_name": project_name,
            "workspace_name": workspace_name,
            "workspace_uri": workspace_uri,
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "thinking_tokens": thinking_tokens,
            "content_tokens": content_tokens,
            "total_tokens": total_tokens,
            "latency_ms": ttft_latency_ms,
            "ttft_latency_ms": ttft_latency_ms,
            "client_prep_ms": client_prep_ms,
            "generation_duration_ms": generation_duration_ms,
            "tokens_per_second": tokens_per_second,
            "step_type": "PLANNER_RESPONSE" if step_type == 15 else str(step_type),
            "tool_name": None,
            "surface": "app",
        }
        extracted_records.append(record)

    conn.close()
    return extracted_records
