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
from silentwitness_mcp.verification.normalizer import normalize_output

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
        "read_tool_output",
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


def _collect_output_paths(obj: Any) -> list[str]:
    """Recursively collect every ``"path"`` string value in a dumped envelope.

    Tools that decompose evidence into files (zeek -> conn.log/http.log/...) report
    those files as ``path`` entries. Surfacing them lets the wrapper tell the agent
    EXACTLY which files to read_tool_output for citation."""
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "path" and isinstance(value, str):
                found.append(value)
            else:
                found.extend(_collect_output_paths(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_collect_output_paths(item))
    return found


def _augment_advisories(dumped: dict[str, Any], *extra: str | None) -> dict[str, Any]:
    """Append guidance to the response's TYPED ``advisories`` field (the same
    channel as ZEEK_CAVEATS) — never an ad-hoc dict key. The agent always reads a
    tool's advisories; the gate still does the hard enforcement. ``None`` entries
    are dropped so callers can pass an optional hint inline."""
    extras = [e for e in extra if e]
    if extras:
        adv = list(dumped.get("advisories") or [])
        adv.extend(extras)
        dumped["advisories"] = adv
    return dumped


def _read_to_cite_advisory(dumped: dict[str, Any]) -> str | None:
    """Advisory pointing the agent at read_tool_output for the output files this
    tool produced. ``None`` when the response carries no file paths."""
    paths = _collect_output_paths(dumped)
    if not paths:
        return None
    return (
        "These fields are an INVENTORY of output files, not their content. To cite a "
        "specific event in record_observation, call read_tool_output(output_path="
        f"<one of these>) and quote the exact line verbatim: {paths}"
    )


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
        dumped = resp.model_dump(mode="json")
        return _augment_advisories(dumped, _read_to_cite_advisory(dumped))

    @mcp.tool()
    async def read_tool_output(
        ctx: Context[ServerSession, AppContext],
        output_path: str,
        line_start: int = 0,
        max_lines: int = 200,
    ) -> dict[str, Any]:
        """Read the line-numbered content of a stored tool-output file (e.g. a
        Zeek log path returned by zeek_run) so you can quote EXACT lines in a
        record_observation citation. Returns an audit_id +
        sha256_of_normalized_output + numbered lines; pass those (with the line
        range and the verbatim span_text) as a cited_span. Only files under the
        case's .tool-output directory are readable. Page via line_start/max_lines."""
        guard_mount("read_tool_output", ctx)
        case_dir, _registry, audit, model = _case_deps(ctx)
        allowed_root = (case_dir / ".tool-output").resolve()
        try:
            target = Path(output_path).resolve()
        except OSError as exc:
            return {"success": False, "reason": "BAD_PATH", "detail": str(exc)}
        if not target.is_relative_to(allowed_root) or not target.is_file():
            return {
                "success": False,
                "reason": "PATH_NOT_ALLOWED",
                "detail": f"only files under {allowed_root} are readable",
            }
        raw = target.read_bytes()
        normalized = normalize_output(raw, "read_tool_output")
        sha = hashlib.sha256(normalized).hexdigest()
        lines = normalized.decode("utf-8", errors="surrogateescape").split("\n")
        total = len(lines)
        start = max(0, line_start)
        window = lines[start : start + max(1, min(max_lines, 500))]
        numbered = "\n".join(f"{start + i}: {ln}" for i, ln in enumerate(window))
        entry = audit.emit(
            backend="read_output",
            tool="read_tool_output",
            params={"output_path": str(target), "line_start": start},
            result_summary={"sha256": sha, "total_lines": total},
            result_sha256=sha,
            stdout_path=target,
            elapsed_ms=0.0,
            model_used=model,
        )
        return {
            "success": True,
            "audit_id": entry.audit_id,
            "sha256_of_normalized_output": sha,
            "total_lines": total,
            "line_start": start,
            "line_end": start + len(window),
            "content": numbered,
        }

    # Lazy imports break the cycle: the sub-modules import helpers from this
    # module, so they can only be imported after it is fully initialised (i.e.
    # at registration time, not module load time).
    from silentwitness_mcp._tool_impls_findings import register_finding_recorders
    from silentwitness_mcp._tool_impls_log import register_log_tools
    from silentwitness_mcp._tool_impls_memory import register_memory_tools

    register_finding_recorders(mcp, guard_mount)
    register_memory_tools(mcp, guard_mount)
    register_log_tools(mcp, guard_mount)


__all__ = ["WIRED_TOOLS", "register_real_tools"]
