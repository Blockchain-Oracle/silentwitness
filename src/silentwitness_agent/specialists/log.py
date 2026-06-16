"""Windows event log and detection-engineering specialist subagent (architecture §5.2)."""

from __future__ import annotations

import logging
import sys

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from silentwitness_agent._caching import cache_settings
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

# Firewall #1: the log specialist is a domain-scoped INDEX querier — it discovers via
# full-text search over the parsed evidence index (EVTX rows are tagged
# source_tool="evtx:<channel>"), not raw evtx/chainsaw/hayabusa tools. Its domain focus
# (logons / RDP / PowerShell / service installs) is in its prompt.
LOG_TOOL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "search_evidence",
        "timeline",
        "get_record",
        "list_detections",
        "record_observation",
        "record_interpretation",
        "read_tool_output",
        "register_evidence",
        "verify_evidence_hash",
    }
)

_SYSTEM_PROMPT: str = _load_specialist_prompt("log")

_ENV_MODEL_KEY = "SILENTWITNESS_SPECIALIST_MODEL_LOG"
_DEFAULT_MODEL = "anthropic:claude-haiku-4-5"
_HIGH_QUALITY_MODEL = "anthropic:claude-opus-4-7"


def _resolve_specialist_model(model: str | None) -> Model:
    return resolve_specialist_model(
        model,
        label="log",
        env_model_key=_ENV_MODEL_KEY,
        default_model=_DEFAULT_MODEL,
        high_quality_model=_HIGH_QUALITY_MODEL,
    )


def build_log_specialist(
    model: str | None = None,
    shared_server: MCPServerStdio | None = None,
) -> Agent[SpecialistDeps, SpecialistReport]:
    """Build and return the log specialist agent.

    Model resolution order: ``model`` arg → ``SILENTWITNESS_SPECIALIST_MODEL_LOG`` env
    → ``SILENTWITNESS_MODEL`` (global) → ``SILENTWITNESS_MODEL_QUALITY=high`` (→ opus-4-7)
    → default (haiku-4-5).

    ``shared_server`` reuses the investigator's MCP server (see
    build_memory_specialist); omit only in isolated unit tests.
    """
    resolved = _resolve_specialist_model(model)
    model_name = getattr(resolved, "model_name", repr(resolved))
    _LOG.debug("log specialist: resolved model=%s", model_name)

    server = shared_server or MCPServerStdio(
        sys.executable,  # not bare "python" (absent on SIFT OVA / VPS)
        ["-m", "silentwitness_mcp"],
        sampling_model=resolved,
    )
    filtered = server.filtered(lambda _ctx, td: td.name in LOG_TOOL_ALLOWLIST)

    return Agent(
        model=resolved,
        deps_type=SpecialistDeps,
        output_type=SpecialistReport,
        system_prompt=_SYSTEM_PROMPT,
        toolsets=[filtered],
        model_settings=cache_settings(resolved),
    )


def register_as_investigator_tool(
    investigator: Agent[InvestigatorDeps, InvestigatorResult],
    log_specialist: Agent[SpecialistDeps, SpecialistReport],
) -> None:
    """Register ``dispatch_log_specialist`` as an @investigator.tool.

    The tool runs the log specialist in its own context window.
    usage=ctx.usage ensures log specialist tokens count against the
    investigator's per-hypothesis budget, not a separate uncapped pool.
    """

    @investigator.tool
    async def dispatch_log_specialist(  # pragma: no cover
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
            result = await log_specialist.run(
                question,
                deps=specialist_deps,
                usage=ctx.usage,
                usage_limits=UsageLimits(request_limit=ctx.deps.request_limit),
            )
        except Exception:
            _LOG.error(
                "dispatch_log_specialist failed (hypothesis_id=%s, examiner=%s, question=%r)",
                hypothesis_id,
                ctx.deps.examiner,
                question,
                exc_info=True,
            )
            raise
        return result.output


__all__ = [
    "LOG_TOOL_ALLOWLIST",
    "build_log_specialist",
    "register_as_investigator_tool",
]
