"""Failure-code catalog (architecture §4.3 advisories field).

Wire contract between MCP server (producer of ``ToolResponse``) and the
reference agent (consumer that pattern-matches on the codes to decide
whether to pivot). Lives in :mod:`silentwitness_common` rather than the
MCP-side envelope module so the agent can import it without crossing
the package-dependency boundary.
"""

from __future__ import annotations

from enum import StrEnum


class FailureReason(StrEnum):
    """Structured codes carried in ``ToolResponse.advisories``."""

    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    CITATION_OUTPUT_HASH_MISMATCH = "CITATION_OUTPUT_HASH_MISMATCH"
    CITATION_AUDIT_ID_NOT_FOUND = "CITATION_AUDIT_ID_NOT_FOUND"
    HALLUCINATED_ENTITIES = "HALLUCINATED_ENTITIES"


__all__ = ["FailureReason"]
