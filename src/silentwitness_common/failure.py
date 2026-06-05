"""Failure-code catalog (architecture §4.3 advisories field).

Wire contract MCP ↔ agent. Lives in common (not mcp) so the agent
package can import it without depending on silentwitness_mcp.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class FailureReason(StrEnum):
    MOUNT_NOT_RO_NOEXEC_NOSUID = "MOUNT_NOT_RO_NOEXEC_NOSUID"
    EVIDENCE_NOT_REGISTERED = "EVIDENCE_NOT_REGISTERED"
    CITATION_OUTPUT_HASH_MISMATCH = "CITATION_OUTPUT_HASH_MISMATCH"
    CITATION_AUDIT_ID_NOT_FOUND = "CITATION_AUDIT_ID_NOT_FOUND"
    HALLUCINATED_ENTITIES = "HALLUCINATED_ENTITIES"


# Sentinel tool name stamped into DataProvenance for refusals fired
# BEFORE any tool ran. Lives here (not in envelope) so the agent can
# grep audit-log rows for this literal without importing MCP.
EMPTY_PROVENANCE_TOOL_NAME: Final = "_pre_tool_execution_"


__all__ = ["EMPTY_PROVENANCE_TOOL_NAME", "FailureReason"]
