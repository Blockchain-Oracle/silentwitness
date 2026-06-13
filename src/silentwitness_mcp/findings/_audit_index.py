"""Build the in-memory audit index the citation gate consumes.

``record_observation`` validates each cited span against the SHA256-pinned tool
output by looking the span's ``audit_id`` up in a ``Mapping[str, AuditEntry]``
and re-reading ``entry.stdout_path``. That mapping must carry FULL
:class:`AuditEntry` objects (``stdout_path`` + ``result_sha256`` + ``params``),
not the lightweight ``AuditEntryRef`` the agent-side report indexer produces.

The index is rebuilt per ``record_observation`` call: the audit log is
append-only during a run, so a cached index would miss freshly-emitted tool
rows. Lines that are not valid ``AuditEntry`` JSON (e.g. ``agent.jsonl`` hook
events written by the CLI side) are skipped — they share the ``audit/``
directory but are a different shape.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from silentwitness_common.types import AuditEntry

_LOG = logging.getLogger(__name__)

# Backends that legitimately hold non-AuditEntry rows: hook events (agent),
# hypothesis transitions, sanitizer strip events, critic verdicts. A parse
# failure there is expected and silent; a parse failure in any OTHER backend
# (evidence/network/findings/vol/read_output…) signals a corrupt or truncated
# audit row, which we log so a citation that silently becomes AUDIT_ID_NOT_FOUND
# is at least greppable.
_NON_AUDIT_BACKENDS = frozenset({"agent", "hypothesis", "sanitizer", "critic"})


def build_audit_index(case_dir: Path) -> dict[str, AuditEntry]:
    """Parse ``case_dir/audit/*.jsonl`` into ``{audit_id: AuditEntry}``."""
    index: dict[str, AuditEntry] = {}
    audit_dir = case_dir / "audit"
    if not audit_dir.is_dir():
        return index
    for jsonl in sorted(audit_dir.glob("*.jsonl")):
        try:
            lines = jsonl.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        expects_audit = jsonl.stem not in _NON_AUDIT_BACKENDS
        for raw in lines:
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = AuditEntry.model_validate_json(raw)
            except (ValidationError, ValueError):
                if expects_audit:
                    _LOG.warning(
                        "build_audit_index: unparseable audit row in %s (possible "
                        "corruption): %.120s",
                        jsonl.name,
                        raw,
                    )
                continue
            index[entry.audit_id] = entry
    return index


__all__ = ["build_audit_index"]
