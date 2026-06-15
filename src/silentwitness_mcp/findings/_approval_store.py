"""Persistence helpers for ``approve_finding``. Mirrors the
persistence / tool-body split used by sibling findings tools."""

from __future__ import annotations

import fcntl
import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import IO, Any, Final

import yaml

from silentwitness_common.atomic_io import write_json_atomic
from silentwitness_mcp.findings.corroboration import CorroborationTier, classify
from silentwitness_mcp.index.store import EvidenceIndex, IndexRecord

_LOG = logging.getLogger(__name__)

_FINDINGS_FILENAME: Final = "findings.json"
_CASE_YAML_FILENAME: Final = "CASE.yaml"
_INDEX_DB: Final = "index.db"
_LOCK_FILENAME: Final = ".findings.lock"
_FINDING_SEQ_RE: Final = re.compile(r"^F-(\d+)$")


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


def _observation_record_ids(observation_dict: dict[str, Any]) -> set[int]:
    """Extract integer record_ids from an observation's cited_spans.

    Robust to absent / malformed schema — corroboration is advisory, so a malformed
    cited_spans field yields an empty set (which classifies as UNVERIFIED) instead
    of crashing the materialise step."""
    out: set[int] = set()
    for span in observation_dict.get("cited_spans", []) or []:
        if not isinstance(span, dict):
            continue
        rid = span.get("record_id")
        if isinstance(rid, int):
            out.add(rid)
    return out


def _resolve_cited_records(case_dir: Path, record_ids: set[int]) -> list[IndexRecord]:
    """Fetch IndexRecords for ``record_ids`` from the case index.

    Mirrors ``_tool_impls_findings._cited_records`` — duplicating the small helper
    rather than importing it avoids a circular dep (``_tool_impls_findings`` already
    imports from this module via the approval-pipeline path). Returns ``[]`` if the
    index does not exist yet (e.g. a case approved before any indexing ran) — the
    classifier treats the empty set as UNVERIFIED, which is the correct semantics."""
    index_path = case_dir / _INDEX_DB
    if not record_ids or not index_path.exists():
        return []
    out: list[IndexRecord] = []
    with EvidenceIndex(index_path) as idx:
        for rid in record_ids:
            rec = idx.get(rid)
            if rec is not None:
                out.append(rec)
    return out


def _classify_observation(
    case_dir: Path, observation_dict: dict[str, Any]
) -> tuple[CorroborationTier, list[str]]:
    """Resolve the observation's cited records and classify their corroboration."""
    record_ids = _observation_record_ids(observation_dict)
    records = _resolve_cited_records(case_dir, record_ids)
    tier, categories = classify(records)
    return tier, sorted(categories)


def _max_finding_seq(findings: list[Any]) -> int:
    mx = 0
    for item in findings:
        if isinstance(item, dict):
            match = _FINDING_SEQ_RE.match(str(item.get("finding_id", "")))
            if match:
                mx = max(mx, int(match.group(1)))
    return mx


def materialize_findings(case_dir: Path) -> list[str]:
    """Create DRAFT Finding records from staged observation+interpretation pairs.

    ``record_observation`` stages OBSERVATION records but never materializes the
    Finding records (``finding_id`` / ``status``) that review / approve / report
    consume — so review shows an empty table and report.md stays empty. This
    bridges that seam: for each observation with >=1 interpretation and no
    existing Finding pointing at it, append
    ``{finding_id, observation_id, interpretation_id (latest), status: "DRAFT",
    staged_at}``. Idempotent — re-running adds nothing new. Returns the
    ``finding_id``s created on this call."""
    created: list[str] = []
    with findings_lock(case_dir):
        findings = read_findings(case_dir)
        covered = {
            item.get("observation_id")
            for item in findings
            if isinstance(item, dict) and item.get("finding_id") and item.get("observation_id")
        }
        seq = _max_finding_seq(findings)
        for item in list(findings):
            if not isinstance(item, dict):
                continue
            oid = item.get("observation_id")
            if not isinstance(oid, str) or oid in covered:
                continue
            interps = [i for i in item.get("interpretations", []) or [] if isinstance(i, dict)]
            iid = interps[-1].get("interpretation_id") if interps else None
            if not isinstance(iid, str):
                # An observation WITH interpretations but no usable id is a schema
                # drift worth surfacing (it would otherwise vanish from review with
                # no signal). Zero interpretations is legitimate "not yet ready".
                if interps:
                    _LOG.warning(
                        "materialize_findings: observation %s has interpretations but the "
                        "latest lacks a string interpretation_id; no finding created",
                        oid,
                    )
                continue
            seq += 1
            fid = f"F-{seq:03d}"
            # Phase 6a: advisory corroboration tier from cited-record category diversity.
            # Computed once at materialise time so the tier reflects the evidence the
            # observation was actually staged against; if the index later gains rows,
            # the tier does NOT auto-upgrade (the agent must re-cite to lift it).
            tier, categories = _classify_observation(case_dir, item)
            findings.append(
                {
                    "finding_id": fid,
                    "observation_id": oid,
                    "interpretation_id": iid,
                    "status": "DRAFT",
                    "staged_at": datetime.now(UTC).isoformat(),
                    "corroboration_tier": tier.value,
                    "corroboration_categories": categories,
                }
            )
            covered.add(oid)
            created.append(fid)
        if created:
            write_json_atomic(case_dir / _FINDINGS_FILENAME, findings)
    return created


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
    "materialize_findings",
    "read_findings",
]
