"""HypothesisStack — hypothesis state machine + JSONL event emission.

Manages one active hypothesis at a time (architecture §5.3 ADR-003).
Emits a ``HypothesisEvent`` JSONL line per transition to
``<case_dir>/audit/hypothesis.jsonl``.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from silentwitness_agent.hypothesis._jsonl import emit_hypothesis_event
from silentwitness_agent.hypothesis.types import (
    Hypothesis,
    HypothesisEvent,
    HypothesisEventType,
    HypothesisStatus,
    SpecialistName,
    make_hypothesis_id,
)
from silentwitness_common.types import WorkflowError

_LOG = logging.getLogger(__name__)


class InvalidTransition(WorkflowError):  # noqa: N818 — name matches domain language; "Error" suffix would clash with StrEnum usage
    """Raised when a state transition targets a non-active or already-resolved hypothesis."""


class BudgetEnforcer(Protocol):
    """Injected policy that gates dispatch; implemented by story-hypothesis-budget.

    ``check_dispatch`` raises ``BudgetExceeded`` if dispatch is denied and returns
    ``None`` otherwise — callers must NOT rely on the return value.
    """

    def check_dispatch(self, hypothesis: Hypothesis) -> None: ...


class StackSnapshot(BaseModel):
    """Frozen point-in-time view of the stack — safe to hand to the report renderer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    active: Hypothesis | None
    queued: tuple[Hypothesis, ...]
    history: tuple[Hypothesis, ...]
    total_pivot_count: int


class HypothesisStack:
    """Single-active-hypothesis state machine with thread-safe ID allocation.

    Concurrency note: one hypothesis is tested at a time (architecture §5.3
    ADR-003). The ``threading.Lock`` exists only to make ``form()`` calls
    from multiple threads produce unique IDs without gaps.
    """

    def __init__(
        self,
        case_dir: Path,
        examiner: str,
        budget: BudgetEnforcer | None = None,
    ) -> None:
        self._case_dir = case_dir
        self._examiner = examiner
        self._budget = budget
        self._active: Hypothesis | None = None
        self._queued: deque[Hypothesis] = deque()
        self._history: list[Hypothesis] = []
        self._lock = threading.Lock()
        self._seq = self._resume_seq()

    # ------------------------------------------------------------------
    # Public state properties — return copies so callers cannot mutate
    # ------------------------------------------------------------------

    @property
    def active(self) -> Hypothesis | None:
        with self._lock:
            return self._active

    @property
    def queued(self) -> tuple[Hypothesis, ...]:
        with self._lock:
            return tuple(self._queued)

    @property
    def history(self) -> tuple[Hypothesis, ...]:
        with self._lock:
            return tuple(self._history)

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def form(
        self,
        statement: str,
        specialist: SpecialistName,
        evidence_expected: list[str] | None = None,
        from_hypothesis_id: str | None = None,
    ) -> Hypothesis:
        """Allocate a new hypothesis; become active if none is running, else queue."""
        with self._lock:
            return self._form_locked(
                statement,
                specialist,
                evidence_expected=evidence_expected,
                from_hypothesis_id=from_hypothesis_id,
            )

    def dispatch(self, hypothesis_id: str, specialist: SpecialistName) -> None:
        """Assert budget allows dispatch; emit DISPATCH event.

        Raises ``InvalidTransition`` if ``hypothesis_id`` is not the active
        hypothesis.  Raises ``BudgetExceeded`` if the injected enforcer
        denies dispatch.
        """
        with self._lock:
            active = self._assert_active(hypothesis_id, "dispatch")
            if self._budget is not None:
                self._budget.check_dispatch(active)  # raises BudgetExceeded if denied
            self._emit(
                HypothesisEvent(
                    ts=datetime.now(UTC),
                    type=HypothesisEventType.DISPATCH,
                    hypothesis_id=hypothesis_id,
                )
            )
            active.assigned_specialist = specialist

    def confirm(self, hypothesis_id: str, evidence_audit_ids: list[str]) -> None:
        """Mark active hypothesis CONFIRMED; promote next queued hypothesis."""
        with self._lock:
            active = self._assert_active(hypothesis_id, "confirm")
            self._emit(
                HypothesisEvent(
                    ts=datetime.now(UTC),
                    type=HypothesisEventType.CONFIRM,
                    hypothesis_id=hypothesis_id,
                    related_audit_ids=tuple(evidence_audit_ids),
                )
            )
            active.status = HypothesisStatus.CONFIRMED
            active.evidence_observed = [*active.evidence_observed, *evidence_audit_ids]
            self._history.append(active)
            self._active = self._queued.popleft() if self._queued else None

    def pivot(
        self,
        from_id: str,
        to_statement: str,
        reason: str,
        evidence_expected: list[str] | None = None,
    ) -> Hypothesis:
        """Pivot from a contradicted hypothesis to a new child.

        The child always becomes active immediately — it bypasses the queue
        because a pivot represents an urgent course correction.  Existing
        queued hypotheses remain queued behind the child.
        """
        with self._lock:
            parent = self._assert_active(from_id, "pivot")
            # Emit PIVOT before any state mutation — if emit fails, parent stays ACTIVE.
            self._emit(
                HypothesisEvent(
                    ts=datetime.now(UTC),
                    type=HypothesisEventType.PIVOT,
                    hypothesis_id=from_id,
                    reason=reason[:240],
                    related_audit_ids=tuple(parent.evidence_observed),
                )
            )
            parent.status = HypothesisStatus.PIVOTED
            self._history.append(parent)
            self._active = None
            # Child bypasses queue — pivot is urgent.
            child = self._form_locked(
                to_statement,
                parent.assigned_specialist or SpecialistName.MEMORY,
                evidence_expected=evidence_expected,
                from_hypothesis_id=from_id,
                _force_active=True,
            )
            return child

    def abandon(self, hypothesis_id: str, reason: str) -> None:
        """Mark active hypothesis ABANDONED; promote next queued hypothesis."""
        with self._lock:
            active = self._assert_active(hypothesis_id, "abandon")
            self._emit(
                HypothesisEvent(
                    ts=datetime.now(UTC),
                    type=HypothesisEventType.ABANDON,
                    hypothesis_id=hypothesis_id,
                    reason=reason[:240],
                )
            )
            active.status = HypothesisStatus.ABANDONED
            self._history.append(active)
            self._active = self._queued.popleft() if self._queued else None

    def snapshot(self) -> StackSnapshot:
        """Return an immutable point-in-time view of the stack."""
        with self._lock:
            return StackSnapshot(
                active=self._active,
                queued=tuple(self._queued),
                history=tuple(self._history),
                total_pivot_count=sum(
                    1 for h in self._history if h.status == HypothesisStatus.PIVOTED
                ),
            )

    # ------------------------------------------------------------------
    # Internal helpers (all called with _lock held)
    # ------------------------------------------------------------------

    def _form_locked(
        self,
        statement: str,
        specialist: SpecialistName,
        *,
        evidence_expected: list[str] | None = None,
        from_hypothesis_id: str | None = None,
        _force_active: bool = False,
    ) -> Hypothesis:
        """Allocate a hypothesis; caller must hold ``_lock``."""
        self._seq += 1
        h = Hypothesis(
            id=make_hypothesis_id(self._seq),
            statement=statement,
            status=HypothesisStatus.ACTIVE,
            formed_at=datetime.now(UTC),
            formed_from=from_hypothesis_id,
            evidence_expected=evidence_expected or [],
            assigned_specialist=specialist,
        )
        if _force_active or (self._active is None and not self._queued):
            self._active = h
        else:
            self._queued.append(h)
        self._emit(
            HypothesisEvent(
                ts=datetime.now(UTC),
                type=HypothesisEventType.FORM,
                hypothesis_id=h.id,
            )
        )
        return h

    def _assert_active(self, hypothesis_id: str, operation: str) -> Hypothesis:
        """Return the active hypothesis or raise ``InvalidTransition``."""
        if self._active is None or self._active.id != hypothesis_id:
            raise InvalidTransition(
                f"{operation}: '{hypothesis_id}' is not the active hypothesis"
                f" (active={self._active.id if self._active else None})"
            )
        return self._active

    def _emit(self, event: HypothesisEvent) -> None:
        try:
            emit_hypothesis_event(self._case_dir, event)
        except (OSError, ValueError) as exc:
            _LOG.error(
                "HypothesisStack: JSONL emit failed for %s: %s", event.type, exc, exc_info=True
            )
            raise

    def _resume_seq(self) -> int:
        """Scan existing hypothesis.jsonl for the highest H-NNN to resume numbering."""
        log = self._case_dir / "audit" / "hypothesis.jsonl"
        if not log.exists():
            return 0
        max_seq = 0
        try:
            for raw in log.read_text(encoding="utf-8", errors="replace").splitlines():
                line = raw.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    m = re.match(r"^H-(\d+)$", data.get("hypothesis_id", ""))
                    if m:
                        max_seq = max(max_seq, int(m.group(1)))
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
        except OSError as exc:
            _LOG.warning("HypothesisStack: could not read hypothesis.jsonl for seq resume: %s", exc)
        return max_seq


__all__ = [
    "BudgetEnforcer",
    "HypothesisStack",
    "InvalidTransition",
    "StackSnapshot",
]
