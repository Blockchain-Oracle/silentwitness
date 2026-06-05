"""MCP-tool response envelope import surface (architecture §4.3).

The source model lives in :mod:`silentwitness_common.types` so the agent
package (which does not depend on :mod:`silentwitness_mcp`) can read it.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Final

from pydantic import BaseModel

from silentwitness_common.types import (
    AuditId,
    Confidence,
    DataProvenance,
    ResponseEnvelope,
    Sha256Hex,
    ToolResponse,
)

__all__ = [
    "EMPTY_PROVENANCE",
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


class FailureReason(StrEnum):
    """Catalog of structured failure codes carried in ``advisories`` so
    downstream consumers can match on a single string per refusal site.
    StrEnum round-trips through JSON as the bare value."""

    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    CITATION_OUTPUT_HASH_MISMATCH = "CITATION_OUTPUT_HASH_MISMATCH"
    CITATION_AUDIT_ID_NOT_FOUND = "CITATION_AUDIT_ID_NOT_FOUND"
    HALLUCINATED_ENTITIES = "HALLUCINATED_ENTITIES"


_EMPTY_SHA256: Final = "0" * 64


def make_empty_provenance(tool: str) -> DataProvenance:
    """Canonical ``DataProvenance`` for refusals that fired BEFORE the
    underlying tool ran. ``stdout_path=/dev/null`` and an all-zeros hash
    let downstream readers distinguish "failed without producing output"
    from a real run that incidentally hashed to zeros (architecturally
    impossible)."""
    return DataProvenance(
        tool=tool,
        stdout_path=Path("/dev/null"),
        result_sha256=_EMPTY_SHA256,
        elapsed_ms=0.0,
        cmd_argv=(),
    )


EMPTY_PROVENANCE: Final = make_empty_provenance("_unset")


def make_failure_envelope(
    *,
    audit_id: AuditId,
    examiner: str,
    reason: FailureReason,
    data_provenance: DataProvenance = EMPTY_PROVENANCE,
    caveats: tuple[str, ...] = (),
    advisories: tuple[str, ...] = (),
    corroboration: tuple[str, ...] = (),
    discipline_reminder: str | None = None,
) -> ToolResponse[BaseModel]:
    """Canonical ``success=False`` envelope. ``reason`` is appended to
    ``advisories`` so the structured code is in one field every consumer
    reads. The ``ToolResponse[BaseModel]`` return is the honest existential
    type — ``data is None`` so the payload generic is phantom; callers
    that need a narrower bind can ``cast`` at the use site."""
    return ToolResponse[BaseModel](
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
