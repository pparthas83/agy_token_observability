"""
Context Extractor for Antigravity Token Observability.
Extracts the structural and directional context map for any conversation turn
from local transcript logs and trajectory events, with deterministic fallback
for Cloud Run deployments where local disk logs are absent.
"""

import json
import os
import re
from typing import Any, Dict, List, Optional

BRAIN_BASE_DIR = os.path.expanduser("~/.gemini/antigravity/brain")

STANDARD_NATIVE_TOOLS = [
    "run_command", "view_file", "replace_file_content", "write_to_file",
    "grep_search", "find_by_name", "list_dir", "ask_question",
    "generate_image", "read_url_content", "schedule", "manage_task",
    "invoke_subagent", "define_subagent"
]

STANDARD_MCP_SERVERS = ["cloudrun", "gmp-code-assist", "sequential-thinking"]
STANDARD_SKILLS_COUNT = 42


def get_static_scope() -> Dict[str, Any]:
    """Returns the static capability footprint of the Antigravity session."""
    return {
        "native_tools_count": len(STANDARD_NATIVE_TOOLS),
        "native_tools_sample": ["run_command", "view_file", "replace_file_content", "grep_search", "write_to_file"],
        "mcp_servers": STANDARD_MCP_SERVERS,
        "skills_count": STANDARD_SKILLS_COUNT,
        "rules_count": 0,
        "persona": "Antigravity Autonomous Pair Programmer",
        "os": "Linux x86_64",
    }


def generate_fallback_context(
    step_index: int,
    prompt_tokens: int = 0,
    cached_tokens: int = 0,
    tool_name: Optional[str] = None,
    user_prompt_preview: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generates a deterministic structural context map when local raw logs
    are not available (e.g. on Cloud Run).
    """
    cached_ratio = (cached_tokens / prompt_tokens) if prompt_tokens > 0 else 0.0
    checkpoint_active = cached_ratio > 0.5 or prompt_tokens > 60000

    recent_tools = [tool_name] if tool_name else []

    return {
        "step_index": step_index,
        "user_request_preview": user_prompt_preview or "User interaction / instruction in scope",
        "timestamp": "",
        "has_media": False,
        "media_files": [],
        "checkpoint_active": checkpoint_active,
        "checkpoint_step_index": 0 if checkpoint_active else None,
        "working_injections": {
            "command_runs": 1 if tool_name == "run_command" else 0,
            "file_reads": 1 if tool_name == "view_file" else 0,
            "file_edits": 1 if tool_name in ("replace_file_content", "write_to_file") else 0,
            "web_searches": 1 if tool_name == "search_web" else 0,
            "recent_commands": ["Terminal Command"] if tool_name == "run_command" else [],
            "recent_files": ["Source File"] if tool_name in ("view_file", "replace_file_content") else [],
            "intermediate_tools": recent_tools,
        },
        "static_scope": get_static_scope(),
    }


def extract_turn_context_metadata(
    conversation_id: str,
    step_index: int,
    prompt_tokens: int = 0,
    cached_tokens: int = 0,
    brain_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extracts structural context metadata for a given turn by reading
    the local transcript logs in the brain directory. Falls back to deterministic
    structural generation if log files are not found.
    """
    if brain_dir is None:
        brain_dir = os.path.join(BRAIN_BASE_DIR, conversation_id)

    log_path = os.path.join(brain_dir, ".system_generated", "logs", "transcript.jsonl")
    if not os.path.exists(log_path):
        log_path = os.path.join(brain_dir, ".system_generated", "logs", "transcript_full.jsonl")

    if not os.path.exists(log_path):
        return generate_fallback_context(step_index, prompt_tokens, cached_tokens)

    try:
        steps_by_idx: Dict[int, Dict[str, Any]] = {}
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    idx = data.get("step_index")
                    if idx is not None and idx <= step_index:
                        steps_by_idx[idx] = data
                except Exception:
                    continue

        if step_index not in steps_by_idx:
            return generate_fallback_context(step_index, prompt_tokens, cached_tokens)

        user_prompt = ""
        user_ts = ""
        checkpoint_active = False
        checkpoint_idx = None

        for idx in range(step_index, -1, -1):
            s = steps_by_idx.get(idx)
            if not s:
                continue
            if s.get("type") == "CHECKPOINT":
                checkpoint_active = True
                checkpoint_idx = idx
                break

        for idx in range(step_index, max(-1, step_index - 30), -1):
            s = steps_by_idx.get(idx)
            if not s:
                continue
            if s.get("type") == "USER_INPUT":
                content = str(s.get("content", ""))
                m = re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>", content, re.DOTALL)
                if m:
                    user_prompt = m.group(1).strip()
                else:
                    user_prompt = content.strip()
                user_ts = str(s.get("created_at", ""))
                break

        command_runs = 0
        file_reads = 0
        file_edits = 0
        web_searches = 0
        recent_commands: List[str] = []
        recent_files: List[str] = []
        intermediate_tools: List[str] = []

        for idx in range(step_index - 1, max(-1, step_index - 20), -1):
            s = steps_by_idx.get(idx)
            if not s:
                continue
            stype = s.get("type")
            if stype == "PLANNER_RESPONSE" and idx != step_index:
                for tc in s.get("tool_calls", []):
                    tname = tc.get("name", "")
                    targs = tc.get("args", {})
                    if tname:
                        intermediate_tools.append(tname)
                    if tname == "run_command":
                        command_runs += 1
                        cmd = targs.get("CommandLine", "")
                        if cmd:
                            recent_commands.append(cmd[:60])
                    elif tname == "view_file":
                        file_reads += 1
                        fpath = os.path.basename(targs.get("AbsolutePath", ""))
                        if fpath:
                            recent_files.append(fpath)
                    elif tname in ("replace_file_content", "write_to_file"):
                        file_edits += 1
                        fpath = os.path.basename(targs.get("TargetFile", ""))
                        if fpath:
                            recent_files.append(fpath)
                    elif tname == "search_web":
                        web_searches += 1
                break

        has_media = False
        media_files: List[str] = []
        media_dir = os.path.join(brain_dir, ".user_uploaded")
        if os.path.exists(media_dir):
            for mf in os.listdir(media_dir):
                if mf.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    media_files.append(mf)
                    has_media = True

        return {
            "step_index": step_index,
            "user_request_preview": (user_prompt[:250] + "...") if len(user_prompt) > 250 else user_prompt,
            "timestamp": user_ts,
            "has_media": has_media,
            "media_files": media_files[:5],
            "checkpoint_active": checkpoint_active,
            "checkpoint_step_index": checkpoint_idx,
            "working_injections": {
                "command_runs": command_runs,
                "file_reads": file_reads,
                "file_edits": file_edits,
                "web_searches": web_searches,
                "recent_commands": list(dict.fromkeys(recent_commands))[:3],
                "recent_files": list(dict.fromkeys(recent_files))[:3],
                "intermediate_tools": list(dict.fromkeys(intermediate_tools))[:5],
            },
            "static_scope": get_static_scope(),
        }
    except Exception:
        return generate_fallback_context(step_index, prompt_tokens, cached_tokens)
