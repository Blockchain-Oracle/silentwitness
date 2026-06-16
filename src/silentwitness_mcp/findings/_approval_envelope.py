"""ToolResponse envelope helper for approval decisions."""

from __future__ import annotations

from pydantic import BaseModel

from silentwitness_common.types import ToolResponse
from silentwitness_mcp.envelope import make_empty_provenance


def wrap_approval_envelope[TPayload: BaseModel](
    result: TPayload,
    *,
    audit_id: str,
    examiner: str,
    success: bool,
    advisory: str | None,
) -> ToolResponse[TPayload]:
    return ToolResponse[TPayload](
        success=True,
        data=result,
        audit_id=audit_id,
        examiner=examiner,
        advisories=() if success or advisory is None else (advisory,),
        data_provenance=make_empty_provenance("approve_finding"),
    )


__all__ = ["wrap_approval_envelope"]
