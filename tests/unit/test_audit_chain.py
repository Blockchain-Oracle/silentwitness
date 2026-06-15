"""Unit tests for the pure hash-chain primitives (no AuditLogger / no I/O)."""

from __future__ import annotations

import json

from silentwitness_mcp.audit.chain import (
    canonical_payload,
    compute_record_hash,
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
