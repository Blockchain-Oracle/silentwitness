"""Property tests for HypothesisStack — random transition sequences maintain invariants."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from silentwitness_agent.hypothesis.stack import HypothesisStack, InvalidTransition
from silentwitness_agent.hypothesis.types import HypothesisStatus, SpecialistName

_STMTS = ["hypothesis-a", "hypothesis-b", "hypothesis-c", "hypothesis-d"]


def _read_events(case_dir: Path) -> list[dict[str, object]]:
    log = case_dir / "audit" / "hypothesis.jsonl"
    if not log.exists():
        return []
    return [json.loads(ln) for ln in log.read_text().splitlines() if ln.strip()]


@settings(max_examples=50, deadline=None)
@given(
    ops=st.lists(
        st.sampled_from(["form", "dispatch", "confirm", "pivot", "abandon"]),
        min_size=1,
        max_size=20,
    )
)
def test_at_most_one_active_at_all_times(ops: list[str]) -> None:
    """At most one hypothesis is active at any point after any sequence of ops."""
    with tempfile.TemporaryDirectory() as d:
        s = HypothesisStack(case_dir=Path(d), examiner="aj")
        for op in ops:
            try:
                if op == "form":
                    s.form(_STMTS[0], SpecialistName.MEMORY)
                elif op == "dispatch" and s.active:
                    s.dispatch(s.active.id, SpecialistName.MEMORY)
                elif op == "confirm" and s.active:
                    s.confirm(s.active.id, [])
                elif op == "pivot" and s.active:
                    s.pivot(s.active.id, _STMTS[1], "reason")
                elif op == "abandon" and s.active:
                    s.abandon(s.active.id, "reason")
            except InvalidTransition:
                pass

        snap = s.snapshot()
        assert snap.active is None or snap.active.status == HypothesisStatus.ACTIVE
        for h in snap.history:
            assert h.status in (
                HypothesisStatus.CONFIRMED,
                HypothesisStatus.PIVOTED,
                HypothesisStatus.ABANDONED,
            )


@settings(max_examples=50, deadline=None)
@given(n_forms=st.integers(min_value=1, max_value=15))
def test_total_events_equals_transitions(n_forms: int) -> None:
    """JSONL line count equals number of successful transition calls."""
    with tempfile.TemporaryDirectory() as d:
        s = HypothesisStack(case_dir=Path(d), examiner="aj")
        event_count = 0
        ids = []
        for _ in range(n_forms):
            h = s.form(_STMTS[0], SpecialistName.MEMORY)
            ids.append(h.id)
            event_count += 1
        for hid in ids:
            if s.active and s.active.id == hid:
                s.confirm(hid, [])
                event_count += 1
        assert len(_read_events(Path(d))) == event_count


@settings(max_examples=50, deadline=None)
@given(n_pivots=st.integers(min_value=1, max_value=5))
def test_pivot_events_reference_existing_parent_in_history(n_pivots: int) -> None:
    """Every PIVOT event's hypothesis_id refers to a hypothesis now in history."""
    with tempfile.TemporaryDirectory() as d:
        case_dir = Path(d)
        s = HypothesisStack(case_dir=case_dir, examiner="aj")
        h = s.form(_STMTS[0], SpecialistName.MEMORY)
        for i in range(n_pivots):
            h = s.pivot(h.id, _STMTS[i % len(_STMTS)], f"reason-{i}")

        snap = s.snapshot()
        history_ids = {h.id for h in snap.history}
        for ev in _read_events(case_dir):
            if ev["type"] == "pivot":
                assert ev["hypothesis_id"] in history_ids
