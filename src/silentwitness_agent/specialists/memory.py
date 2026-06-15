"""Memory forensics specialist subagent (architecture §5.2)."""

from __future__ import annotations

import logging
import sys

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPServerStdio
from pydantic_ai.models import Model

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

# Firewall #1: the memory specialist is a domain-scoped INDEX querier — it discovers via
# full-text search over the parsed evidence index, not raw Volatility tools. Its domain
# focus (processes / netconns / malfind from the memory image) is in its prompt.
MEMORY_TOOL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "search_evidence",
        "timeline",
        "get_record",
        "record_observation",
        "record_interpretation",
        "read_tool_output",
        "register_evidence",
        "verify_evidence_hash",
    }
)

_SYSTEM_PROMPT: str = _load_specialist_prompt("memory")

_ENV_MODEL_KEY = "SILENTWITNESS_SPECIALIST_MODEL_MEMORY"
_DEFAULT_MODEL = "anthropic:claude-haiku-4-5"
_HIGH_QUALITY_MODEL = "anthropic:claude-opus-4-7"


def _resolve_specialist_model(model: str | None) -> Model:
    return resolve_specialist_model(
        model,
        label="memory",
        env_model_key=_ENV_MODEL_KEY,
        default_model=_DEFAULT_MODEL,
        high_quality_model=_HIGH_QUALITY_MODEL,
    )


def build_memory_specialist(
    model: str | None = None,
    shared_server: MCPServerStdio | None = None,
) -> Agent[SpecialistDeps, SpecialistReport]:
    """Build and return the memory specialist agent.

    Model resolution order: ``model`` arg → ``SILENTWITNESS_SPECIALIST_MODEL_MEMORY`` env
    → ``SILENTWITNESS_MODEL`` (global) → ``SILENTWITNESS_MODEL_QUALITY=high`` (→ opus-4-7)
    → default (haiku-4-5).

    ``shared_server``: when the live investigator passes its case-bound MCP server,
    the specialist reuses it (one subprocess, one AuditLogger). Omitting it spawns
    a private case-less server; in practice only isolated unit tests do this — the
    live path always supplies the server via ``register_all_specialists``.
    """
    resolved = _resolve_specialist_model(model)
    model_name = getattr(resolved, "model_name", repr(resolved))
    _LOG.debug("memory specialist: resolved model=%s", model_name)

    server = shared_server or MCPServerStdio(
        sys.executable,  # not bare "python" (absent on SIFT OVA / VPS)
        ["-m", "silentwitness_mcp"],
        sampling_model=resolved,
    )
    filtered = server.filtered(lambda _ctx, td: td.name in MEMORY_TOOL_ALLOWLIST)

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
    memory_specialist: Agent[SpecialistDeps, SpecialistReport],
) -> None:
    """Register ``dispatch_memory_specialist`` as an @investigator.tool.

    The tool runs the memory specialist in its own context window.
    usage=ctx.usage ensures memory specialist tokens count against the
    investigator's per-hypothesis budget, not a separate uncapped pool.
    """

    @investigator.tool
    async def dispatch_memory_specialist(  # pragma: no cover
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
            result = await memory_specialist.run(
                question,
                deps=specialist_deps,
                usage=ctx.usage,
            )
        except Exception:
            _LOG.error(
                "dispatch_memory_specialist failed (hypothesis_id=%s, examiner=%s, question=%r)",
                hypothesis_id,
                ctx.deps.examiner,
                question,
                exc_info=True,
            )
            raise
        return result.output


__all__ = [
    "MEMORY_TOOL_ALLOWLIST",
    "build_memory_specialist",
    "register_as_investigator_tool",
]
