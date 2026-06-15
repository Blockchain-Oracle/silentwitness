"""Live closed-loop critic wired into the investigate run (architecture §5.5).

The investigator stages findings as it works. On an interval (N new findings OR
M minutes, via :class:`CriticTrigger`), an ``after_model_request`` hook runs the
fresh-context critic over the findings staged since the last pass and routes the
verdicts: AGREE/REJECT mutate findings.json directly; CHALLENGE pushes a record
into ``InvestigatorDeps.pending_critiques``. A dynamic instruction surfaces those
pending challenges back into the agent's context every turn, so the investigator
revises or corroborates the challenged finding rather than barrelling ahead — the
live self-correction loop, not a post-hoc review pass.
"""

from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities import Hooks
from pydantic_ai.messages import ModelResponse
from pydantic_ai.models import ModelRequestContext

from silentwitness_agent.contradiction_detectors import run_contradiction_detectors
from silentwitness_agent.critic import CriticReport, CriticVerdictRecord, StagedFinding, critique
from silentwitness_agent.critic_trigger import CriticTrigger
from silentwitness_agent.investigator import InvestigatorDeps
from silentwitness_mcp.audit.chain import append_chained_jsonl_line

_LOG = logging.getLogger(__name__)

_FINDINGS_JSON = "findings.json"
_CRITIC_JSONL = "audit/critic.jsonl"


class CritiqueFn(Protocol):
    """The critic entry point — real ``critique`` in production, a FunctionModel
    stub in tests (so the loop drives with no API key)."""

    async def __call__(
        self,
        case_dir: Path,
        examiner: str,
        findings: list[StagedFinding],
        *,
        model: str | None = ...,
    ) -> CriticReport: ...


def _audit_critic_error(case_dir: Path, examiner: str) -> None:
    """Leave a durable breadcrumb in critic.jsonl when the LLM critic fails, so the
    audit trail shows the pass degraded to deterministic detectors (not silence)."""
    log = case_dir / _CRITIC_JSONL
    log.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(Exception):
        append_chained_jsonl_line(
            log,
            json.dumps(
                {
                    "type": "critic_error",
                    "reason": "LLM critique failed; deterministic detectors only",
                    "examiner": examiner,
                    "ts": datetime.now(UTC).isoformat(),
                    "phase": "investigate",
                }
            ),
        )


def _finding_count(case_dir: Path) -> int:
    """Number of records in findings.json — the watermark the trigger compares
    against. Matches ``staged_findings_for_review``'s slice index."""
    path = case_dir / _FINDINGS_JSON
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return 0
    return len(data) if isinstance(data, list) else 0


def route_live_verdicts(
    case_dir: Path,
    examiner: str,
    verdicts: Sequence[CriticVerdictRecord],
    pending_critiques: list[CriticVerdictRecord],
) -> int:
    """Route critic verdicts during a live investigation; return CHALLENGE count.

    During investigation, findings.json holds only observations — DRAFT *finding*
    records are not materialised until review. So the live loop does NOT mutate
    findings.json (that is review's job, via handle_critic_verdicts). It routes
    by the live mechanism instead: every verdict is appended to audit/critic.jsonl,
    and each CHALLENGE is pushed into pending_critiques so the next-turn instruction
    surfaces it and the investigator revises or corroborates the finding.
    """
    critic_log = case_dir / _CRITIC_JSONL
    critic_log.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).isoformat()
    # Phase 1: durably record every verdict FIRST. If this raises (disk full), it
    # raises before any pending_critiques mutation, so the in-memory list never
    # disagrees with the audit log.
    for v in verdicts:
        append_chained_jsonl_line(
            critic_log,
            json.dumps(
                {
                    "type": v.verdict.lower(),
                    "finding_id": v.finding_id,
                    "reason": v.reason,
                    "suggested_revision": v.suggested_revision,
                    "missing_corroboration": v.missing_corroboration,
                    "examiner": examiner,
                    "ts": ts,
                    "phase": "investigate",
                }
            ),
        )
    # Phase 2: push CHALLENGEs the agent hasn't already been told about (dedupe by
    # finding_id so a re-reviewed window doesn't stack duplicates).
    already = {v.finding_id for v in pending_critiques}
    challenges = 0
    for v in verdicts:
        if v.verdict == "CHALLENGE" and v.finding_id not in already:
            pending_critiques.append(v)
            already.add(v.finding_id)
            challenges += 1
    return challenges


def render_pending_critiques(critiques: Sequence[CriticVerdictRecord]) -> str:
    """Render the open CHALLENGE verdicts as an instruction block, or '' if none.

    Only CHALLENGE verdicts are actionable mid-loop — AGREE needs no response and
    REJECT already removed the finding."""
    challenges = [v for v in critiques if v.verdict == "CHALLENGE"]
    if not challenges:
        return ""
    lines = [
        "PENDING CRITIC CHALLENGES — a peer reviewer challenged findings you "
        "staged. Address each (revise the finding, or dispatch a specialist to "
        "gather the named corroboration) before you finalise:"
    ]
    for v in challenges:
        parts = [f"- Finding {v.finding_id}: {v.reason}"]
        if v.suggested_revision:
            parts.append(f"Suggested revision: {v.suggested_revision}")
        if v.missing_corroboration:
            parts.append(f"Missing corroboration: {', '.join(v.missing_corroboration)}")
        lines.append(" ".join(parts))
    return "\n".join(lines)


def register_pending_critique_instruction(agent: Agent[InvestigatorDeps, Any]) -> None:
    """Attach a dynamic instruction that injects the open CHALLENGEs each turn."""

    @agent.instructions
    def _pending_critiques(ctx: RunContext[InvestigatorDeps]) -> str:
        return render_pending_critiques(ctx.deps.pending_critiques)


def build_live_critic_hooks(
    case_dir: Path, examiner: str, *, model: str | None = None
) -> Hooks[InvestigatorDeps]:
    """Construct a fresh CriticTrigger and the live-critic hook in one call —
    the single entry point investigate._do_agent_run wires in."""
    trigger = CriticTrigger(case_dir=case_dir, examiner=examiner)
    return build_critic_hooks(case_dir, examiner, trigger, model=model)


def build_critic_hooks(
    case_dir: Path,
    examiner: str,
    trigger: CriticTrigger,
    *,
    model: str | None = None,
    critique_fn: CritiqueFn = critique,
) -> Hooks[InvestigatorDeps]:
    """Return a Hooks instance whose ``after_model_request`` runs the interval critic.

    Resilience: a critic-model failure (no key, offline, timeout) must NOT abort
    the investigation — it is logged and the run continues. Verdict-routing
    failures are likewise logged, not raised, so a single bad pass cannot kill the
    loop. The watermark advances on every fire so a transient failure does not
    re-trigger the critic on every subsequent step.
    """
    hooks: Hooks[InvestigatorDeps] = Hooks()

    @hooks.on.after_model_request
    async def _maybe_critique(
        ctx: RunContext[InvestigatorDeps],
        /,
        *,
        request_context: ModelRequestContext,
        response: ModelResponse,
    ) -> ModelResponse:
        count = _finding_count(case_dir)
        if not trigger.should_fire(count):
            return response
        findings_json = case_dir / _FINDINGS_JSON
        staged = trigger.staged_findings_for_review(findings_json)
        if not staged:
            # Nothing reviewable yet (observations awaiting interpretation). Do NOT
            # advance the watermark — those records stay eligible next tick.
            return response
        # Deterministic detectors first — a model-free CHALLENGE floor that fires
        # even if the LLM critic is unavailable.
        verdicts: list[CriticVerdictRecord] = list(run_contradiction_detectors(staged))
        try:
            report = await critique_fn(case_dir, examiner, staged, model=model)
            verdicts.extend(report.verdicts)
        except Exception:
            _LOG.warning(
                "live critic: LLM critique failed (case=%s) — using deterministic detectors only",
                case_dir.name,
                exc_info=True,
            )
            _audit_critic_error(case_dir, examiner)
        try:
            route_live_verdicts(case_dir, examiner, verdicts, ctx.deps.pending_critiques)
        except Exception:
            # Routing failed — do NOT advance the watermark, so this window is
            # re-reviewed next tick rather than silently lost.
            _LOG.error(
                "live critic: verdict routing failed (case=%s)", case_dir.name, exc_info=True
            )
            return response
        # Advance only after a successful review+route, and only past records that
        # were actually interpreted (see CriticTrigger.advance_after_review).
        trigger.advance_after_review(findings_json)
        return response

    return hooks


__all__ = [
    "build_critic_hooks",
    "build_live_critic_hooks",
    "register_pending_critique_instruction",
    "render_pending_critiques",
    "route_live_verdicts",
]
