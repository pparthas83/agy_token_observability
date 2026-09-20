"""Unit tests for sqlite_extractor.py protobuf decoding and event parsing."""

import sqlite3
import tempfile
import os
import pytest
from google.protobuf.internal import encoder
import sqlite_extractor


def _encode_varint_field(field_num: int, value: int) -> bytes:
    """Helper to encode a field_num -> varint pair."""
    tag = (field_num << 3) | 0
    buf = bytearray()
    encoder._EncodeVarint(buf.extend, tag)
    encoder._EncodeVarint(buf.extend, value)
    return bytes(buf)


def _encode_bytes_field(field_num: int, data: bytes) -> bytes:
    """Helper to encode a field_num -> length-delimited bytes pair."""
    tag = (field_num << 3) | 2
    buf = bytearray()
    encoder._EncodeVarint(buf.extend, tag)
    encoder._EncodeVarint(buf.extend, len(data))
    buf.extend(data)
    return bytes(buf)


def test_decode_protobuf_varint_map():
    # Construct a protobuf buffer with:
    # Field 1 = 123 (varint)
    # Field 2 = "hello" (bytes)
    # Field 5 = 9999 (varint)
    buf = bytearray()
    buf.extend(_encode_varint_field(1, 123))
    buf.extend(_encode_bytes_field(2, b"hello"))
    buf.extend(_encode_varint_field(5, 9999))

    decoded = sqlite_extractor._decode_protobuf_varint_map(bytes(buf))
    assert decoded[1] == 123
    assert decoded[2] == b"hello"
    assert decoded[5] == 9999


def test_extract_session_events_from_sqlite():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_conv.db")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Create schema
        cur.execute("CREATE TABLE gen_metadata (idx INTEGER, data BLOB);")
        cur.execute("CREATE TABLE steps (idx INTEGER, step_type INTEGER, status INTEGER, data BLOB, metadata BLOB);")

        # Insert model name in gen_metadata
        cur.execute("INSERT INTO gen_metadata VALUES (1, ?);", (b"selected_model: gemini-3.8-flash",))

        # Build usage metadata (field 9 in step metadata)
        # field 2: prompt_tokens = 2160
        # field 3: output_tokens = 672
        # field 5: cached_tokens = 95000
        # field 9: thinking_tokens = 45
        usage_buf = bytearray()
        usage_buf.extend(_encode_varint_field(2, 2160))
        usage_buf.extend(_encode_varint_field(3, 672))
        usage_buf.extend(_encode_varint_field(5, 95000))
        usage_buf.extend(_encode_varint_field(9, 45))

        # Build step metadata
        # field 9 = usage_buf
        # field 11 = latency_ms = 450
        meta_buf = bytearray()
        meta_buf.extend(_encode_bytes_field(9, bytes(usage_buf)))
        meta_buf.extend(_encode_varint_field(11, 450))

        # Insert step (idx, step_type, status, data, metadata)
        cur.execute(
            "INSERT INTO steps VALUES (1, 15, 1, ?, ?);",
            (b"", bytes(meta_buf))
        )
        conn.commit()
        conn.close()

        records = sqlite_extractor.extract_conversation_steps(
            conversation_id="test-conv-001",
            last_synced_step=-1,
            db_path=db_path,
        )

        assert len(records) == 1
        rec = records[0]
        assert rec["conversation_id"] == "test-conv-001"
        assert rec["step_index"] == 1
        assert rec["model"] == "gemini-3.8-flash"
        assert rec["prompt_tokens"] == 2160
        assert rec["output_tokens"] == 672
        assert rec["cached_tokens"] == 95000
        assert rec["thinking_tokens"] == 45
        assert rec["latency_ms"] == 450
        assert rec["step_type"] == "PLANNER_RESPONSE"
