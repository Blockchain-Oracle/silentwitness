"""Volatility 3 LSA-secret tool body — physically isolated from
:mod:`memory` because credential material is the highest-review-
priority code path in the memory family (architecture §4.2 + §4.6,
PRD FR #5).

A row from Vol3's JSON renderer carries ``Key`` (secret name like
``$MACHINE.ACC`` / ``DefaultPassword`` / ``_SC_<service>`` /
``DPAPI_SYSTEM``), ``Hex`` (verbatim bytes), and a best-effort
``Secret`` printable rendering. We re-derive ``Secret`` from ``Hex``
ourselves so a Vol3 renderer change can't silently feed an unchecked
string into the typed model — the entity gate cites the Hex bytes."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Final

from silentwitness_common.types import ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._memory_models import LsaDumpOutput, LsaSecretEntry
from silentwitness_mcp.tools._vol_common import DEFAULT_TIMEOUT_S
from silentwitness_mcp.tools._vol_pipeline import _run_wrapper

# Vol3 ≥2.29 path; the old ``windows.lsadump.Lsadump`` is removed.
_LSADUMP_PLUGIN: Final = "windows.registry.lsadump.Lsadump"

_DISCIPLINE_REMINDER: Final = (
    "credential material — record_observation against this output should "
    "be reviewed at Restricted classification and HMAC-approved before "
    "report inclusion"
)

# UTF-16LE decode acceptance band: the bytes are printable iff every
# decoded char is either ASCII printable or a Unicode Letter/Mark/
# Number/Punctuation/Symbol category char. Refuse C-class (control),
# surrogates, and unassigned — silently mangling these into a string
# field would corrupt the audit trail (Hex remains authoritative).
_ACCEPTED_UNICODE_CATEGORIES: Final = frozenset({"L", "M", "N", "P", "S", "Z"})


def _is_printable_unicode(text: str) -> bool:
    """Acceptance check for the convenience-only Secret field."""
    if not text:
        return False
    return all(unicodedata.category(c)[0] in _ACCEPTED_UNICODE_CATEGORIES for c in text)


def _decode_secret(hex_str: str) -> str | None:
    """Best-effort UTF-16LE decode of the verbatim hex bytes. ``None``
    when the result is empty or contains any non-printable codepoint —
    the entity gate cites ``Hex``, so a half-decoded ``Secret`` would
    be worse than no ``Secret``."""
    try:
        raw = bytes.fromhex(hex_str.replace(" ", "").replace("\n", ""))
    except ValueError:
        return None
    # LSA secrets are UTF-16LE Unicode strings; null-terminate trim.
    try:
        text = raw.decode("utf-16-le").rstrip("\x00")
    except UnicodeDecodeError:
        return None
    return text if _is_printable_unicode(text) else None


# Closed-set of keys Vol3's lsadump renderer is allowed to emit. Any
# additional key is schema drift on a credential-material surface
# and MUST fail closed — silently dropping a column we don't recognise
# would let the audit trail elide a field the entity gate may need.
_LSADUMP_EXPECTED_KEYS: Final = frozenset({"Key", "Hex", "Secret"})


def _parse_lsadump(raw: bytes) -> LsaDumpOutput:
    """Re-derive ``Secret`` from ``Hex`` locally (Vol3's renderer-side
    printable is unverified). Reject any Vol3 row with unknown
    columns — credential-material audit cannot silently elide drift."""
    rows = json.loads(raw.decode("utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"lsadump JSON must be a list, got {type(rows).__name__}")
    entries: list[LsaSecretEntry] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"lsadump row must be a dict, got {type(row).__name__}")
        unknown = set(row) - _LSADUMP_EXPECTED_KEYS
        if unknown:
            raise ValueError(f"lsadump row has unknown column(s): {sorted(unknown)}")
        hex_value = row.get("Hex")
        cleaned = {"Key": row.get("Key"), "Hex": hex_value}
        if isinstance(hex_value, str):
            cleaned["Secret"] = _decode_secret(hex_value)
        entries.append(LsaSecretEntry.model_validate(cleaned))
    return LsaDumpOutput(entries=tuple(entries))


async def vol_lsadump(
    evidence_path: Path,
    *,
    case_dir: Path,
    evidence_registry: EvidenceRegistry,
    audit_logger: AuditLogger,
    model_used: str,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> ToolResponse[LsaDumpOutput]:
    """Decrypted LSA secrets from the in-memory SYSTEM + SECURITY
    hives. Carries a non-empty ``discipline_reminder`` — the only
    vol_* tool that does so — to seed Restricted classification on
    any observation built from this output."""
    return await _run_wrapper(
        tool_name="vol_lsadump",
        plugin_name=_LSADUMP_PLUGIN,
        caveat_key="lsadump",
        output_cls=LsaDumpOutput,
        parse_rows=_parse_lsadump,
        evidence_path=evidence_path,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
        timeout_s=timeout_s,
        discipline_reminder=_DISCIPLINE_REMINDER,
    )


__all__ = ["vol_lsadump"]
