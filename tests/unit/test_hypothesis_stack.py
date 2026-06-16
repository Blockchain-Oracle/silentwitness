"""Behavioural tests for HypothesisStack — ≥14 tests per story spec."""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from silentwitness_agent.hypothesis.stack import (
    HypothesisStack,
    InvalidTransition,
    StackSnapshot,
)
from silentwitness_agent.hypothesis.types import (
    BudgetExceeded,
    BudgetExhaustedReason,
    Hypothesis,
    HypothesisEvent,
    HypothesisStatus,
    SpecialistName,
)

_STMT = "If wardriving, expect promiscuous-mode capture tool"
_STMT2 = "If persistence, expect Run-key entry"
_STMT3 = "Vol3 symbol-table mismatch — rebuild then retry pstree"


def _stack(tmp_path: Path, **kw: object) -> HypothesisStack:
    return HypothesisStack(case_dir=tmp_path, examiner="aj", **kw)


def _jsonl_lines(case_dir: Path) -> list[dict[str, object]]:
    log = case_dir / "audit" / "hypothesis.jsonl"
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# form — basic allocation
# ---------------------------------------------------------------------------


def test_form_first_returns_h001_and_becomes_active(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h = s.form(_STMT, SpecialistName.MEMORY)
    assert h.id == "H-001"
    assert h.status == HypothesisStatus.ACTIVE
    assert h.formed_at is not None
    assert s.active is h


def test_form_second_while_active_goes_to_queued(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    h2 = s.form(_STMT2, SpecialistName.DISK)
    assert h2.id == "H-002"
    assert s.active is h1
    assert s.queued == (h2,)


def test_form_emits_one_jsonl_form_line(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h = s.form(_STMT, SpecialistName.MEMORY)
    lines = _jsonl_lines(tmp_path)
    assert len(lines) == 1
    assert lines[0]["type"] == "form"
    assert lines[0]["hypothesis_id"] == h.id


def test_form_jsonl_line_parses_as_hypothesis_event(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    s.form(_STMT, SpecialistName.MEMORY)
    raw = (tmp_path / "audit" / "hypothesis.jsonl").read_text().strip()
    event = HypothesisEvent.model_validate_json(raw)
    assert event.type.value == "form"


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------


def test_dispatch_emits_dispatch_event(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h = s.form(_STMT, SpecialistName.MEMORY)
    s.dispatch(h.id, SpecialistName.MEMORY)
    lines = _jsonl_lines(tmp_path)
    assert lines[-1]["type"] == "dispatch"
    assert lines[-1]["hypothesis_id"] == h.id


def test_dispatch_inactive_hypothesis_raises(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    s.form(_STMT, SpecialistName.MEMORY)
    with pytest.raises(InvalidTransition):
        s.dispatch("H-999", SpecialistName.MEMORY)


def test_dispatch_budget_enforcer_denied_raises_budget_exceeded(tmp_path: Path) -> None:
    class _DenyAll:
        def check_dispatch(self, h: Hypothesis) -> None:
            raise BudgetExceeded(
                h.id, BudgetExhaustedReason.TOKEN_BUDGET_EXHAUSTED, 5000, 0, 5000, 10
            )

    s = _stack(tmp_path, budget=_DenyAll())
    h = s.form(_STMT, SpecialistName.MEMORY)
    before = len(_jsonl_lines(tmp_path))
    with pytest.raises(BudgetExceeded):
        s.dispatch(h.id, SpecialistName.MEMORY)
    # No DISPATCH event written
    assert len(_jsonl_lines(tmp_path)) == before


# ---------------------------------------------------------------------------
# confirm
# ---------------------------------------------------------------------------


def test_confirm_sets_confirmed_moves_to_history_promotes_queued(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    h2 = s.form(_STMT2, SpecialistName.DISK)
    s.confirm(h1.id, ["sift-aj-20260613-007", "sift-aj-20260613-008"])

    assert h1.status == HypothesisStatus.CONFIRMED
    assert h1.evidence_observed == ["sift-aj-20260613-007", "sift-aj-20260613-008"]
    assert h1 in s.history
    assert s.active is h2
    assert s.queued == ()


def test_confirm_emits_confirm_line_with_audit_ids(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    s.confirm(h1.id, ["sift-aj-001", "sift-aj-002"])
    lines = _jsonl_lines(tmp_path)
    confirm = next(ln for ln in lines if ln["type"] == "confirm")
    assert confirm["related_audit_ids"] == ["sift-aj-001", "sift-aj-002"]


def test_confirm_inactive_hypothesis_raises(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    s.form(_STMT, SpecialistName.MEMORY)
    with pytest.raises(InvalidTransition):
        s.confirm("H-999", [])


def test_confirm_empty_queue_leaves_active_none(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h = s.form(_STMT, SpecialistName.MEMORY)
    s.confirm(h.id, [])
    assert s.active is None
    assert s.queued == ()


# ---------------------------------------------------------------------------
# pivot
# ---------------------------------------------------------------------------


def test_pivot_sets_parent_pivoted_child_active_with_formed_from(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    child = s.pivot(h1.id, _STMT3, "vol3 symbol-table mismatch; rebuilt")

    assert h1.status == HypothesisStatus.PIVOTED
    assert h1 in s.history
    assert child.id == "H-002"
    assert child.formed_from == h1.id
    assert s.active is child


def test_pivot_emits_pivot_then_form_events(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    s.pivot(h1.id, _STMT3, "symbol table mismatch")
    lines = _jsonl_lines(tmp_path)
    types = [ln["type"] for ln in lines]
    assert types == ["form", "pivot", "form"]


def test_pivot_jsonl_contains_type_pivot_literal(tmp_path: Path) -> None:
    """Pivot count grep -c '"type":"pivot"' must match the emitted lines."""
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    s.pivot(h1.id, _STMT3, "reason")
    raw = (tmp_path / "audit" / "hypothesis.jsonl").read_text()
    assert '"type":"pivot"' in raw


def test_pivot_child_bypasses_queue(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    h2 = s.form(_STMT2, SpecialistName.DISK)  # queued
    child = s.pivot(h1.id, _STMT3, "reason")
    assert s.active is child
    assert h2 in s.queued


# ---------------------------------------------------------------------------
# pivot — negative path
# ---------------------------------------------------------------------------


def test_pivot_inactive_hypothesis_raises(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    s.form(_STMT, SpecialistName.MEMORY)
    with pytest.raises(InvalidTransition):
        s.pivot("H-999", _STMT3, "reason")


# ---------------------------------------------------------------------------
# abandon
# ---------------------------------------------------------------------------


def test_abandon_sets_abandoned_promotes_queued(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    h2 = s.form(_STMT2, SpecialistName.DISK)
    s.abandon(h1.id, "BUDGET_EXHAUSTED")

    assert h1.status == HypothesisStatus.ABANDONED
    assert h1 in s.history
    assert s.active is h2


def test_abandon_emits_abandon_event_with_reason(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    s.abandon(h1.id, "BUDGET_EXHAUSTED")
    lines = _jsonl_lines(tmp_path)
    abandon = next(ln for ln in lines if ln["type"] == "abandon")
    assert abandon["reason"] == "BUDGET_EXHAUSTED"


def test_abandon_inactive_hypothesis_raises(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    s.form(_STMT, SpecialistName.MEMORY)
    with pytest.raises(InvalidTransition):
        s.abandon("H-999", "reason")


def test_abandon_empty_queue_leaves_active_none(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h = s.form(_STMT, SpecialistName.MEMORY)
    s.abandon(h.id, "BUDGET_EXHAUSTED")
    assert s.active is None


# ---------------------------------------------------------------------------
# snapshot — immutability
# ---------------------------------------------------------------------------


def test_snapshot_queued_mutation_does_not_affect_stack(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    s.form(_STMT, SpecialistName.MEMORY)
    extra = s.form(_STMT2, SpecialistName.DISK)
    snap: StackSnapshot = s.snapshot()
    # snap.queued is a tuple — cannot mutate it; but verify stack queued unchanged
    assert snap.queued == (extra,)
    assert s.queued == (extra,)


def test_snapshot_total_pivot_count(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    h1 = s.form(_STMT, SpecialistName.MEMORY)
    s.pivot(h1.id, _STMT3, "reason")
    snap = s.snapshot()
    assert snap.total_pivot_count == 1


# ---------------------------------------------------------------------------
# Emit failure — state must not mutate on JSONL write error
# ---------------------------------------------------------------------------


def test_emit_oserror_propagates_and_leaves_state_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import silentwitness_agent.hypothesis._jsonl as _jmod

    s = _stack(tmp_path)
    h = s.form(_STMT, SpecialistName.MEMORY)

    def _raise(*_a: object, **_kw: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(_jmod, "append_jsonl_line", _raise)

    with pytest.raises(OSError, match="disk full"):
        s.confirm(h.id, ["sift-aj-001"])

    # State must NOT have mutated — hypothesis is still active and ACTIVE.
    assert s.active is h
    assert h.status == HypothesisStatus.ACTIVE


# ---------------------------------------------------------------------------
# Sequence resume
# ---------------------------------------------------------------------------


def test_seq_resume_from_existing_jsonl(tmp_path: Path) -> None:
    # Pre-write 3 FORM events as if from a previous run
    log = tmp_path / "audit" / "hypothesis.jsonl"
    log.parent.mkdir(parents=True)
    for i in range(1, 4):
        log.write_text(log.read_text() if log.exists() else "")
        ev = HypothesisEvent(
            ts=__import__("datetime").datetime(
                2026, 6, 11, tzinfo=__import__("datetime").timezone.utc
            ),
            type=__import__(
                "silentwitness_agent.hypothesis.types", fromlist=["HypothesisEventType"]
            ).HypothesisEventType.FORM,
            hypothesis_id=f"H-{i:03d}",
        )
        from silentwitness_common.atomic_io import append_jsonl_line

        append_jsonl_line(log, ev.model_dump_json())

    s = _stack(tmp_path)
    assert s._seq == 3
    h = s.form(_STMT, SpecialistName.MEMORY)
    assert h.id == "H-004"


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


def test_concurrent_form_produces_unique_ids(tmp_path: Path) -> None:
    s = _stack(tmp_path)
    results: list[str] = []
    lock = threading.Lock()

    def _do_form() -> None:
        h = s.form(_STMT, SpecialistName.MEMORY)
        with lock:
            results.append(h.id)

    threads = [threading.Thread(target=_do_form) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 50
    assert len(set(results)) == 50
    seqs = sorted(int(hid.split("-")[1]) for hid in results)
    assert seqs == list(range(1, 51))
