"""Volatility 3 LSA-secret tool body.

Credential material — record_observation against this output should be
reviewed at Restricted classification and HMAC-approved before report
inclusion (see :data:`_DISCIPLINE_REMINDER`). The wrapper lives outside
:mod:`tools.memory` for two reasons: (1) the 400-LOC CI gate would
otherwise force a split anyway (:mod:`tools.memory` is already in the
high 300s with the rest of the memory family); (2) the Restricted-
classification surface warrants its own review boundary. Future
credential-material wrappers (vol_hashdump, vol_cachedump, …) should
land here too — at that point this module's name may want to evolve
to ``memory_restricted.py`` to match its actual scope.

A row from Vol3's JSON renderer carries ``Key`` (secret name like
``$MACHINE.ACC`` / ``DefaultPassword`` / ``_SC_<service>`` /
``DPAPI_SYSTEM``), ``Hex`` (verbatim bytes), and a best-effort
``Secret`` printable rendering. We re-derive ``Secret`` from ``Hex``
ourselves so a Vol3 renderer change can't silently feed an unchecked
string into the typed model — the entity gate cites the Hex bytes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from silentwitness_common.types import ToolResponse
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._lsa_models import LsaDumpOutput, LsaSecretEntry
from silentwitness_mcp.tools._lsa_secret_decode import decode_secret
from silentwitness_mcp.tools._vol_common import DEFAULT_TIMEOUT_S
from silentwitness_mcp.tools._vol_pipeline import _run_wrapper

# Vol3 ≥2.29 path; the old ``windows.lsadump.Lsadump`` is removed.
_LSADUMP_PLUGIN: Final = "windows.registry.lsadump.Lsadump"

_DISCIPLINE_REMINDER: Final = (
    "credential material — record_observation against this output should "
    "be reviewed at Restricted classification and HMAC-approved before "
    "report inclusion"
)

# Closed-set of keys Vol3's lsadump renderer is allowed to emit. Any
# additional key is schema drift on a credential-material surface
# and MUST fail closed. NOTE: this guard is NOT redundant with the
# model's ``extra="forbid"`` — the parser reconstructs ``cleaned``
# from a closed key list before calling ``model_validate``, so an
# extra wire-schema key would be silently discarded if this check
# were removed. Both layers are load-bearing.
_LSADUMP_EXPECTED_KEYS: Final = frozenset({"Key", "Hex", "Secret"})


def _parse_lsadump(raw: bytes) -> LsaDumpOutput:
    """Re-derive ``secret`` from ``Hex`` locally (Vol3's renderer-side
    printable is unverified). Reject any Vol3 row with unknown
    columns OR a missing/non-string ``Hex`` — credential-material
    audit cannot silently elide drift. Malformed-hex / bad-UTF-16LE
    bytes raise ``ValueError`` (via :func:`decode_secret`) and
    surface as ``OUTPUT_PARSE_FAILED`` at the wrapper boundary, NOT
    as a silent ``secret=None`` indistinguishable from the legitimate
    binary-non-printable case."""
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
        if not isinstance(hex_value, str):
            raise ValueError(
                f"lsadump row missing or non-string Hex (Key={row.get('Key')!r}, "
                f"Hex type={type(hex_value).__name__})"
            )
        key = row.get("Key")
        # Pass key= so binary-key allowlist short-circuits Secret=None
        # for host-managed random bytes (NTLM hashes / AES key
        # material / DPAPI seeds), even when the bytes incidentally
        # decode to a printable Unicode glyph string.
        cleaned: dict[str, Any] = {
            "Key": key,
            "Hex": hex_value,
            "Secret": decode_secret(hex_value, key=key if isinstance(key, str) else None),
        }
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
    hives. Carries a non-empty ``discipline_reminder`` to seed
    Restricted classification on any observation built from this
    output — propagates through both success and refuse envelopes
    so a refused run is still tagged with its sensitivity class."""
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
