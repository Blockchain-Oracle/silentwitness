"""Persistence helpers for ``approve_finding``. Mirrors the
persistence / tool-body split used by sibling findings tools."""

from __future__ import annotations

import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Final

import yaml

_FINDINGS_FILENAME: Final = "findings.json"
_CASE_YAML_FILENAME: Final = "CASE.yaml"
_LOCK_FILENAME: Final = ".findings.lock"


class CaseSaltMalformedError(ValueError):
    """Raised when ``CASE.yaml`` exists but its content is broken —
    bad YAML, salt_hex not a hex string, etc. Caller maps to the
    dedicated CASE_SALT_MALFORMED reason instead of misattributing the
    corruption to ``findings.json``."""


@contextmanager
def findings_lock(case_dir: Path) -> Iterator[None]:
    """Exclusive flock around the read-modify-write of findings.json.
    Same lockfile name observation_id / interpretation_id allocators
    use, so all writers serialize across processes."""
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


def read_findings(case_dir: Path) -> list[Any]:
    """Returns ``list[Any]`` (not ``list[dict]``) so the per-row
    isinstance guards in the locators stay reachable at type-check time."""
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


def load_case_salt(case_dir: Path) -> bytes | None:
    """Read ``CASE.yaml`` ``salt_hex``; ``None`` if file or key absent.
    Verifier reads the same file so signer + verifier derive identical
    keys. Raises :class:`CaseSaltMalformedError` if the file exists but
    is broken (YAML error / non-hex salt_hex) so the caller can
    distinguish "no salt registered yet" from "salt registration
    corrupted" — finding the wrong file at debug time is a real bug."""
    path = case_dir / _CASE_YAML_FILENAME
    if not path.exists():
        return None
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CaseSaltMalformedError(f"CASE.yaml is not valid YAML: {exc}") from exc
    raw = loaded or {}
    if not isinstance(raw, dict):
        return None
    salt_hex = raw.get("salt_hex")
    if not isinstance(salt_hex, str) or not salt_hex:
        return None
    try:
        return bytes.fromhex(salt_hex)
    except ValueError as exc:
        raise CaseSaltMalformedError(f"CASE.yaml salt_hex is not valid hex: {exc}") from exc


def locate_finding(findings: list[Any], finding_id: str) -> tuple[int, dict[str, Any]] | None:
    for idx, item in enumerate(findings):
        if isinstance(item, dict) and item.get("finding_id") == finding_id:
            return (idx, item)
    return None


def locate_observation(findings: list[Any], observation_id: str) -> dict[str, Any] | None:
    for item in findings:
        if isinstance(item, dict) and item.get("observation_id") == observation_id:
            return item
    return None


def locate_interpretation(findings: list[Any], interpretation_id: str) -> dict[str, Any] | None:
    """Interpretations live nested under each observation's record."""
    for item in findings:
        if not isinstance(item, dict):
            continue
        for interp in item.get("interpretations", []) or []:
            if isinstance(interp, dict) and interp.get("interpretation_id") == interpretation_id:
                return interp
    return None


__all__ = [
    "CaseSaltMalformedError",
    "findings_lock",
    "load_case_salt",
    "locate_finding",
    "locate_interpretation",
    "locate_observation",
    "read_findings",
]
