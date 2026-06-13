"""Real MCP wrappers for the four finding recorders (record_*).

Split from :mod:`silentwitness_mcp._tool_impls` to keep each file under the
400-LOC cap. Each wrapper reconstructs the pydantic Input model via
``model_validate`` (nested coercion) and returns a structured reject on bad
input rather than raising, so the agent's self-correction loop sees a reason.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from pydantic import ValidationError

from silentwitness_mcp._lifecycle import AppContext
from silentwitness_mcp._tool_impls import _case_deps, _GuardFn
from silentwitness_mcp.findings._audit_index import build_audit_index
from silentwitness_mcp.findings.interpretation import (
    InterpretationInput,
    record_interpretation as _impl_record_interpretation,
)
from silentwitness_mcp.findings.narrative import (
    NarrativeInput,
    record_narrative as _impl_record_narrative,
)
from silentwitness_mcp.findings.observation import (
    ObservationInput,
    record_observation as _impl_record_observation,
)
from silentwitness_mcp.findings.pivot import PivotInput, record_pivot as _impl_record_pivot

FINDING_TOOLS: frozenset[str] = frozenset(
    {"record_observation", "record_interpretation", "record_narrative", "record_pivot"}
)


def register_finding_recorders(mcp: FastMCP, guard_mount: _GuardFn) -> None:
    """Register the four record_* wrappers in :data:`FINDING_TOOLS`."""

    @mcp.tool()
    async def record_observation(
        ctx: Context[ServerSession, AppContext],
        text: str,
        cited_spans: list[dict[str, Any]],
        audit_ids: list[str],
    ) -> dict[str, Any]:
        """Record a verifiable observation. Each cited_span = {audit_id,
        sha256_of_normalized_output, line_start, line_end, span_text}; span_text
        must appear verbatim in the cited tool output (citation gate) and every
        named entity must appear in a cited span (entity gate). Rejections are
        returned, not raised — re-submit with fixes."""
        guard_mount("record_observation", ctx)
        case_dir, _registry, audit, model = _case_deps(ctx)
        try:
            payload = ObservationInput.model_validate(
                {"text": text, "cited_spans": cited_spans, "audit_ids": audit_ids}
            )
        except (ValidationError, ValueError) as exc:
            return {"success": False, "reason": "INVALID_INPUT", "detail": str(exc)}
        resp = _impl_record_observation(
            payload,
            case_dir=case_dir,
            audit_index=build_audit_index(case_dir),
            audit_logger=audit,
            model_used=model,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def record_interpretation(
        ctx: Context[ServerSession, AppContext],
        observation_id: str,
        text: str,
        confidence: str,
        justification: str,
        what_would_change_this_confidence: str,
    ) -> dict[str, Any]:
        """Link an interpretation to an observation. confidence is LOW/MEDIUM/HIGH;
        higher confidence requires a longer justification."""
        guard_mount("record_interpretation", ctx)
        case_dir, _registry, audit, model = _case_deps(ctx)
        try:
            payload = InterpretationInput.model_validate(
                {
                    "observation_id": observation_id,
                    "text": text,
                    "confidence": confidence,
                    "justification": justification,
                    "what_would_change_this_confidence": what_would_change_this_confidence,
                }
            )
        except (ValidationError, ValueError) as exc:
            return {"success": False, "reason": "INVALID_INPUT", "detail": str(exc)}
        resp = _impl_record_interpretation(
            payload, case_dir=case_dir, audit_logger=audit, model_used=model
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def record_narrative(
        ctx: Context[ServerSession, AppContext],
        section: str,
        text: str,
        initial_hypothesis: str,
        attack_chain: list[dict[str, Any]],
        pivots: list[str] | None = None,
        gaps: list[str] | None = None,
    ) -> dict[str, Any]:
        """Append a narrative section. section is one of executive_summary/
        methodology/findings/timeline/iocs; attack_chain = [{observation_id,
        interpretation_id?, note?}]; pivots = [P-NNN]; gaps = free text."""
        guard_mount("record_narrative", ctx)
        case_dir, _registry, audit, model = _case_deps(ctx)
        try:
            payload = NarrativeInput.model_validate(
                {
                    "section": section,
                    "text": text,
                    "initial_hypothesis": initial_hypothesis,
                    "attack_chain": attack_chain,
                    "pivots": tuple(pivots or ()),
                    "gaps": tuple(gaps or ()),
                }
            )
        except (ValidationError, ValueError) as exc:
            return {"success": False, "reason": "INVALID_INPUT", "detail": str(exc)}
        resp = _impl_record_narrative(
            payload, case_dir=case_dir, audit_logger=audit, model_used=model
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def record_pivot(
        ctx: Context[ServerSession, AppContext],
        from_hypothesis_id: str,
        to_hypothesis_id: str,
        reason: str,
        abandoning_evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        """Record a hypothesis pivot — abandoning one theory for another, with the
        evidence that triggered the change."""
        guard_mount("record_pivot", ctx)
        case_dir, _registry, audit, model = _case_deps(ctx)
        try:
            payload = PivotInput.model_validate(
                {
                    "from_hypothesis_id": from_hypothesis_id,
                    "to_hypothesis_id": to_hypothesis_id,
                    "reason": reason,
                    "abandoning_evidence": tuple(abandoning_evidence or ()),
                }
            )
        except (ValidationError, ValueError) as exc:
            return {"success": False, "reason": "INVALID_INPUT", "detail": str(exc)}
        resp = _impl_record_pivot(payload, case_dir=case_dir, audit_logger=audit, model_used=model)
        return resp.model_dump(mode="json")


__all__ = ["FINDING_TOOLS", "register_finding_recorders"]
