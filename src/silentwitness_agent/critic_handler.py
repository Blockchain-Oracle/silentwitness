"""Routes critic verdicts per architecture §5.5.

Verdict routing:
  AGREE     → critic_status="AGREED"; audit {type:"agree", finding_id, reason, ts}
  CHALLENGE → critic_status="CHALLENGED"; push to pending_critiques;
              audit {type:"challenge", finding_id, reason, suggested_revision, ...}
  REJECT    → remove from findings.json; append to findings.archived.json;
              audit {type:"reject", finding_id, reason, ts}

Thread safety: a single module-level lock serialises all mutations to
findings.json, findings.archived.json, and audit/critic.jsonl.
``pending_critiques`` is shared with the investigator's InvestigatorDeps;
callers performing read-then-clear on the list must use the same lock.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from silentwitness_agent.critic import CriticVerdictRecord
from silentwitness_common.atomic_io import append_jsonl_line, write_json_atomic

_LOG = logging.getLogger(__name__)
_LOCK = threading.Lock()

_FINDINGS_JSON = "findings.json"
_ARCHIVED_JSON = "findings.archived.json"
_CRITIC_JSONL = "audit/critic.jsonl"


class CriticHandlerResult(BaseModel):
    """Summary counts returned by handle_critic_verdicts."""

    agree_count: int = Field(default=0, ge=0)
    challenge_count: int = Field(default=0, ge=0)
    reject_count: int = Field(default=0, ge=0)
    archived_finding_ids: list[str] = Field(default_factory=list)
    audit_lines_written: int = Field(default=0, ge=0)


def handle_critic_verdicts(
    case_dir: Path,
    examiner: str,
    verdicts: list[CriticVerdictRecord],
    pending_critiques: list[CriticVerdictRecord],
) -> CriticHandlerResult:
    """Route critic verdicts per architecture §5.5 routing table.

    Reads findings.json once, applies all verdict mutations in memory, then
    writes findings.json and findings.archived.json atomically at the end.
    audit/critic.jsonl receives one line per verdict (including skips).
    """
    audit_path = case_dir / _CRITIC_JSONL
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    agree_count = 0
    challenge_count = 0
    reject_count = 0
    archived_ids: list[str] = []
    audit_lines = 0

    with _LOCK:
        raw_findings = _read_json_list(case_dir / _FINDINGS_JSON)
        archived = _read_json_list(case_dir / _ARCHIVED_JSON)

        # Build a mutable dict keyed by finding id, preserving insertion order.
        findings_map: dict[str, dict[str, Any]] = {}
        for item in raw_findings:
            if isinstance(item, dict):
                fid_key: str = item.get("id") or ""
                if fid_key:
                    findings_map[fid_key] = dict(item)

        rejected_ids: set[str] = set()

        for verdict in verdicts:
            fid = verdict.finding_id
            ts = _now_iso()

            if fid not in findings_map:
                _emit_line(
                    audit_path,
                    {
                        "type": "skip",
                        "finding_id": fid,
                        "reason": "finding not found in findings.json",
                        "examiner": examiner,
                        "ts": ts,
                    },
                )
                audit_lines += 1
                _LOG.warning("critic_handler: finding_id=%s not in findings.json; skipped", fid)
                continue

            finding = findings_map[fid]

            if verdict.verdict == "AGREE":
                _handle_agree(audit_path, finding, verdict, ts, examiner)
                agree_count += 1
                audit_lines += 1

            elif verdict.verdict == "CHALLENGE":
                _handle_challenge(audit_path, finding, verdict, ts, examiner, pending_critiques)
                challenge_count += 1
                audit_lines += 1

            elif verdict.verdict == "REJECT":
                _handle_reject(audit_path, finding, verdict, ts, examiner, archived)
                rejected_ids.add(fid)
                reject_count += 1
                archived_ids.append(fid)
                audit_lines += 1

        remaining = [findings_map[k] for k in findings_map if k not in rejected_ids]
        write_json_atomic(case_dir / _FINDINGS_JSON, remaining)
        if rejected_ids:
            write_json_atomic(case_dir / _ARCHIVED_JSON, archived)

    return CriticHandlerResult(
        agree_count=agree_count,
        challenge_count=challenge_count,
        reject_count=reject_count,
        archived_finding_ids=archived_ids,
        audit_lines_written=audit_lines,
    )


# ---------------------------------------------------------------------------
# Routing helpers — called inside the module-level _LOCK
# ---------------------------------------------------------------------------


def _handle_agree(
    audit_path: Path,
    finding: dict[str, Any],
    verdict: CriticVerdictRecord,
    ts: str,
    examiner: str,
) -> None:
    finding["critic_status"] = "AGREED"
    _emit_line(
        audit_path,
        {
            "type": "agree",
            "finding_id": verdict.finding_id,
            "reason": verdict.reason,
            "examiner": examiner,
            "ts": ts,
        },
    )


def _handle_challenge(
    audit_path: Path,
    finding: dict[str, Any],
    verdict: CriticVerdictRecord,
    ts: str,
    examiner: str,
    pending_critiques: list[CriticVerdictRecord],
) -> None:
    finding["critic_status"] = "CHALLENGED"
    finding["critic_challenge_reason"] = verdict.reason
    pending_critiques.append(verdict)
    _emit_line(
        audit_path,
        {
            "type": "challenge",
            "finding_id": verdict.finding_id,
            "reason": verdict.reason,
            "suggested_revision": verdict.suggested_revision,
            "missing_corroboration": verdict.missing_corroboration,
            "examiner": examiner,
            "ts": ts,
        },
    )


def _handle_reject(
    audit_path: Path,
    finding: dict[str, Any],
    verdict: CriticVerdictRecord,
    ts: str,
    examiner: str,
    archived: list[Any],
) -> None:
    archived.append(
        {
            **finding,
            "status": "ARCHIVED",
            "critic_status": "REJECTED",
            "archival_reason": verdict.reason,
            "archived_at": ts,
        }
    )
    _emit_line(
        audit_path,
        {
            "type": "reject",
            "finding_id": verdict.finding_id,
            "reason": verdict.reason,
            "examiner": examiner,
            "ts": ts,
        },
    )


# ---------------------------------------------------------------------------
# I/O primitives
# ---------------------------------------------------------------------------


def _emit_line(path: Path, record: dict[str, Any]) -> None:
    append_jsonl_line(path, json.dumps(record, ensure_ascii=False, sort_keys=True))


def _read_json_list(path: Path) -> list[Any]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
        _LOG.warning("critic_handler: cannot read %s err=%s", path, exc)
        return []


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


__all__ = ["CriticHandlerResult", "handle_critic_verdicts"]
