"""MCP-tool response envelope — canonical import surface (architecture §4.3).

The envelope's source model (:class:`ToolResponse[TPayload]`, the
:class:`DataProvenance` payload, the :class:`Confidence` enum) lives in
:mod:`silentwitness_common.types` because the agent (which depends on
``silentwitness_common`` but NOT on ``silentwitness_mcp``) must also
read it. Putting the source in ``silentwitness_common`` preserves the
package dependency direction.

This module is the MCP-server-facing import handle. Tools defined in
the FastMCP server (story-fastmcp-server-bootstrap and the per-tool
stories that follow) import from here so the canonical envelope surface
is one stable name:

.. code-block:: python

    from silentwitness_mcp.envelope import ToolResponse, DataProvenance

The :func:`make_failure_envelope` factory bundles the most common
failure shape — ``success=False`` + structured reason — so guard code
(mount validation, evidence-registration refusal, citation-gate
rejection) doesn't repeat the constructor invariants. The fields that
make the envelope structurally meaningful — ``audit_id``, ``examiner``,
``data_provenance`` — are required even for failures so the audit
trail is intact.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from silentwitness_common.types import (
    Confidence,
    DataProvenance,
    ResponseEnvelope,
    ToolResponse,
)

__all__ = [
    "Confidence",
    "DataProvenance",
    "ResponseEnvelope",
    "ToolResponse",
    "make_failure_envelope",
]


def make_failure_envelope[TPayload: BaseModel](
    payload_type: type[TPayload],
    *,
    audit_id: str,
    examiner: str,
    tool: str,
    stdout_path: Path,
    result_sha256: str,
    elapsed_ms: float,
    cmd_argv: tuple[str, ...],
    reason: str,
    caveats: tuple[str, ...] = (),
    advisories: tuple[str, ...] = (),
    corroboration: tuple[str, ...] = (),
    discipline_reminder: str | None = None,
) -> ToolResponse[TPayload]:
    """Factory for the canonical ``success=False`` envelope.

    ``reason`` is appended to ``advisories`` so the structured code
    (e.g. ``MOUNT_NOT_RO_NOEXEC_NOSUID``, ``EVIDENCE_NOT_REGISTERED``,
    ``CITATION_OUTPUT_HASH_MISMATCH``) is uniformly discoverable in the
    same field every downstream consumer reads. The Pydantic invariant
    ``success=False ⇒ data is None`` is satisfied by construction —
    callers cannot accidentally pass ``data=`` to this factory.

    The ``tool``/``stdout_path``/``result_sha256``/``elapsed_ms``/
    ``cmd_argv`` arguments build a :class:`DataProvenance`; even for a
    failure they must be supplied because every audit-log entry needs
    the provenance of the call that produced it. For an "empty"
    provenance use ``stdout_path=Path("/dev/null")``, an all-zeros
    sha256, and ``cmd_argv=()``.
    """
    provenance = DataProvenance(
        tool=tool,
        stdout_path=stdout_path,
        result_sha256=result_sha256,
        elapsed_ms=elapsed_ms,
        cmd_argv=cmd_argv,
    )
    full_advisories = (*advisories, reason)
    return ToolResponse[payload_type](  # type: ignore[valid-type]
        success=False,
        data=None,
        audit_id=audit_id,
        examiner=examiner,
        caveats=caveats,
        advisories=full_advisories,
        corroboration=corroboration,
        discipline_reminder=discipline_reminder,
        data_provenance=provenance,
    )
