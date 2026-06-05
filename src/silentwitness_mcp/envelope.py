"""MCP-tool response envelope import surface (architecture §4.3).

The source models live in :mod:`silentwitness_common` so the agent
package can read them without depending on :mod:`silentwitness_mcp`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pydantic import BaseModel

from silentwitness_common.failure import FailureReason
from silentwitness_common.types import (
    AuditId,
    Confidence,
    DataProvenance,
    ResponseEnvelope,
    Sha256Hex,
    ToolResponse,
)

__all__ = [
    "EMPTY_PROVENANCE_TOOL_NAME",
    "AuditId",
    "Confidence",
    "DataProvenance",
    "FailureReason",
    "ResponseEnvelope",
    "Sha256Hex",
    "ToolResponse",
    "make_empty_provenance",
    "make_failure_envelope",
]

# Tool-name sentinel used by :func:`make_empty_provenance` when the
# caller cannot supply a real one. Surfaces in audit logs as the literal
# string so an analyst grepping for "_pre_tool_execution_" finds every
# refusal that fired before any tool ran.
EMPTY_PROVENANCE_TOOL_NAME: Final = "_pre_tool_execution_"
_EMPTY_SHA256: Final = "0" * 64


def make_empty_provenance(tool: str = EMPTY_PROVENANCE_TOOL_NAME) -> DataProvenance:
    """Build a fresh ``DataProvenance`` for refusals fired BEFORE the
    underlying tool ran. Stdout_path=/dev/null + all-zeros hash let
    downstream readers distinguish "failed pre-execution" from a real
    run that incidentally hashed to zeros (architecturally impossible).
    A NEW instance is returned per call — the EMPTY_PROVENANCE
    module-level singleton was removed (cross-envelope contamination
    risk via Pydantic's ``object.__setattr__`` frozen-bypass channel)."""
    return DataProvenance(
        tool=tool,
        stdout_path=Path("/dev/null"),
        result_sha256=_EMPTY_SHA256,
        elapsed_ms=0.0,
        cmd_argv=(),
    )


def make_failure_envelope[TPayload: BaseModel](
    *,
    audit_id: AuditId,
    examiner: str,
    reason: FailureReason,
    data_provenance: DataProvenance,
    caveats: tuple[str, ...] = (),
    advisories: tuple[str, ...] = (),
    corroboration: tuple[str, ...] = (),
    discipline_reminder: str | None = None,
) -> ToolResponse[TPayload]:
    """Build the canonical ``success=False`` envelope.

    ``data_provenance`` is REQUIRED so callers cannot omit it and have
    the literal ``_pre_tool_execution_`` tool name leak silently into
    the audit log. Use :func:`make_empty_provenance` to obtain a
    pre-tool-execution shape, passing the intended tool name.

    Caller advisories are preserved IN ORDER; ``reason`` is appended last
    so downstream consumers can rely on ``env.advisories[-1]`` being the
    structured failure code. Callers must NOT pre-include ``reason`` in
    ``advisories`` — duplicates are preserved verbatim (the factory does
    not dedup; see ``test_make_failure_envelope_allows_duplicate_reason_in_advisories``).
    """
    return ToolResponse[TPayload](
        success=False,
        data=None,
        audit_id=audit_id,
        examiner=examiner,
        caveats=caveats,
        advisories=(*advisories, reason.value),
        corroboration=corroboration,
        discipline_reminder=discipline_reminder,
        data_provenance=data_provenance,
    )
