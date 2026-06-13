"""Shared record builders for the report-composition tests.

Not a test module (leading underscore) — imported by the compose test files so
the observation/finding fixtures live in one place.
"""

from __future__ import annotations

from typing import Any


def _obs(
    obs_id: str,
    text: str,
    audit_ids: list[str],
    interp_id: str,
    interp_text: str,
    confidence: str = "HIGH",
) -> dict[str, Any]:
    return {
        "observation_id": obs_id,
        "text": text,
        "audit_ids": audit_ids,
        "cited_spans": [],
        "interpretations": [
            {
                "interpretation_id": interp_id,
                "text": interp_text,
                "confidence": confidence,
                "justification": "test",
                "what_would_change_this_confidence": "counter-evidence",
                "recorded_at": "2026-06-13T14:00:00Z",
            }
        ],
    }


def _finding(fid: str, obs_id: str, interp_id: str, status: str = "APPROVED") -> dict[str, Any]:
    return {
        "finding_id": fid,
        "observation_id": obs_id,
        "interpretation_id": interp_id,
        "status": status,
        "title": f"Title for {fid}",
    }
