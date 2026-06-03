"""Hypothesis property tests for AuditLogger invariants."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from hypothesis import given, settings, strategies as st

from silentwitness_common.ids import make_audit_id, parse_audit_id
from silentwitness_mcp.audit.logger import AuditLogger

_HASH64 = "a" * 64
_FROZEN_DAY = datetime(2026, 6, 13, 14, 27, tzinfo=UTC)
_BACKENDS = st.sampled_from(["memory", "disk", "network", "log"])


def _frozen_clock(when: datetime) -> callable:  # type: ignore[type-arg]
    return lambda: when


@given(
    emissions=st.lists(
        st.tuples(_BACKENDS, st.text(min_size=1, max_size=20)),
        min_size=1,
        max_size=30,
    )
)
@settings(max_examples=20, deadline=None)
def test_seq_is_strictly_monotonic(emissions: list[tuple[str, str]]) -> None:
    """For any sequence of (backend, tool) tuples, the resulting audit_id
    sequence numbers are strictly monotonic across the whole batch."""
    with tempfile.TemporaryDirectory() as raw:
        case_dir = Path(raw)
        logger = AuditLogger(case_dir=case_dir, examiner="aj", clock=_frozen_clock(_FROZEN_DAY))
        seqs: list[int] = []
        for backend, tool in emissions:
            entry = logger.emit(
                backend=backend,
                tool=tool,
                params={},
                result_summary={},
                result_sha256=_HASH64,
                stdout_path=Path("/x"),
                elapsed_ms=0.0,
                model_used="m",
            )
            seqs.append(parse_audit_id(entry.audit_id).seq)
        assert seqs == list(range(1, len(emissions) + 1))


@given(
    prior_audit_ids=st.lists(
        st.integers(min_value=1, max_value=999).map(
            lambda n: make_audit_id("aj", _FROZEN_DAY.date(), n)
        ),
        min_size=0,
        max_size=30,
        unique=True,
    )
)
@settings(max_examples=20, deadline=None)
def test_load_sequence_state_recovers_max(prior_audit_ids: list[str]) -> None:
    """For any pre-populated audit file, a fresh logger picks up next == max + 1."""
    with tempfile.TemporaryDirectory() as raw:
        case_dir = Path(raw)
        audit_dir = case_dir / "audit"
        audit_dir.mkdir()
        if prior_audit_ids:
            (audit_dir / "memory.jsonl").write_text(
                "\n".join(json.dumps({"audit_id": aid}) for aid in prior_audit_ids) + "\n",
                encoding="utf-8",
            )
        logger = AuditLogger(case_dir=case_dir, examiner="aj", clock=_frozen_clock(_FROZEN_DAY))
        next_seq = parse_audit_id(logger.next_audit_id()).seq
        expected_max = (
            max(parse_audit_id(aid).seq for aid in prior_audit_ids) if prior_audit_ids else 0
        )
        assert next_seq == expected_max + 1


@given(
    lines=st.lists(
        st.tuples(_BACKENDS, st.text(min_size=1, max_size=20)),
        min_size=1,
        max_size=10,
    )
)
@settings(max_examples=15, deadline=None)
def test_emit_then_parse_round_trip(lines: list[tuple[str, str]]) -> None:
    """Every emitted line parses back into the same AuditEntry."""
    from silentwitness_common.types import AuditEntry

    with tempfile.TemporaryDirectory() as raw:
        case_dir = Path(raw)
        logger = AuditLogger(case_dir=case_dir, examiner="aj", clock=_frozen_clock(_FROZEN_DAY))
        emitted: dict[str, AuditEntry] = {}
        for backend, tool in lines:
            entry = logger.emit(
                backend=backend,
                tool=tool,
                params={},
                result_summary={},
                result_sha256=_HASH64,
                stdout_path=Path("/x"),
                elapsed_ms=0.0,
                model_used="m",
            )
            emitted[entry.audit_id] = entry
        # Re-read every backend file and confirm round-trip equality.
        for backend_file in (case_dir / "audit").glob("*.jsonl"):
            for raw_line in backend_file.read_text(encoding="utf-8").splitlines():
                parsed = AuditEntry.model_validate_json(raw_line)
                assert emitted[parsed.audit_id] == parsed
