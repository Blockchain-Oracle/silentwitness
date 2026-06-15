"""Unit tests for the chained-append writer helper + companions.

Split from ``test_audit_chain.py`` so each file stays under the 400-LOC gate
(architecture §14). The pure primitives (canonical_payload, compute_record_hash,
verify_chain_lines) live next door; this file covers the I/O-touching layer:
``append_chained_jsonl_line``, ``_read_last_record_hash``,
``strip_chain_fields_from_line``, and the private test seam
``_reset_chain_cache``.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from silentwitness_mcp.audit.chain import (
    ChainSeedError,
    _reset_chain_cache,
    append_chained_jsonl_line,
    strip_chain_fields_from_line,
    verify_chain_lines,
)

# ---------------------------------------------------------------------------
# append_chained_jsonl_line — happy path
# ---------------------------------------------------------------------------


def test_chained_append_first_row_has_null_prev(tmp_path: Path) -> None:
    _reset_chain_cache()
    path = tmp_path / "agent.jsonl"
    rh = append_chained_jsonl_line(path, json.dumps({"tool": "x", "n": 1}))
    line = path.read_text(encoding="utf-8").strip()
    entry = json.loads(line)
    assert entry["prev_record_hash"] is None
    assert entry["record_hash"] == rh
    assert entry["tool"] == "x"


def test_chained_append_second_row_links_to_first(tmp_path: Path) -> None:
    _reset_chain_cache()
    path = tmp_path / "agent.jsonl"
    h1 = append_chained_jsonl_line(path, json.dumps({"tool": "x"}))
    h2 = append_chained_jsonl_line(path, json.dumps({"tool": "y"}))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[1])["prev_record_hash"] == h1
    assert json.loads(lines[1])["record_hash"] == h2


def test_chained_append_three_rows_verify_clean(tmp_path: Path) -> None:
    _reset_chain_cache()
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
    h1 = append_chained_jsonl_line(path, json.dumps({"verdict": "AGREE"}))
    _reset_chain_cache()
    h2 = append_chained_jsonl_line(path, json.dumps({"verdict": "CHALLENGE"}))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert json.loads(lines[1])["prev_record_hash"] == h1
    assert json.loads(lines[1])["record_hash"] == h2
    assert verify_chain_lines(lines).ok is True


def test_chained_append_rejects_non_object_line(tmp_path: Path) -> None:
    _reset_chain_cache()
    path = tmp_path / "x.jsonl"
    with pytest.raises(ValueError, match="must be a JSON object"):
        append_chained_jsonl_line(path, json.dumps(["array", "not", "object"]))


def test_chained_append_overwrites_caller_supplied_hash_fields(tmp_path: Path) -> None:
    """A naive caller that pre-populated record_hash / prev_record_hash gets
    those values silently corrected — the helper is the source of truth."""
    _reset_chain_cache()
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
    _reset_chain_cache()
    a = tmp_path / "agent.jsonl"
    c = tmp_path / "critic.jsonl"
    ha1 = append_chained_jsonl_line(a, json.dumps({"event": "a1"}))
    hc1 = append_chained_jsonl_line(c, json.dumps({"event": "c1"}))
    ha2 = append_chained_jsonl_line(a, json.dumps({"event": "a2"}))
    hc2 = append_chained_jsonl_line(c, json.dumps({"event": "c2"}))
    assert ha1 != hc1 and ha2 != hc2
    assert json.loads(a.read_text(encoding="utf-8").splitlines()[1])["prev_record_hash"] == ha1
    assert json.loads(c.read_text(encoding="utf-8").splitlines()[1])["prev_record_hash"] == hc1


# ---------------------------------------------------------------------------
# Path normalisation — relative vs absolute references share one chain
# ---------------------------------------------------------------------------


def test_chained_append_normalises_relative_and_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``Path("./x.jsonl")`` and ``Path("/abs/x.jsonl")`` for the same file must
    share one chain cache. Without ``path.resolve()`` they would be distinct
    dict keys, and the second write would start a fresh genesis row —
    silently breaking the chain at verify time."""
    _reset_chain_cache()
    monkeypatch.chdir(tmp_path)
    rel = Path("agent.jsonl")
    abs_path = tmp_path / "agent.jsonl"

    h_abs = append_chained_jsonl_line(abs_path, json.dumps({"step": 1}))
    h_rel = append_chained_jsonl_line(rel, json.dumps({"step": 2}))

    lines = abs_path.read_text(encoding="utf-8").splitlines()
    second = json.loads(lines[1])
    assert second["prev_record_hash"] == h_abs
    assert second["record_hash"] == h_rel
    assert verify_chain_lines(lines).ok is True


# ---------------------------------------------------------------------------
# Concurrent writers — the per-path lock keeps the chain straight
# ---------------------------------------------------------------------------


def test_chained_append_concurrent_writers_serialised_by_lock(tmp_path: Path) -> None:
    """Two threads racing on the same path must serialise — the lock holds
    the read-prev/compute/append/cache window. Without it both threads would
    read the same prior hash, write siblings, and the chain would break.
    This is the bug class PR #237 exists to fix; this test pins it shut."""
    _reset_chain_cache()
    path = tmp_path / "agent.jsonl"
    n_per_thread = 25
    barrier = threading.Barrier(2)

    def write_n(tag: str) -> None:
        barrier.wait()
        for i in range(n_per_thread):
            append_chained_jsonl_line(path, json.dumps({"thread": tag, "i": i}))

    t1 = threading.Thread(target=write_n, args=("a",))
    t2 = threading.Thread(target=write_n, args=("b",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2 * n_per_thread
    result = verify_chain_lines(lines)
    assert result.ok is True, f"concurrent writers broke chain: {result.breaks}"
    assert result.rows_checked == 2 * n_per_thread


# ---------------------------------------------------------------------------
# Loud failure on chain-seed corruption
# ---------------------------------------------------------------------------


def test_read_last_record_hash_raises_on_malformed_tail(tmp_path: Path) -> None:
    """A file ending in malformed JSON used to silently restart the chain —
    the verifier would only catch it days later. Now it raises on the next
    write so the operator sees it immediately."""
    _reset_chain_cache()
    path = tmp_path / "agent.jsonl"
    append_chained_jsonl_line(path, json.dumps({"step": 1}))
    with path.open("a", encoding="utf-8") as fh:
        fh.write("{not json\n")
    _reset_chain_cache()
    with pytest.raises(ChainSeedError, match="malformed JSON"):
        append_chained_jsonl_line(path, json.dumps({"step": 2}))


def test_read_last_record_hash_raises_on_chain_regression_at_tail(tmp_path: Path) -> None:
    """A chain that has chained rows earlier but a non-chained tail row is a
    regression — silently restarting from genesis would mask whatever bypassed
    the helper. We refuse and raise."""
    _reset_chain_cache()
    path = tmp_path / "agent.jsonl"
    append_chained_jsonl_line(path, json.dumps({"step": 1}))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"step": 2, "missing": "chain_fields"}) + "\n")
    _reset_chain_cache()
    with pytest.raises(ChainSeedError, match="tail row has no record_hash"):
        append_chained_jsonl_line(path, json.dumps({"step": 3}))


def test_read_last_record_hash_allows_pre_chain_file(tmp_path: Path) -> None:
    """A file with NO chained rows yet (pre-chain legacy data) is the one
    case where starting a fresh chain head is safe — preserve that behaviour
    so the migration from pre-chain to chained logs doesn't crash."""
    _reset_chain_cache()
    path = tmp_path / "legacy.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"legacy": "row1"}) + "\n")
        fh.write(json.dumps({"legacy": "row2"}) + "\n")
    h = append_chained_jsonl_line(path, json.dumps({"new": "row3"}))
    third = json.loads(path.read_text(encoding="utf-8").splitlines()[2])
    assert third["prev_record_hash"] is None
    assert third["record_hash"] == h


# ---------------------------------------------------------------------------
# strip_chain_fields_from_line — symmetric loud failure
# ---------------------------------------------------------------------------


def test_strip_chain_fields_raises_on_non_object_line() -> None:
    """Symmetric with ``append_chained_jsonl_line``: a caller passing a
    corrupted (non-object) line should see a ValueError pointing at the strip
    step, not a confusing Pydantic ValidationError downstream."""
    with pytest.raises(ValueError, match="expects a JSON object"):
        strip_chain_fields_from_line(json.dumps([1, 2, 3]))


def test_strip_chain_fields_removes_both_chain_fields() -> None:
    """The happy path: chain fields stripped, payload preserved, output is
    a valid JSON object string ready for Pydantic ``model_validate_json``."""
    line = json.dumps({"event": "hello", "prev_record_hash": None, "record_hash": "deadbeef"})
    stripped = strip_chain_fields_from_line(line)
    payload = json.loads(stripped)
    assert payload == {"event": "hello"}


# ---------------------------------------------------------------------------
# Privacy of the reset seam — pin it shut so production callers can't import
# ---------------------------------------------------------------------------


def test_reset_chain_cache_is_not_in_public_api() -> None:
    """``_reset_chain_cache`` is a test seam; its underscore prefix and
    absence from ``__all__`` mark it as private. If a future refactor exports
    it by accident, this test catches that — production callers would silently
    introduce chain-break risk."""
    from silentwitness_mcp.audit import chain as chain_module

    assert "_reset_chain_cache" not in chain_module.__all__
    assert "reset_chain_cache" not in chain_module.__all__


# ---------------------------------------------------------------------------
# Cross-process cache invalidation (round-2 N3) — cached prev_hash must be
# refreshed if another process appended to the file between our writes.
# ---------------------------------------------------------------------------


def test_chained_append_refreshes_cache_after_external_write(tmp_path: Path) -> None:
    """Simulates a second process appending between our writes. Without the
    file-size cache invalidation the second write would reuse the stale
    cached prev_hash and produce a chain fork at verify time. With the size
    check the cache is dropped and we re-read disk."""
    from silentwitness_mcp.audit import chain as chain_module

    _reset_chain_cache()
    path = tmp_path / "agent.jsonl"
    append_chained_jsonl_line(path, json.dumps({"step": 1}))
    # Snapshot our process's view (size_after_h1, h1).
    our_view = dict(chain_module._LAST_HASH_CACHE)

    # Simulate a foreign process appending h2: drop the cache, write, restore
    # our stale view (this is the bug condition the size-check defends).
    _reset_chain_cache()
    h2 = append_chained_jsonl_line(path, json.dumps({"step": 2}))
    chain_module._LAST_HASH_CACHE.clear()
    chain_module._LAST_HASH_CACHE.update(our_view)

    # h3 from "our" process. Cached size is now smaller than current file size
    # → size mismatch → re-seed → chain to h2 (correct), not h1 (stale).
    h3 = append_chained_jsonl_line(path, json.dumps({"step": 3}))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    third = json.loads(lines[2])
    assert third["prev_record_hash"] == h2
    assert third["record_hash"] == h3
    assert verify_chain_lines(lines).ok is True


# ---------------------------------------------------------------------------
# Sidecar lockfile location (round-2: sidecar moved to audit/.locks/)
# ---------------------------------------------------------------------------


def test_chained_append_creates_sidecar_in_locks_subdir(tmp_path: Path) -> None:
    """The flock sidecar lives under ``audit/.locks/<file>.lock`` so it stays
    hidden from ``ls audit/``, default tarballers, and the verifier's
    ``*.jsonl`` glob. A regression that puts the lockfile back at the audit
    root would pollute every operator's directory listing."""
    _reset_chain_cache()
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    path = audit_dir / "agent.jsonl"
    append_chained_jsonl_line(path, json.dumps({"step": 1}))

    assert (audit_dir / ".locks" / "agent.jsonl.lock").exists()
    # Lockfile is NOT at the audit root.
    assert not list(audit_dir.glob(".agent.jsonl*"))
