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

``WIRED_TOOLS`` is the agent's tool surface registered here + the finding/index
sub-modules. The raw-evidence wrappers (vol_*/zeek/chainsaw/hayabusa/suricata) are
NOT registered — they are demoted to ingest feeders (firewall layer #1), so the agent
discovers evidence by querying the index, not by free-reading. :mod:`_tool_stubs`
registers only the ``approve_finding`` examiner-approval stub.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Final

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
from silentwitness_mcp.verification.normalizer import normalize_output

_CaseDeps = tuple[Path, EvidenceRegistry, AuditLogger, str]

_GuardFn = Callable[[str, "Context[ServerSession, AppContext]"], None]

# All tool names wired to real implementations across this module + the finding/index
# sub-modules (_tool_impls_findings, _tool_impls_index). Listed explicitly (not imported
# from the sub-modules) to avoid an import cycle, since those modules import helpers from
# here. A registration-time assertion (see register_real_tools) enforces that the live
# tool surface == WIRED_TOOLS | the _tool_stubs complement (just approve_finding), so
# this list cannot silently drift from what is actually registered.
# Firewall layer #1: the agent's discovery surface is the parsed evidence INDEX
# (search_evidence / timeline / get_record), not raw-evidence-producing tools. The
# memory (vol_*), log (chainsaw/hayabusa) and network (zeek/suricata) wrappers are
# DEMOTED to ingest feeders (impl funcs reused by index/ingest_*), so the agent cannot
# free-read raw evidence. read_tool_output stays only to fetch a cited raw blob.
WIRED_TOOLS: frozenset[str] = frozenset(
    {
        "register_evidence",
        "verify_evidence_hash",
        "record_observation",
        "record_interpretation",
        "record_narrative",
        "record_pivot",
        "read_tool_output",
        "search_evidence",
        "get_record",
        "timeline",
    }
)

# Tools registered directly in this module (the rest live in the sub-modules);
# used by register_real_tools to assert WIRED_TOOLS hasn't drifted.
_CORE_TOOLS: frozenset[str] = frozenset(
    {"register_evidence", "verify_evidence_hash", "read_tool_output"}
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
    if not isinstance(app, AppContext) or app.case is None:
        raise ServerConfigurationError(
            "MCP server is not case-bound (SILENTWITNESS_CASE_DIR/EXAMINER/MODEL_USED "
            "unset); evidence-bound tools require a case context"
        )
    case = app.case
    return case.case_dir, case.evidence_registry, case.audit_logger, case.model_used


def _tool_out_dir(case_dir: Path, tool: str, key: str) -> Path:
    """Per-call output dir derived from case_dir — never an LLM-supplied path."""
    digest = hashlib.sha1(key.encode("utf-8"), usedforsecurity=False).hexdigest()[:12]
    return case_dir / ".tool-output" / tool / digest


# Cap read_tool_output so a multi-GB zeek/hayabusa output can't OOM the box —
# the line window is applied AFTER the full read, so the cap is mandatory.
_MAX_READ_BYTES: Final = 64 * 1024 * 1024  # 64 MiB


def _refuse(reason: str, detail: str) -> dict[str, Any]:
    """Single constructor for the LLM-facing refusal envelope so the
    success/reason/detail shape cannot drift via a field typo across wrappers."""
    return {"success": False, "reason": reason, "detail": detail}


def _collect_output_paths(obj: Any) -> list[str]:
    """Recursively collect every ``"path"`` string value in a dumped envelope.

    Tools that decompose evidence into files (zeek -> conn.log/http.log/...) report
    those files as ``path`` entries. Surfacing them lets the wrapper tell the agent
    which files it can read_tool_output for additional context."""
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
    """Advisory listing the output files this tool produced, for context-gathering
    via read_tool_output. ``None`` when the response carries no file paths."""
    paths = _collect_output_paths(dumped)
    if not paths:
        return None
    return (
        "These fields are an INVENTORY of output files, not their content. "
        "read_tool_output(output_path=<one of these>) shows a file's raw bytes; "
        "to CITE evidence in record_observation, pass {record_id, span_text} from a "
        f"search_evidence / get_record hit (citations resolve against index records): {paths}"
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
            return _refuse(
                "INVALID_EVIDENCE_TYPE",
                f"{evidence_type!r} is not one of {[e.value for e in EvidenceType]}",
            )
        audit_id = audit.next_audit_id()
        try:
            record = registry.register(Path(evidence_path), etype, audit_id)
        except EvidenceContentDriftError as exc:
            return _refuse("SHA256_MISMATCH_ON_REREGISTER", str(exc))
        except (EvidenceRegistryError, OSError) as exc:
            return _refuse("REGISTER_FAILED", str(exc))
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
            return _refuse("VERIFY_FAILED", str(exc))
        return {
            "success": True,
            "matches": result.matches,
            "expected": result.expected,
            "actual": result.actual,
        }

    @mcp.tool()
    async def read_tool_output(
        ctx: Context[ServerSession, AppContext],
        output_path: str,
        line_start: int = 0,
        max_lines: int = 200,
    ) -> dict[str, Any]:
        """Read the line-numbered content of a stored tool-output blob (the raw
        bytes behind a search_evidence / get_record hit) when you need to inspect
        more context than the indexed record carries. To CITE evidence, pass
        {record_id, span_text} from a search_evidence / get_record hit to
        record_observation — citations resolve against index records, not this
        blob. Only files under the case's .tool-output directory are readable.
        Page via line_start/max_lines."""
        guard_mount("read_tool_output", ctx)
        case_dir, _registry, audit, model = _case_deps(ctx)
        allowed_root = (case_dir / ".tool-output").resolve()
        try:
            target = Path(output_path).resolve()
        except OSError as exc:
            return _refuse("BAD_PATH", str(exc))
        if not target.is_relative_to(allowed_root) or not target.is_file():
            return _refuse("PATH_NOT_ALLOWED", f"only files under {allowed_root} are readable")
        try:
            size = target.stat().st_size
            if size > _MAX_READ_BYTES:
                return _refuse(
                    "OUTPUT_TOO_LARGE",
                    f"{size} bytes exceeds the {_MAX_READ_BYTES}-byte read cap; "
                    "page a smaller window or narrow the query",
                )
            raw = target.read_bytes()
        except OSError as exc:
            # TOCTOU (deleted/permission-changed between is_file() and read) →
            # structured reject, not a raw OSError out of the tool body.
            return _refuse("READ_FAILED", str(exc))
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
    from silentwitness_mcp._tool_impls_findings import (
        FINDING_TOOLS,
        register_finding_recorders,
    )
    from silentwitness_mcp._tool_impls_index import INDEX_TOOLS, register_index_tools

    # Make WIRED_TOOLS load-bearing: it must equal the union of what this module
    # and the sub-modules actually register, or the hand-maintained list has
    # drifted (a tool added to a sub-module but not advertised, or vice versa).
    # The memory/log/network wrappers are NOT registered — they are demoted to ingest
    # feeders (firewall layer #1); the agent queries the index instead.
    expected = _CORE_TOOLS | FINDING_TOOLS | INDEX_TOOLS
    if WIRED_TOOLS != expected:
        raise ServerConfigurationError(
            f"WIRED_TOOLS drifted from the registered tool sets: {WIRED_TOOLS ^ expected}"
        )

    register_finding_recorders(mcp, guard_mount)
    register_index_tools(mcp, guard_mount)


__all__ = ["WIRED_TOOLS", "register_real_tools"]
