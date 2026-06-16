"""I/O tests for non-tool audit streams that still need hash chaining."""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_mcp.audit.chain import verify_chain_lines
from silentwitness_mcp.audit.chained_jsonl import append_chained_jsonl


def test_append_chained_jsonl_links_rows(tmp_path: Path) -> None:
    log = tmp_path / "audit" / "agent.jsonl"

    first = append_chained_jsonl(log, {"type": "start", "step": 1})
    second = append_chained_jsonl(log, {"type": "finish", "step": 2})

    assert first["prev_record_hash"] is None
    assert second["prev_record_hash"] == first["record_hash"]
    result = verify_chain_lines(log.read_text(encoding="utf-8").splitlines())
    assert result.ok
    assert result.rows_checked == 2


def test_append_chained_jsonl_escapes_line_separators(tmp_path: Path) -> None:
    log = tmp_path / "audit" / "critic.jsonl"

    append_chained_jsonl(log, {"reason": "line\u2028separator"})

    raw = log.read_text(encoding="utf-8")
    assert "\u2028" not in raw
    assert "\\u2028" in raw
    parsed = json.loads(raw)
    assert parsed["reason"] == "line\u2028separator"
    assert verify_chain_lines(raw.splitlines()).ok


def test_append_chained_jsonl_replaces_supplied_hash_fields(tmp_path: Path) -> None:
    log = tmp_path / "audit" / "hypothesis.jsonl"

    entry = append_chained_jsonl(
        log,
        {
            "type": "pivot",
            "prev_record_hash": "fake-prev",
            "record_hash": "fake-record",
        },
    )

    assert entry["prev_record_hash"] is None
    assert entry["record_hash"] != "fake-record"
    assert verify_chain_lines(log.read_text(encoding="utf-8").splitlines()).ok
