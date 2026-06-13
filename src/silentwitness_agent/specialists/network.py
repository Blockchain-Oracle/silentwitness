"""Network forensics specialist subagent (architecture §5.2)."""

from __future__ import annotations

import logging
import os

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model, infer_model

from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult
from silentwitness_agent.specialists._base import (
    SpecialistDeps,
    SpecialistReport,
    _load_specialist_prompt,
)

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool allowlist — architecture §5.2
# ---------------------------------------------------------------------------

NETWORK_TOOL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "zeek_run",
        "suricata_run",
        "record_observation",
        "record_interpretation",
        "read_tool_output",
        "register_evidence",
        "verify_evidence_hash",
    }
)

_SYSTEM_PROMPT: str = _load_specialist_prompt("network")

_ENV_MODEL_KEY = "SILENTWITNESS_SPECIALIST_MODEL_NETWORK"
_ENV_QUALITY_KEY = "SILENTWITNESS_MODEL_QUALITY"
_DEFAULT_MODEL = "anthropic:claude-haiku-4-5"
_HIGH_QUALITY_MODEL = "anthropic:claude-opus-4-7"


def _resolve_specialist_model(model: str | None) -> Model:
    if model is not None:
        try:
            return infer_model(model)
        except (ValueError, Exception) as exc:
            raise ValueError(
                f"network specialist: explicit model={model!r} is not a valid Pydantic AI "
                f"model string (e.g. 'anthropic:claude-haiku-4-5'). Error: {exc}"
            ) from exc
    env_model = os.environ.get(_ENV_MODEL_KEY)
    if env_model:
        try:
            return infer_model(env_model)
        except (ValueError, Exception) as exc:
            raise ValueError(
                f"network specialist: {_ENV_MODEL_KEY}={env_model!r} is not a valid Pydantic AI "
                f"model string (e.g. 'anthropic:claude-haiku-4-5'). Error: {exc}"
            ) from exc
    if os.environ.get(_ENV_QUALITY_KEY, "").lower() == "high":
        return infer_model(_HIGH_QUALITY_MODEL)
    return infer_model(_DEFAULT_MODEL)


def build_network_specialist(
    model: str | None = None,
) -> Agent[SpecialistDeps, SpecialistReport]:
    """Build and return the network specialist agent.

    Model resolution order: ``model`` arg → ``SILENTWITNESS_SPECIALIST_MODEL_NETWORK`` env
    → ``SILENTWITNESS_MODEL_QUALITY=high`` (→ opus-4-7) → default (haiku-4-5).
    """
    resolved = _resolve_specialist_model(model)
    model_name = getattr(resolved, "model_name", repr(resolved))
    _LOG.debug("network specialist: resolved model=%s", model_name)

    mcp_server = MCPServerStdio(
        "python",
        ["-m", "silentwitness_mcp"],
        sampling_model=resolved,
    )
    filtered = mcp_server.filtered(lambda _ctx, td: td.name in NETWORK_TOOL_ALLOWLIST)

    return Agent(
        model=resolved,
        deps_type=SpecialistDeps,
        output_type=SpecialistReport,
        system_prompt=_SYSTEM_PROMPT,
        toolsets=[filtered],
    )


def register_as_investigator_tool(
    investigator: Agent[InvestigatorDeps, InvestigatorResult],
    network_specialist: Agent[SpecialistDeps, SpecialistReport],
) -> None:
    """Register ``dispatch_network_specialist`` as an @investigator.tool.

    The tool runs the network specialist in its own context window.
    usage=ctx.usage ensures network specialist tokens count against the
    investigator's per-hypothesis budget, not a separate uncapped pool.
    """

    @investigator.tool
    async def dispatch_network_specialist(
        ctx: RunContext[InvestigatorDeps],
        question: str,
        hypothesis_id: str,
    ) -> SpecialistReport:
        specialist_deps = SpecialistDeps(
            case_dir=ctx.deps.case_dir,
            examiner=ctx.deps.examiner,
            hypothesis_id=hypothesis_id,
            evidence_paths=(),
            pending_critiques=tuple(ctx.deps.pending_critiques or ()),
        )
        try:
            result = await network_specialist.run(
                question,
                deps=specialist_deps,
                usage=ctx.usage,
            )
        except Exception:
            _LOG.error(
                "dispatch_network_specialist failed (hypothesis_id=%s, examiner=%s, question=%r)",
                hypothesis_id,
                ctx.deps.examiner,
                question,
                exc_info=True,
            )
            raise
        return result.output


__all__ = [
    "NETWORK_TOOL_ALLOWLIST",
    "build_network_specialist",
    "register_as_investigator_tool",
]
