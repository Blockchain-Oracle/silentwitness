"""MCP-tool response envelope import surface (architecture §4.3).

The source models live in :mod:`silentwitness_common` so the agent
package can read them without depending on :mod:`silentwitness_mcp`.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from silentwitness_common.failure import EMPTY_PROVENANCE_TOOL_NAME, FailureReason
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


def make_empty_provenance(tool: str) -> DataProvenance:
    """Fresh ``DataProvenance`` for refusals fired BEFORE the tool ran.
    ``stdout_path=/dev/null`` + all-zeros hash let downstream readers
    distinguish "failed pre-execution" from a real run that incidentally
    hashed to zeros. A new instance per call — no shared singleton
    (round-3 silent-failure H2: ``object.__setattr__`` frozen-bypass
    could cross-contaminate). ``tool`` is REQUIRED so a caller cannot
    silently leak the EMPTY_PROVENANCE_TOOL_NAME sentinel into the
    audit log; pass it explicitly even for sentinel construction."""
    return DataProvenance(
        tool=tool,
        stdout_path=Path("/dev/null"),
        result_sha256="0" * 64,
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

    Caller advisories are preserved IN ORDER; ``reason`` is appended last
    so downstream consumers can rely on ``env.advisories[-1]`` being the
    structured failure code. Callers MUST NOT pre-include ``reason`` in
    ``advisories`` — duplicates are preserved verbatim (the factory does
    not dedup).

    ``TPayload`` is inferred from the caller's context (LHS annotation
    or sink parameter type). Failure envelopes carry ``data=None`` so the
    generic is for caller ergonomics; ``make_failure_envelope[T](...)``
    runtime-subscription is a ``TypeError`` (PEP 695 functions aren't
    subscriptable at runtime — bind at the call site instead).
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
