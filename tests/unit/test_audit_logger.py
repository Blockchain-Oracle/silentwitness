"""Behavioural tests for src/silentwitness_mcp/audit/logger.py.

Real filesystem (tmp_path), real Pydantic models — no mocks per
architecture §14. The clock is dependency-injected for determinism.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from silentwitness_common.types import AuditEntry
from silentwitness_mcp.audit.logger import AuditLogger

_HASH64 = "a" * 64


def _frozen_clock(when: datetime) -> Callable[[], datetime]:
    """Return a clock callable that always returns ``when``."""
    return lambda: when


def _emit(
    logger: AuditLogger,
    backend: str = "memory",
    tool: str = "vol_pslist",
) -> AuditEntry:
    """Common emit-with-canonical-params test helper."""
    return logger.emit(
        backend=backend,
        tool=tool,
        params={"image": "/evidence/mem.raw"},
        result_summary={"row_count": 42},
        result_sha256=_HASH64,
        stdout_path=Path("/var/lib/silentwitness/stdout/x.json"),
        elapsed_ms=120.5,
        model_used="anthropic:claude-opus-4-7",
    )


# ---------------------------------------------------------------------------
# next_audit_id semantics
# ---------------------------------------------------------------------------


def test_next_audit_id_starts_at_001(tmp_path: Path) -> None:
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    assert logger.next_audit_id() == "sift-aj-20260613-001"


def test_next_audit_id_increments(tmp_path: Path) -> None:
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    assert logger.next_audit_id() == "sift-aj-20260613-001"
    assert logger.next_audit_id() == "sift-aj-20260613-002"
    assert logger.next_audit_id() == "sift-aj-20260613-003"


def test_next_audit_id_resets_on_date_rollover(tmp_path: Path) -> None:
    """Each calendar day starts a fresh sequence at 001."""
    moments = iter(
        [
            datetime(2026, 6, 13, 23, 59, 59, tzinfo=UTC),
            datetime(2026, 6, 14, 0, 0, 0, tzinfo=UTC),
        ]
    )
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=lambda: next(moments))
    assert logger.next_audit_id() == "sift-aj-20260613-001"
    assert logger.next_audit_id() == "sift-aj-20260614-001"


# ---------------------------------------------------------------------------
# Restart-resume
# ---------------------------------------------------------------------------


def _pre_populate(audit_dir: Path, backend: str, audit_ids: list[str]) -> None:
    """Write canned JSONL lines under a backend file to simulate prior runs."""
    audit_dir.mkdir(parents=True, exist_ok=True)
    target = audit_dir / f"{backend}.jsonl"
    target.write_text(
        "\n".join(json.dumps({"audit_id": aid}) for aid in audit_ids) + "\n",
        encoding="utf-8",
    )


def test_restart_resumes_from_highest_extant_seq_in_one_backend(tmp_path: Path) -> None:
    _pre_populate(
        tmp_path / "audit",
        "memory",
        ["sift-aj-20260613-001", "sift-aj-20260613-002", "sift-aj-20260613-003"],
    )
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    assert logger.next_audit_id() == "sift-aj-20260613-004"


def test_restart_takes_max_across_multiple_backends(tmp_path: Path) -> None:
    _pre_populate(tmp_path / "audit", "memory", ["sift-aj-20260613-005"])
    _pre_populate(tmp_path / "audit", "disk", ["sift-aj-20260613-007"])
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    assert logger.next_audit_id() == "sift-aj-20260613-008"


def test_restart_tolerates_malformed_lines(tmp_path: Path) -> None:
    """A non-JSON or wrong-shape line must NOT crash startup. Skip + continue."""
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True)
    target = audit_dir / "memory.jsonl"
    target.write_text(
        "not-json\n"
        '{"audit_id": "sift-aj-20260613-009"}\n'
        '{"no_audit_id": "field"}\n'
        '{"audit_id": "malformed-not-sift"}\n',
        encoding="utf-8",
    )
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    assert logger.next_audit_id() == "sift-aj-20260613-010"


def test_restart_ignores_other_days(tmp_path: Path) -> None:
    """Yesterday's max does NOT influence today's start."""
    _pre_populate(tmp_path / "audit", "memory", ["sift-aj-20260612-042"])
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    assert logger.next_audit_id() == "sift-aj-20260613-001"


# ---------------------------------------------------------------------------
# emit() — file content + line shape
# ---------------------------------------------------------------------------


def test_emit_writes_one_line_to_named_backend(tmp_path: Path) -> None:
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    entry = _emit(logger, backend="memory")
    target = tmp_path / "audit" / "memory.jsonl"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert content.count("\n") == 1
    # Round-trip the line back through Pydantic to confirm shape stability.
    re_parsed = AuditEntry.model_validate_json(content.rstrip("\n"))
    assert re_parsed == entry
    assert entry.audit_id == "sift-aj-20260613-001"


def test_emit_rejects_path_separator_backend(tmp_path: Path) -> None:
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    for bad in ("../etc/passwd", "memory/sub", "Memory", "0memory", ""):
        with pytest.raises(ValueError, match="invalid backend"):
            _emit(logger, backend=bad)


def test_emit_does_not_consume_seq_on_validation_failure(tmp_path: Path) -> None:
    """If AuditEntry construction fails (e.g. bad hash), the sequence number
    must NOT be consumed — the next caller gets the same number."""
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    with pytest.raises(ValueError):  # Pydantic ValidationError subclasses ValueError
        logger.emit(
            backend="memory",
            tool="vol_pslist",
            params={},
            result_summary={},
            result_sha256="not-hex" * 8,  # invalid
            stdout_path=Path("/x"),
            elapsed_ms=0.0,
            model_used="m",
        )
    # The next successful emit must still produce -001 because the failed call
    # never reached the seq-commit point.
    entry = _emit(logger)
    assert entry.audit_id == "sift-aj-20260613-001"


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


def test_concurrent_next_audit_id_no_duplicates(tmp_path: Path) -> None:
    """100 threads each call next_audit_id once — every result is unique."""
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    results: list[str] = []
    results_lock = threading.Lock()

    def worker() -> None:
        aid = logger.next_audit_id()
        with results_lock:
            results.append(aid)

    threads = [threading.Thread(target=worker) for _ in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 100
    assert len(set(results)) == 100
    # The reserved numbers form a contiguous 001..100 range.
    seqs = sorted(int(aid.split("-")[-1]) for aid in results)
    assert seqs == list(range(1, 101))


def test_concurrent_emit_produces_100_well_formed_unique_lines(tmp_path: Path) -> None:
    """10 threads x 10 emits each → 100 JSONL lines in one file, all valid,
    all distinct audit_ids."""
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))

    def worker(thread_id: int) -> None:
        for j in range(10):
            logger.emit(
                backend="memory",
                tool=f"tool_{thread_id}_{j}",
                params={},
                result_summary={},
                result_sha256=_HASH64,
                stdout_path=Path("/x"),
                elapsed_ms=0.0,
                model_used="m",
            )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    target = tmp_path / "audit" / "memory.jsonl"
    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 100
    audit_ids = []
    for raw in lines:
        entry = AuditEntry.model_validate_json(raw)
        audit_ids.append(entry.audit_id)
    assert len(set(audit_ids)) == 100
    seqs = sorted(int(aid.split("-")[-1]) for aid in audit_ids)
    assert seqs == list(range(1, 101))


# ---------------------------------------------------------------------------
# audit_id_of accessor was dropped (pure passthrough, see PR-100 review)
# ----------------------------------------------------------------------------


def test_logger_properties_round_trip(tmp_path: Path) -> None:
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="ajweb3", clock=_frozen_clock(today))
    assert logger.case_dir == tmp_path
    assert logger.examiner == "ajweb3"


# ---------------------------------------------------------------------------
# Singleton-per-case (flock) — PR-100 silent-failure #8
# ---------------------------------------------------------------------------


def test_second_logger_for_same_case_dir_raises(tmp_path: Path) -> None:
    """Two live AuditLoggers for the same case_dir would dispense colliding
    audit_ids. The flock contract must reject the second."""
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    first = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    try:
        with pytest.raises(RuntimeError, match="singleton"):
            AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    finally:
        first.close()


def test_logger_after_close_can_be_re_acquired(tmp_path: Path) -> None:
    """Releasing the flock via close() must allow a fresh logger to acquire."""
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    first = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    first.close()
    second = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    second.close()


# ---------------------------------------------------------------------------
# I/O failure preservation — code-reviewer #1 / silent-failure N4
# ---------------------------------------------------------------------------


def test_emit_does_not_consume_seq_on_disk_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If append_jsonl_line raises (disk full, EIO, etc.) the seq number is
    NOT consumed — the next successful emit returns the same number."""
    from silentwitness_mcp.audit import logger as _logger_mod

    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))

    call_count = {"n": 0}
    real_append = _logger_mod.append_jsonl_line

    def flaky_append(*args: object, **kwargs: object) -> None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise OSError("simulated disk-full")
        real_append(*args, **kwargs)

    monkeypatch.setattr(_logger_mod, "append_jsonl_line", flaky_append)
    with pytest.raises(OSError, match="simulated"):
        _emit(logger)
    entry = _emit(logger)
    assert entry.audit_id == "sift-aj-20260613-001"
    logger.close()


# ---------------------------------------------------------------------------
# Startup tolerance — silent-failure #1, N2
# ---------------------------------------------------------------------------


def test_load_sequence_state_propagates_oserror_on_unreadable_file(tmp_path: Path) -> None:
    """A glob-matched file we cannot open is a real corruption — silent skip
    would let an unreadable file with seq=999 reset the sequence to 1."""
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    target = audit_dir / "memory.jsonl"
    target.write_text(json.dumps({"audit_id": "sift-aj-20260613-999"}) + "\n", encoding="utf-8")
    target.chmod(0o000)
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    try:
        with pytest.raises((PermissionError, OSError)):
            AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    finally:
        target.chmod(0o644)


def test_load_sequence_state_ignores_non_backend_jsonl(tmp_path: Path) -> None:
    """`.swap.jsonl` and other non-backend-pattern files must NOT be parsed."""
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    (audit_dir / "memory.jsonl").write_text(
        json.dumps({"audit_id": "sift-aj-20260613-005"}) + "\n", encoding="utf-8"
    )
    (audit_dir / ".swap.jsonl").write_text(
        json.dumps({"audit_id": "sift-aj-20260613-999"}) + "\n", encoding="utf-8"
    )
    today = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
    logger = AuditLogger(case_dir=tmp_path, examiner="aj", clock=_frozen_clock(today))
    try:
        assert logger.next_audit_id() == "sift-aj-20260613-006"
    finally:
        logger.close()
