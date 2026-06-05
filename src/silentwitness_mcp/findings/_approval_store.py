"""Persistence helpers for ``approve_finding``. Mirrors the
persistence / tool-body split used by sibling findings tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

import yaml

_FINDINGS_FILENAME: Final = "findings.json"
_CASE_YAML_FILENAME: Final = "CASE.yaml"


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
    Verifier reads the same file so signer + verifier derive
    identical keys."""
    path = case_dir / _CASE_YAML_FILENAME
    if not path.exists():
        return None
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    salt_hex = raw.get("salt_hex")
    if not isinstance(salt_hex, str) or not salt_hex:
        return None
    return bytes.fromhex(salt_hex)


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
    "load_case_salt",
    "locate_finding",
    "locate_interpretation",
    "locate_observation",
    "read_findings",
]
