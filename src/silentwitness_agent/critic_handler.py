"""Routes critic verdicts per architecture §5.5.

Verdict routing:
  AGREE     → critic_status="AGREED"; audit {type:"agree", finding_id, reason, ts}
  CHALLENGE → critic_status="CHALLENGED"; push to pending_critiques;
              audit {type:"challenge", finding_id, reason, suggested_revision, ...}
  REJECT    → remove from findings.json; append to findings.archived.json;
              audit {type:"reject", finding_id, reason, ts}

``_LOCK`` serialises all file I/O within this module. ``pending_critiques`` is
shared with the investigator's InvestigatorDeps; callers performing
read-then-clear on that list must also hold ``_LOCK``.
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
from silentwitness_common.atomic_io import write_json_atomic
from silentwitness_mcp.audit.chain import append_chained_jsonl_line

_LOG = logging.getLogger(__name__)
_LOCK = threading.Lock()

_FINDINGS_JSON = "findings.json"
_ARCHIVED_JSON = "findings.archived.json"
_CRITIC_JSONL = "audit/critic.jsonl"


class CriticHandlerResult(BaseModel):
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
    writes to disk. findings.archived.json is written BEFORE findings.json so
    that if the archived write fails, the rejected finding is still present in
    findings.json (recoverable) rather than absent from both files (not
    recoverable). findings.json is only written when at least one verdict was
    routed (not on empty-verdicts calls).

    Note: callers reading or clearing ``pending_critiques`` concurrently must
    acquire ``_LOCK`` from this module to avoid a read-during-append race.
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

        # findings.json is a MIXED array — observation records (observation_id),
        # narratives, AND finding records (finding_id). Index only the findings
        # by finding_id and mutate them IN PLACE so non-finding records survive
        # write-back. A prior version keyed on a non-existent "id" field and
        # rebuilt the file from the index alone, which dropped every observation.
        findings_index: dict[str, int] = {}
        for idx, item in enumerate(raw_findings):
            if isinstance(item, dict):
                fid_key = item.get("finding_id")
                if isinstance(fid_key, str) and fid_key:
                    findings_index[fid_key] = idx

        rejected_ids: set[str] = set()

        for verdict in verdicts:
            fid = verdict.finding_id
            ts = _now_iso()

            if fid not in findings_index:
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

            finding = raw_findings[findings_index[fid]]
            if not isinstance(finding, dict):  # pragma: no cover — index holds only dicts
                continue

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

        # archived written FIRST: if this fails, findings.json still holds the rejected entry.
        if rejected_ids:
            try:
                write_json_atomic(case_dir / _ARCHIVED_JSON, archived)
            except OSError:
                _LOG.error(
                    "critic_handler: failed to persist %s; %d finding(s) NOT archived "
                    "case_dir=%s rejected_ids=%s",
                    _ARCHIVED_JSON,
                    len(rejected_ids),
                    case_dir,
                    sorted(rejected_ids),
                    exc_info=True,
                )
                raise

        if agree_count or challenge_count or rejected_ids:
            # Preserve every record (observations, narratives, non-rejected
            # findings); drop only the rejected findings (now in archived.json).
            remaining = [
                item
                for item in raw_findings
                if not (isinstance(item, dict) and item.get("finding_id") in rejected_ids)
            ]
            try:
                write_json_atomic(case_dir / _FINDINGS_JSON, remaining)
            except OSError:
                _LOG.error(
                    "critic_handler: failed to persist %s after routing %d verdict(s); "
                    "audit log has %d line(s) ahead of disk case_dir=%s",
                    _FINDINGS_JSON,
                    len(verdicts),
                    audit_lines,
                    case_dir,
                    exc_info=True,
                )
                raise

    return CriticHandlerResult(
        agree_count=agree_count,
        challenge_count=challenge_count,
        reject_count=reject_count,
        archived_finding_ids=archived_ids,
        audit_lines_written=audit_lines,
    )


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
    # Emit audit line before mutating caller's list — if emit raises, no side-effect leaks out.
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
    pending_critiques.append(verdict)


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


def _emit_line(path: Path, record: dict[str, Any]) -> None:
    # ensure_ascii=True prevents U+2028/U+2029/NEL slipping through to append_jsonl_line's
    # forbidden-character validator (json.dumps with ensure_ascii=False preserves them).
    append_chained_jsonl_line(path, json.dumps(record, ensure_ascii=True, sort_keys=True))


def _read_json_list(path: Path) -> list[Any]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"critic_handler: {path.name} is corrupt: {exc}") from exc
    except OSError as exc:
        raise OSError(f"critic_handler: cannot read {path.name}: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(
            f"critic_handler: {path.name} is not a JSON list (got {type(data).__name__})"
        )
    return data


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


__all__ = ["CriticHandlerResult", "handle_critic_verdicts"]
