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

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._errors import ServerConfigurationError
from silentwitness_mcp._lifecycle import AppContext
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceContentDriftError,
    EvidenceRegistry,
    EvidenceRegistryError,
)
from silentwitness_mcp.tools.network import zeek_run as _impl_zeek_run

_CaseDeps = tuple[Path, EvidenceRegistry, AuditLogger, str]

_GuardFn = Callable[[str, "Context[ServerSession, AppContext]"], None]

# Tool names wired to real implementations here. Grows as the surface is wired;
# _tool_stubs stubs only the complement so no tool name is ever unadvertised.
WIRED_TOOLS: frozenset[str] = frozenset(
    {
        "register_evidence",
        "verify_evidence_hash",
        "zeek_run",
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


__all__ = ["WIRED_TOOLS", "register_real_tools"]
