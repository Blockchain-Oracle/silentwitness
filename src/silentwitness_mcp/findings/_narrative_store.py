"""Persistence helpers for ``record_narrative``. Mirrors the
persistence / tool-body split used by sibling findings tools — keeps
the tool body under the 400-LOC CI cap.

Schema: narratives are appended to ``findings.json`` at top level as
records with ``narrative_id`` (``N-NNN``). The case-wide N-NNN
sequence makes critic citations unambiguous.

Pivot existence reads ``audit/hypothesis.jsonl``; observation
existence reads ``findings.json``."""

from __future__ import annotations

import fcntl
import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Final

from silentwitness_common.atomic_io import write_json_atomic

_FINDINGS_FILENAME: Final = "findings.json"
_LOCK_FILENAME: Final = ".findings.lock"
_NARRATIVE_ID_PATTERN: Final = re.compile(r"^N-(\d{3,})$")
_PIVOT_ID_PATTERN: Final = re.compile(r"^P-\d{3,}$")


class NarrativeStoreError(ValueError):
    """Raised when findings.json or hypothesis.jsonl violates the
    persistence contract (wrong top-level type, malformed narrative
    entries, missing required keys). Inherits from ``ValueError`` so the
    catch in :func:`silentwitness_mcp.findings.narrative.record_narrative`
    maps it to ``AUDIT_STORE_CORRUPTED`` — same fail-closed pattern as
    sibling stores."""


@contextmanager
def _locked(case_dir: Path) -> Iterator[None]:
    """Same lockfile name observation_id / interpretation_id allocation
    use, so all four allocators serialize across processes."""
    lock_path = case_dir / _LOCK_FILENAME
    lock_path.touch(exist_ok=True)
    handle: IO[bytes] = lock_path.open("rb+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def _read_findings(case_dir: Path) -> list[Any]:
    """Returns ``list[Any]`` (not ``list[dict]``) so the per-row
    isinstance guards stay reachable at type-check time — a hand-edited
    findings.json may legitimately contain non-dict scalars."""
    path = case_dir / _FINDINGS_FILENAME
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise NarrativeStoreError(f"findings.json must be a JSON array; got {type(data).__name__}")
    return data


def existing_observation_ids(case_dir: Path) -> set[str]:
    """Set of every ``observation_id`` persisted in findings.json so the
    narrative tool can verify cited observations exist. Non-string
    observation_id raises :class:`NarrativeStoreError`."""
    findings = _read_findings(case_dir)
    ids: set[str] = set()
    for item in findings:
        if not isinstance(item, dict):
            continue
        if "observation_id" not in item:
            continue
        oid = item["observation_id"]
        if not isinstance(oid, str):
            raise NarrativeStoreError(f"observation_id must be a string; got {type(oid).__name__}")
        ids.add(oid)
    return ids


def existing_pivot_ids(hypothesis_log: Path) -> set[str]:
    """Set of every ``pivot_id`` persisted in hypothesis.jsonl. Raises
    :class:`NarrativeStoreError` if a dict row carries a non-string or
    non-matching ``pivot_id``."""
    if not hypothesis_log.exists():
        return set()
    ids: set[str] = set()
    for line in hypothesis_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            continue
        if "pivot_id" not in record:
            continue
        pid = record["pivot_id"]
        if not isinstance(pid, str):
            raise NarrativeStoreError(f"pivot_id must be a string; got {type(pid).__name__}")
        if _PIVOT_ID_PATTERN.match(pid) is None:
            raise NarrativeStoreError(f"pivot_id {pid!r} does not match P-NNN format")
        ids.add(pid)
    return ids


def _max_narrative_seq(findings: list[Any]) -> int:
    """Highest existing ``N-NNN`` sequence. Raises
    :class:`NarrativeStoreError` if any narrative entry has a non-string
    or non-matching narrative_id — silent skip risks an allocator
    collision with an invisible existing N-NNN."""
    highest = 0
    for item in findings:
        if not isinstance(item, dict):
            continue
        if "narrative_id" not in item:
            continue
        nid = item["narrative_id"]
        if not isinstance(nid, str):
            raise NarrativeStoreError(f"narrative_id must be a string; got {type(nid).__name__}")
        match = _NARRATIVE_ID_PATTERN.match(nid)
        if match is None:
            raise NarrativeStoreError(f"narrative_id {nid!r} does not match N-NNN format")
        seq = int(match.group(1))
        if seq > highest:
            highest = seq
    return highest


def allocate_narrative_id(case_dir: Path, narrative_record: dict[str, Any]) -> str:
    """Append the narrative as a top-level record in findings.json and
    return ``N-NNN``. flock-protected so the allocator serializes
    against observation_id / interpretation_id writes."""
    case_dir.mkdir(parents=True, exist_ok=True)
    with _locked(case_dir):
        findings = _read_findings(case_dir)
        next_seq = _max_narrative_seq(findings) + 1
        nid = f"N-{next_seq:03d}"
        entry = {**narrative_record, "narrative_id": nid}
        findings.append(entry)
        write_json_atomic(case_dir / _FINDINGS_FILENAME, findings)
        return nid


__all__ = [
    "NarrativeStoreError",
    "allocate_narrative_id",
    "existing_observation_ids",
    "existing_pivot_ids",
]
