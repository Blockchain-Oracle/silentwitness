"""Observation-ID sequencer (architecture §4.2 ``record_observation`` row).

IDs are zero-padded ``O-NNN`` (width auto-widens past 999 so the prefix
sort stays stable). The sequencer resumes across server restarts by
reading the maximum existing ``observation_id`` from
``cases/<case_id>/findings.json`` — there is no separate sequence-state
file (architecture §5.2: findings.json is the single source of truth
for finding state).

Race-safety: ``fcntl.flock`` defends against multi-process writers (e.g.
concurrent stdio + Streamable HTTP transport instances both touching the
same case dir). In-process serialization comes from the synchronous call
site — Python's GIL + the kernel-level flock cover the cross-process
case; an async refactor would need to add an ``asyncio.Lock`` here.
"""

from __future__ import annotations

import fcntl
import json
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Final

from silentwitness_common.atomic_io import write_json_atomic

_FINDINGS_FILENAME: Final = "findings.json"
_LOCK_FILENAME: Final = ".findings.lock"
_OBSERVATION_ID_PATTERN: Final = re.compile(r"^O-(\d+)$")


@contextmanager
def _locked(case_dir: Path) -> Iterator[None]:
    """Exclusive flock on the findings lock file. Created if absent."""
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


def _read_findings(case_dir: Path) -> list[dict[str, object]]:
    path = case_dir / _FINDINGS_FILENAME
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError(f"findings.json must be a JSON array; got {type(data).__name__}")
    return data


def _max_observation_seq(findings: list[dict[str, object]]) -> int:
    highest = 0
    for item in findings:
        oid = item.get("observation_id")
        if not isinstance(oid, str):
            continue
        match = _OBSERVATION_ID_PATTERN.match(oid)
        if match is None:
            continue
        seq = int(match.group(1))
        if seq > highest:
            highest = seq
    return highest


def allocate_observation_id(case_dir: Path, observation_record: Mapping[str, object]) -> str:
    """Allocate the next ``O-NNN`` AND atomically append the observation
    record to ``findings.json`` under the lock. One operation so the ID
    and the persisted record cannot disagree."""
    case_dir.mkdir(parents=True, exist_ok=True)
    with _locked(case_dir):
        findings = _read_findings(case_dir)
        next_seq = _max_observation_seq(findings) + 1
        oid = f"O-{next_seq:03d}"
        observation_record = {**observation_record, "observation_id": oid}
        findings.append(observation_record)
        write_json_atomic(case_dir / _FINDINGS_FILENAME, findings)
        return oid


__all__ = ["allocate_observation_id"]
