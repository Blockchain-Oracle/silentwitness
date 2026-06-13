"""Disk / NTFS-artifact forensics specialist subagent (architecture §5.2)."""

from __future__ import annotations

import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model

from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult
from silentwitness_agent.specialists._base import (
    SpecialistDeps,
    SpecialistReport,
    _load_specialist_prompt,
    resolve_specialist_model,
)

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool allowlist — architecture §5.2
# ---------------------------------------------------------------------------

DISK_TOOL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "parse_mft",
        "parse_amcache",
        "parse_shimcache",
        "parse_prefetch",
        "parse_shellbags",
        "regripper_run",
        "record_observation",
        "record_interpretation",
        "read_tool_output",
        "register_evidence",
        "verify_evidence_hash",
    }
)

_SYSTEM_PROMPT: str = _load_specialist_prompt("disk")

_ENV_MODEL_KEY = "SILENTWITNESS_SPECIALIST_MODEL_DISK"
_DEFAULT_MODEL = "anthropic:claude-haiku-4-5"
_HIGH_QUALITY_MODEL = "anthropic:claude-opus-4-7"


def _resolve_specialist_model(model: str | None) -> Model:
    return resolve_specialist_model(
        model,
        label="disk",
        env_model_key=_ENV_MODEL_KEY,
        default_model=_DEFAULT_MODEL,
        high_quality_model=_HIGH_QUALITY_MODEL,
    )


def build_disk_specialist(
    model: str | None = None,
) -> Agent[SpecialistDeps, SpecialistReport]:
    """Build and return the disk specialist agent.

    Model resolution order: ``model`` arg → ``SILENTWITNESS_SPECIALIST_MODEL_DISK`` env
    → ``SILENTWITNESS_MODEL`` (global) → ``SILENTWITNESS_MODEL_QUALITY=high`` (→ opus-4-7)
    → default (haiku-4-5).
    """
    resolved = _resolve_specialist_model(model)
    model_name = getattr(resolved, "model_name", repr(resolved))
    _LOG.debug("disk specialist: resolved model=%s", model_name)

    mcp_server = MCPServerStdio(
        "python",
        ["-m", "silentwitness_mcp"],
        sampling_model=resolved,
    )
    filtered = mcp_server.filtered(lambda _ctx, td: td.name in DISK_TOOL_ALLOWLIST)

    return Agent(
        model=resolved,
        deps_type=SpecialistDeps,
        output_type=SpecialistReport,
        system_prompt=_SYSTEM_PROMPT,
        toolsets=[filtered],
    )


def register_as_investigator_tool(
    investigator: Agent[InvestigatorDeps, InvestigatorResult],
    disk_specialist: Agent[SpecialistDeps, SpecialistReport],
) -> None:
    """Register ``dispatch_disk_specialist`` as an @investigator.tool.

    The tool runs the disk specialist in its own context window.
    usage=ctx.usage ensures disk specialist tokens count against the
    investigator's per-hypothesis budget, not a separate uncapped pool.
    """

    @investigator.tool
    async def dispatch_disk_specialist(
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
            result = await disk_specialist.run(
                question,
                deps=specialist_deps,
                usage=ctx.usage,
            )
        except Exception:
            _LOG.error(
                "dispatch_disk_specialist failed (hypothesis_id=%s, examiner=%s, question=%r)",
                hypothesis_id,
                ctx.deps.examiner,
                question,
                exc_info=True,
            )
            raise
        return result.output


__all__ = [
    "DISK_TOOL_ALLOWLIST",
    "build_disk_specialist",
    "register_as_investigator_tool",
]
