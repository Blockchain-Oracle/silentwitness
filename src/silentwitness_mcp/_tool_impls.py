"""Real MCP tool implementations (architecture §4.2).

These wrappers are the bridge between the LLM-facing MCP tool surface and the
unit-tested forensic/finding implementations in :mod:`silentwitness_mcp.tools`
and :mod:`silentwitness_mcp.findings`. Each wrapper:

1. mount-guards via the injected ``guard_mount`` (same as the legacy stubs);
2. pulls the per-case dependencies (``case_dir`` / ``evidence_registry`` /
   ``audit_logger`` / ``model_used``) from the lifespan ``AppContext`` — the
   server is bound to exactly one case for its lifetime (see ``_case_env``);
3. derives any ``out_dir`` from ``case_dir`` (never an LLM-supplied path);
4. calls the real implementation and returns ``resp.model_dump(mode="json")``.

Returning a plain ``dict`` (not the generic ``ToolResponse[T]``) keeps FastMCP's
output-schema generation simple and gives the agent a stable JSON envelope with
``audit_id`` / ``advisories`` intact for the self-correction loop.

``WIRED_TOOLS`` is the set of names registered here; :mod:`_tool_stubs` registers
``NotImplementedError`` stubs only for the names NOT in this set, so the surface
can be wired incrementally while every tool name stays advertised.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from pydantic import ValidationError

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._errors import ServerConfigurationError
from silentwitness_mcp._lifecycle import AppContext
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceContentDriftError,
    EvidenceRegistry,
    EvidenceRegistryError,
)
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
from silentwitness_mcp.tools.network import zeek_run as _impl_zeek_run

_CaseDeps = tuple[Path, EvidenceRegistry, AuditLogger, str]

_GuardFn = Callable[[str, "Context[ServerSession, AppContext]"], None]

# Tool names wired to real implementations here. Grows as the surface is wired;
# _tool_stubs stubs only the complement so no tool name is ever unadvertised.
# All tool names wired to real implementations across this module + the
# per-domain sub-modules (_tool_impls_memory, _tool_impls_log). Listed
# explicitly (not imported from the sub-modules) to avoid an import cycle, since
# those modules import helpers from here. _tool_stubs stubs only the complement
# (currently suricata_run + approve_finding).
WIRED_TOOLS: frozenset[str] = frozenset(
    {
        "register_evidence",
        "verify_evidence_hash",
        "zeek_run",
        "record_observation",
        "record_interpretation",
        "record_narrative",
        "record_pivot",
        "vol_pslist",
        "vol_psscan",
        "vol_pstree",
        "vol_malfind",
        "vol_netscan",
        "vol_cmdline",
        "vol_dlllist",
        "vol_handles",
        "vol_lsadump",
        "chainsaw_hunt",
        "hayabusa_csv_timeline",
    }
)


def _case_deps(ctx: Context[ServerSession, AppContext]) -> _CaseDeps:
    """Return the non-None per-case deps (case_dir, registry, logger, model) or
    raise a typed config error.

    A server reaches a tool body without a case binding only when started
    without ``SILENTWITNESS_CASE_DIR`` (a misconfiguration or a bare/test boot).
    Real investigate runs always bind, so this is a defensive guard, not a hot
    path — raising surfaces a clear error to the agent rather than an
    ``AttributeError`` on ``None``. Returning a tuple narrows the Optional
    fields for the type checker.
    """
    app = ctx.request_context.lifespan_context
    if (
        not isinstance(app, AppContext)
        or app.case_dir is None
        or app.evidence_registry is None
        or app.audit_logger is None
        or app.model_used is None
    ):
        raise ServerConfigurationError(
            "MCP server is not case-bound (SILENTWITNESS_CASE_DIR/EXAMINER/MODEL_USED "
            "unset); evidence-bound tools require a case context"
        )
    return app.case_dir, app.evidence_registry, app.audit_logger, app.model_used


def _tool_out_dir(case_dir: Path, tool: str, key: str) -> Path:
    """Per-call output dir derived from case_dir — never an LLM-supplied path."""
    digest = hashlib.sha1(key.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return case_dir / ".tool-output" / tool / digest


def register_real_tools(mcp: FastMCP, guard_mount: _GuardFn) -> None:
    """Register the wrappers in :data:`WIRED_TOOLS` on ``mcp``."""

    @mcp.tool()
    async def register_evidence(
        ctx: Context[ServerSession, AppContext],
        evidence_path: str,
        evidence_type: str,
    ) -> dict[str, Any]:
        """Hash + manifest-register an evidence file (idempotent). ``evidence_type``
        is one of: disk_image, memory_image, evtx, pcap."""
        guard_mount("register_evidence", ctx)
        _case_dir, registry, audit, model = _case_deps(ctx)
        t0 = time.monotonic()
        try:
            etype = EvidenceType(evidence_type)
        except ValueError:
            return {
                "success": False,
                "reason": "INVALID_EVIDENCE_TYPE",
                "detail": f"{evidence_type!r} is not one of {[e.value for e in EvidenceType]}",
            }
        audit_id = audit.next_audit_id()
        try:
            record = registry.register(Path(evidence_path), etype, audit_id)
        except EvidenceContentDriftError as exc:
            return {"success": False, "reason": "SHA256_MISMATCH_ON_REREGISTER", "detail": str(exc)}
        except (EvidenceRegistryError, OSError) as exc:
            return {"success": False, "reason": "REGISTER_FAILED", "detail": str(exc)}
        summary: dict[str, object] = {"sha256": record.sha256, "size_bytes": record.size_bytes}
        audit.emit(
            backend="evidence",
            tool="register_evidence",
            params={"evidence_path": evidence_path, "evidence_type": evidence_type},
            result_summary=summary,
            result_sha256=hashlib.sha256(json.dumps(summary, sort_keys=True).encode()).hexdigest(),
            stdout_path=registry.manifest_path,
            elapsed_ms=(time.monotonic() - t0) * 1000.0,
            model_used=model,
        )
        return {
            "success": True,
            "audit_id": audit_id,
            "sha256": record.sha256,
            "size_bytes": record.size_bytes,
            "evidence_type": record.type.value,
        }

    @mcp.tool()
    async def verify_evidence_hash(
        ctx: Context[ServerSession, AppContext],
        evidence_path: str,
    ) -> dict[str, Any]:
        """Re-hash a registered evidence file and compare to the manifest digest."""
        guard_mount("verify_evidence_hash", ctx)
        _case_dir, registry, _audit, _model = _case_deps(ctx)
        try:
            result = registry.verify_hash(Path(evidence_path))
        except (EvidenceRegistryError, OSError) as exc:
            return {"success": False, "reason": "VERIFY_FAILED", "detail": str(exc)}
        return {
            "success": True,
            "matches": result.matches,
            "expected": result.expected,
            "actual": result.actual,
        }

    @mcp.tool()
    async def zeek_run(
        ctx: Context[ServerSession, AppContext],
        pcap_path: str,
        timeout_s: float = 900.0,
    ) -> dict[str, Any]:
        """Zeek offline pcap replay — decomposes a pcap into structured logs."""
        guard_mount("zeek_run", ctx)
        case_dir, registry, audit, model = _case_deps(ctx)
        out_dir = _tool_out_dir(case_dir, "zeek", pcap_path)
        resp = await _impl_zeek_run(
            Path(pcap_path),
            out_dir,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=audit,
            model_used=model,
            timeout_s=timeout_s,
        )
        return resp.model_dump(mode="json")

    @mcp.tool()
    async def record_observation(
        ctx: Context[ServerSession, AppContext],
        text: str,
        cited_spans: list[dict[str, Any]],
        audit_ids: list[str],
    ) -> dict[str, Any]:
        """Record a verifiable observation. Each cited_span = {audit_id, line_start,
        line_end, span_text}; span_text must appear verbatim in the cited tool
        output (citation gate) and every named entity must appear in a cited span
        (entity gate). Rejections are returned, not raised — re-submit with fixes."""
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

    # Lazy imports break the cycle: the sub-modules import helpers from this
    # module, so they can only be imported after it is fully initialised (i.e.
    # at registration time, not module load time).
    from silentwitness_mcp._tool_impls_log import register_log_tools
    from silentwitness_mcp._tool_impls_memory import register_memory_tools

    register_memory_tools(mcp, guard_mount)
    register_log_tools(mcp, guard_mount)


__all__ = ["WIRED_TOOLS", "register_real_tools"]
