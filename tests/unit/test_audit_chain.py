"""Unit tests for the pure hash-chain primitives (no AuditLogger / no I/O)."""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_mcp.audit.chain import (
    append_chained_jsonl_line,
    canonical_payload,
    compute_record_hash,
    reset_chain_cache,
    verify_chain_lines,
)

# ---------------------------------------------------------------------------
# canonical_payload + compute_record_hash
# ---------------------------------------------------------------------------


def test_canonical_payload_drops_hash_fields() -> None:
    entry = {
        "a": 1,
        "b": 2,
        "record_hash": "deadbeef",
        "prev_record_hash": None,
    }
    canonical = canonical_payload(entry)
    parsed = json.loads(canonical)
    assert parsed == {"a": 1, "b": 2}
    assert "record_hash" not in parsed
    assert "prev_record_hash" not in parsed


def test_canonical_payload_is_key_sorted_deterministic() -> None:
    e1 = {"b": 1, "a": 2}
    e2 = {"a": 2, "b": 1}
    assert canonical_payload(e1) == canonical_payload(e2)


def test_compute_record_hash_genesis_row_no_prev() -> None:
    h = compute_record_hash(None, {"a": 1})
    # 64 hex chars; deterministic given fixed input.
    assert len(h) == 64
    h2 = compute_record_hash(None, {"a": 1})
    assert h == h2


def test_compute_record_hash_links_to_prev() -> None:
    h_genesis = compute_record_hash(None, {"a": 1})
    h_with_prev = compute_record_hash(h_genesis, {"b": 2})
    h_no_prev = compute_record_hash(None, {"b": 2})
    # Adding a prev_hash changes the result — proves the chain links.
    assert h_with_prev != h_no_prev


def test_compute_record_hash_changes_when_payload_changes() -> None:
    h1 = compute_record_hash(None, {"a": 1, "tool": "x"})
    h2 = compute_record_hash(None, {"a": 1, "tool": "y"})  # one byte flipped
    assert h1 != h2


# ---------------------------------------------------------------------------
# verify_chain_lines — table cases
# ---------------------------------------------------------------------------


def _build_chained_entries(payloads: list[dict]) -> list[str]:
    """Compose a list of JSONL lines linked into a valid chain."""
    lines = []
    prev = None
    for payload in payloads:
        rec_hash = compute_record_hash(prev, payload)
        entry = {**payload, "prev_record_hash": prev, "record_hash": rec_hash}
        lines.append(json.dumps(entry))
        prev = rec_hash
    return lines


def test_empty_input_is_ok_zero_rows() -> None:
    result = verify_chain_lines([])
    assert result.ok is True
    assert result.rows_checked == 0
    assert result.breaks == ()


def test_single_chained_row_verifies() -> None:
    lines = _build_chained_entries([{"a": 1}])
    result = verify_chain_lines(lines)
    assert result.ok is True
    assert result.rows_checked == 1


def test_three_chained_rows_verify() -> None:
    lines = _build_chained_entries([{"a": 1}, {"b": 2}, {"c": 3}])
    result = verify_chain_lines(lines)
    assert result.ok is True
    assert result.rows_checked == 3


def test_middle_row_tampered_breaks_chain() -> None:
    """Mutate the payload of the middle row without updating its record_hash —
    the recomputed hash diverges; the verifier reports `record_hash_mismatch`."""
    lines = _build_chained_entries([{"a": 1}, {"b": 2}, {"c": 3}])
    middle = json.loads(lines[1])
    middle["b"] = 99  # tamper
    lines[1] = json.dumps(middle)
    result = verify_chain_lines(lines)
    assert result.ok is False
    assert any(b.index == 1 and b.reason == "record_hash_mismatch" for b in result.breaks)


def test_last_row_rewritten_record_hash_breaks() -> None:
    """An attacker replaces only the last row's payload + recomputes ONLY its
    own record_hash but cannot fix the prev_record_hash → still detected."""
    lines = _build_chained_entries([{"a": 1}, {"b": 2}])
    # Rewrite the second row entirely with a fresh genesis-style hash.
    rewritten = {"b": 99}
    rewritten["record_hash"] = compute_record_hash(None, rewritten)
    rewritten["prev_record_hash"] = None  # attacker wishes the chain started here
    lines[1] = json.dumps(rewritten)
    result = verify_chain_lines(lines)
    assert result.ok is False
    # The break is the prev_record_hash mismatch on row 1.
    assert any(b.index == 1 and b.reason == "prev_record_hash_mismatch" for b in result.breaks)


def test_missing_record_hash_field_flagged() -> None:
    """An old (pre-chain) row mixed into a chain-enabled file is detectable —
    verify reports `record_hash_missing` rather than silently skipping."""
    lines = _build_chained_entries([{"a": 1}])
    lines.append(json.dumps({"b": 2}))  # no chain fields
    result = verify_chain_lines(lines)
    assert result.ok is False
    assert any(b.reason == "record_hash_missing" for b in result.breaks)


def test_malformed_json_flagged() -> None:
    lines = _build_chained_entries([{"a": 1}])
    lines.append("{not json")
    result = verify_chain_lines(lines)
    assert result.ok is False
    assert any(b.reason == "malformed_json" for b in result.breaks)


def test_empty_lines_are_skipped_not_counted() -> None:
    lines = _build_chained_entries([{"a": 1}, {"b": 2}])
    lines.insert(1, "")  # blank line between entries
    lines.append("   ")
    result = verify_chain_lines(lines)
    assert result.ok is True
    assert result.rows_checked == 2


def test_genesis_with_non_null_prev_is_break() -> None:
    """If the FIRST row claims to chain off something, that's an obvious forge."""
    payload = {"a": 1}
    fake_prev = "0" * 64
    rec_hash = compute_record_hash(fake_prev, payload)
    line = json.dumps({**payload, "prev_record_hash": fake_prev, "record_hash": rec_hash})
    result = verify_chain_lines([line])
    assert result.ok is False
    assert any(b.reason == "prev_record_hash_mismatch" for b in result.breaks)


# ---------------------------------------------------------------------------
# append_chained_jsonl_line — the direct-writer helper (production seam)
# ---------------------------------------------------------------------------


def test_chained_append_first_row_has_null_prev(tmp_path: Path) -> None:
    reset_chain_cache()
    path = tmp_path / "agent.jsonl"
    rh = append_chained_jsonl_line(path, json.dumps({"tool": "x", "n": 1}))
    line = path.read_text(encoding="utf-8").strip()
    entry = json.loads(line)
    assert entry["prev_record_hash"] is None
    assert entry["record_hash"] == rh
    assert entry["tool"] == "x"


def test_chained_append_second_row_links_to_first(tmp_path: Path) -> None:
    reset_chain_cache()
    path = tmp_path / "agent.jsonl"
    h1 = append_chained_jsonl_line(path, json.dumps({"tool": "x"}))
    h2 = append_chained_jsonl_line(path, json.dumps({"tool": "y"}))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[1])["prev_record_hash"] == h1
    assert json.loads(lines[1])["record_hash"] == h2


def test_chained_append_three_rows_verify_clean(tmp_path: Path) -> None:
    reset_chain_cache()
    path = tmp_path / "findings.jsonl"
    for i in range(3):
        append_chained_jsonl_line(path, json.dumps({"event": "i", "n": i}))
    result = verify_chain_lines(path.read_text(encoding="utf-8").splitlines())
    assert result.ok is True
    assert result.rows_checked == 3


def test_chained_append_resumes_from_existing_file_on_cold_cache(tmp_path: Path) -> None:
    """Simulates a fresh process landing on an existing audit file — the
    helper must read the file's last record_hash to seed its cache."""
    path = tmp_path / "critic.jsonl"
    # Write a chained row through the helper, then drop the cache to simulate
    # a process restart.
    h1 = append_chained_jsonl_line(path, json.dumps({"verdict": "AGREE"}))
    reset_chain_cache()
    h2 = append_chained_jsonl_line(path, json.dumps({"verdict": "CHALLENGE"}))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[1])["prev_record_hash"] == h1
    assert json.loads(lines[1])["record_hash"] == h2
    # Full-file verify still clean across the cold-start boundary.
    result = verify_chain_lines(lines)
    assert result.ok is True


def test_chained_append_rejects_non_object_line(tmp_path: Path) -> None:
    reset_chain_cache()
    path = tmp_path / "x.jsonl"
    import pytest as _p

    with _p.raises(ValueError, match="must be a JSON object"):
        append_chained_jsonl_line(path, json.dumps(["array", "not", "object"]))


def test_chained_append_overwrites_caller_supplied_hash_fields(tmp_path: Path) -> None:
    """A naive caller that pre-populated record_hash / prev_record_hash gets
    those values silently corrected — the helper is the source of truth."""
    reset_chain_cache()
    path = tmp_path / "z.jsonl"
    h = append_chained_jsonl_line(
        path,
        json.dumps({"tool": "y", "record_hash": "deadbeef", "prev_record_hash": "cafebabe"}),
    )
    entry = json.loads(path.read_text(encoding="utf-8").strip())
    assert entry["record_hash"] == h
    assert entry["prev_record_hash"] is None  # genuinely the first row


def test_chained_append_independent_chains_per_path(tmp_path: Path) -> None:
    """Two files write in parallel; their chains advance independently."""
    reset_chain_cache()
    a = tmp_path / "agent.jsonl"
    c = tmp_path / "critic.jsonl"
    ha1 = append_chained_jsonl_line(a, json.dumps({"event": "a1"}))
    hc1 = append_chained_jsonl_line(c, json.dumps({"event": "c1"}))
    ha2 = append_chained_jsonl_line(a, json.dumps({"event": "a2"}))
    # Critic's second row chains to its own first, not to agent's.
    hc2 = append_chained_jsonl_line(c, json.dumps({"event": "c2"}))
    assert ha1 != hc1 and ha2 != hc2
    assert json.loads(a.read_text(encoding="utf-8").splitlines()[1])["prev_record_hash"] == ha1
    assert json.loads(c.read_text(encoding="utf-8").splitlines()[1])["prev_record_hash"] == hc1
