"""Agent-side tools that let the investigator drive its HypothesisStack.

The ``HypothesisStack`` (form/dispatch/confirm/pivot/abandon) is fully built and
unit-tested, but it was never exposed to the model: architecture §8.1's
"hypothesis form → dispatch → confirm/pivot" loop had no *driver*, so every live
run reported zero hypotheses and the headline wedge never appeared in the report.

These ``@investigator.tool`` functions close that gap. They run in-process with
access to ``ctx.deps.stack`` — unlike the MCP finding tools, which live in a
separate subprocess and cannot touch the agent-side stack. This mirrors the
existing ``dispatch_<specialist>_specialist`` tools, which use the same
``@investigator.tool`` + ``ctx.deps`` pattern.
"""

from __future__ import annotations

import logging

from pydantic_ai import Agent, RunContext

from silentwitness_agent.hypothesis.stack import InvalidTransition
from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult
from silentwitness_common.types import SpecialistName

_LOG = logging.getLogger(__name__)


def _coerce_specialist(value: str) -> SpecialistName:
    """Map a free-text specialist name to the enum, with a helpful error."""
    try:
        return SpecialistName(value.strip().upper())
    except ValueError as exc:
        valid = ", ".join(s.value for s in SpecialistName)
        raise ValueError(f"unknown specialist {value!r}; choose one of: {valid}") from exc


def register_hypothesis_tools(
    investigator: Agent[InvestigatorDeps, InvestigatorResult],
) -> None:
    """Register the form/confirm/pivot/abandon tools onto the investigator agent.

    Call this once, after ``build_investigator``, on the same agent the live
    run executes. The tools mutate ``ctx.deps.stack`` — the very stack whose
    ``snapshot()`` the run reads back for the hypothesis counts.
    """

    @investigator.tool
    async def form_hypothesis(
        ctx: RunContext[InvestigatorDeps],
        statement: str,
        specialist: str,
        evidence_expected: list[str] | None = None,
    ) -> str:
        """Form a concrete, falsifiable hypothesis and make it active.

        Returns the new hypothesis id (``H-NNN``). You MUST call this BEFORE
        recording observations, and reuse the returned id when you dispatch a
        specialist and when you confirm / pivot / abandon. ``specialist`` is one
        of MEMORY, DISK, NETWORK, LOG. ``evidence_expected`` is an optional list
        of what would confirm the hypothesis.
        """
        spec = _coerce_specialist(specialist)
        h = ctx.deps.stack.form(statement, spec, evidence_expected=evidence_expected)
        _LOG.info("form_hypothesis: %s (%s) active", h.id, spec.value)
        return (
            f"formed {h.id} (now active) — statement={h.statement!r}, "
            f"assigned_specialist={spec.value}. Use {h.id} for confirm/pivot/abandon."
        )

    @investigator.tool
    async def confirm_hypothesis(
        ctx: RunContext[InvestigatorDeps],
        hypothesis_id: str,
        evidence_audit_ids: list[str],
    ) -> str:
        """Confirm the active hypothesis, citing the audit_ids that substantiate it.

        Promotes the next queued hypothesis (if any) to active.
        """
        try:
            ctx.deps.stack.confirm(hypothesis_id, evidence_audit_ids)
        except InvalidTransition as exc:
            return f"cannot confirm: {exc}. Form a hypothesis first, then cite its id."
        return f"confirmed {hypothesis_id} with evidence {list(evidence_audit_ids)}"

    @investigator.tool
    async def pivot_hypothesis(
        ctx: RunContext[InvestigatorDeps],
        from_hypothesis_id: str,
        to_statement: str,
        reason: str,
        evidence_expected: list[str] | None = None,
    ) -> str:
        """Pivot from a contradicted hypothesis to a new one, naming the reason.

        The new child hypothesis becomes active immediately. A refuted
        hypothesis is information, not failure.
        """
        try:
            child = ctx.deps.stack.pivot(
                from_hypothesis_id, to_statement, reason, evidence_expected=evidence_expected
            )
        except InvalidTransition as exc:
            return f"cannot pivot: {exc}. Only the active hypothesis can be pivoted."
        return f"pivoted {from_hypothesis_id} -> {child.id} (now active) — reason={reason!r}"

    @investigator.tool
    async def abandon_hypothesis(
        ctx: RunContext[InvestigatorDeps],
        hypothesis_id: str,
        reason: str,
    ) -> str:
        """Abandon the active hypothesis when evidence neither confirms nor pivots it."""
        try:
            ctx.deps.stack.abandon(hypothesis_id, reason)
        except InvalidTransition as exc:
            return f"cannot abandon: {exc}. Only the active hypothesis can be abandoned."
        return f"abandoned {hypothesis_id} — reason={reason!r}"


__all__ = ["register_hypothesis_tools"]
