"""Findings-store helpers for ``record_interpretation``.

Mirrors the split observation.py uses with _id_gen.py: the allocator
runs under a shared ``.findings.lock`` so multi-process writers
(concurrent stdio + Streamable HTTP) serialize against each other,
and observation_id + interpretation_id allocation contend on the same
lock so the two cannot interleave in a way that corrupts findings.json.
"""

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
_INTERPRETATION_ID_PATTERN: Final = re.compile(r"^I-(\d+)$")


@contextmanager
def _locked(case_dir: Path) -> Iterator[None]:
    """Same lockfile name observation_id allocation uses."""
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


def _read_findings(case_dir: Path) -> list[dict[str, Any]]:
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


def _max_interpretation_seq(findings: list[dict[str, Any]]) -> int:
    """Global ``I-NNN`` sequence across ALL observations — case-wide
    unambiguous IDs for critic citations."""
    highest = 0
    for obs in findings:
        for item in obs.get("interpretations", []) or []:
            if not isinstance(item, dict):
                continue
            iid = item.get("interpretation_id")
            if not isinstance(iid, str):
                continue
            match = _INTERPRETATION_ID_PATTERN.match(iid)
            if match is None:
                continue
            seq = int(match.group(1))
            if seq > highest:
                highest = seq
    return highest


def allocate_interpretation_id(
    case_dir: Path,
    observation_id: str,
    interpretation_record: dict[str, Any],
) -> str | None:
    """Append the interpretation under its observation's record and
    return ``I-NNN``. Returns ``None`` if the observation_id is absent
    from findings.json — the caller maps that to OBSERVATION_NOT_FOUND."""
    case_dir.mkdir(parents=True, exist_ok=True)
    with _locked(case_dir):
        findings = _read_findings(case_dir)
        target_idx = next(
            (i for i, item in enumerate(findings) if item.get("observation_id") == observation_id),
            None,
        )
        if target_idx is None:
            return None
        target = findings[target_idx]
        existing = target.get("interpretations", [])
        if not isinstance(existing, list):
            raise ValueError(
                f"findings.json[{target_idx}].interpretations must be a list; "
                f"got {type(existing).__name__}"
            )
        next_seq = _max_interpretation_seq(findings) + 1
        iid = f"I-{next_seq:03d}"
        entry = {**interpretation_record, "interpretation_id": iid}
        existing.append(entry)
        target["interpretations"] = existing
        findings[target_idx] = target
        write_json_atomic(case_dir / _FINDINGS_FILENAME, findings)
        return iid


__all__ = ["allocate_interpretation_id"]
