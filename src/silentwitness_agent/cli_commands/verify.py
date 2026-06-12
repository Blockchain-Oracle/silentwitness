"""Examiner verify command — HMAC ledger reconciliation (architecture §4.9)."""

from __future__ import annotations

import getpass
import sys
from datetime import UTC, datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from silentwitness_common.types import Confidence
from silentwitness_mcp.audit.ledger import (
    HMACLedger,
    InterpretationParts,
    LedgerComposer,
    LedgerCorruptionError,
    LedgerSecurityError,
    ObservationParts,
)
from silentwitness_mcp.findings._approval_store import (
    CaseSaltMalformedError,
    load_case_salt,
    locate_interpretation,
    locate_observation,
    read_findings,
)

_DEFAULT_LEDGER_DIR = Path("/var/lib/silentwitness/verification")
_PBKDF2_ITER = 600_000

# Reconciliation outcome vocabulary — architecture §4.9, verbatim.
_VERIFIED = "VERIFIED"
_DESCRIPTION_MISMATCH = "DESCRIPTION_MISMATCH"
_APPROVED_NO_VERIFICATION = "APPROVED_NO_VERIFICATION"
_VERIFICATION_NO_FINDING = "VERIFICATION_NO_FINDING"


class _NoTTYError(Exception):
    pass


def _read_password(prompt: str = "examiner password: ") -> str:
    # _SILENTWITNESS_TEST_PASSWORD: test-only bypass (same contract as approve).
    import os

    if "pytest" in sys.modules and (tp := os.environ.get("_SILENTWITNESS_TEST_PASSWORD")):
        return tp
    if not sys.stdin.isatty():
        raise _NoTTYError()
    return getpass.getpass(prompt)


def _build_content_bytes(entry_type: str, findings: list[object], item_id: str) -> bytes | None:
    """Reconstruct the substantive bytes for an entry per architecture §4.9."""
    if entry_type == "finding":
        # Locate the finding, then its observation and interpretation.
        from silentwitness_mcp.findings._approval_store import locate_finding

        loc = locate_finding(findings, item_id)
        if loc is None:
            return None
        _, finding = loc
        obs = locate_observation(findings, finding.get("observation_id", ""))
        interp = locate_interpretation(findings, finding.get("interpretation_id", ""))
        if obs is None or interp is None:
            return None
        obs_parts = ObservationParts(
            text=obs.get("text", ""),
            audit_ids=tuple(obs.get("audit_ids", []) or []),
        )
        interp_parts = InterpretationParts(
            observation_id=interp.get("observation_id") or obs.get("observation_id", ""),
            text=interp.get("text", ""),
            confidence=Confidence(interp.get("confidence", "LOW")),
        )
        return LedgerComposer.finding(obs_parts, interp_parts)
    if entry_type == "observation":
        obs = locate_observation(findings, item_id)
        if obs is None:
            return None
        obs_parts = ObservationParts(
            text=obs.get("text", ""),
            audit_ids=tuple(obs.get("audit_ids", []) or []),
        )
        return LedgerComposer.observation(obs_parts)
    if entry_type == "interpretation":
        interp = locate_interpretation(findings, item_id)
        if interp is None:
            return None
        interp_parts = InterpretationParts(
            observation_id=interp.get("observation_id", ""),
            text=interp.get("text", ""),
            confidence=Confidence(interp.get("confidence", "LOW")),
        )
        return LedgerComposer.interpretation(interp_parts)
    return None


def run(
    case_dir: Path,
    case_id: str,
    *,
    ledger_dir: Path,
    strict: bool,
    no_color: bool,
) -> int:
    console = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)

    # Load salt — distinguish absent from malformed.
    try:
        salt = load_case_salt(case_dir)
    except CaseSaltMalformedError as exc:
        err.print(f"[red]✗[/red] CASE_SALT_MALFORMED: {exc}", highlight=False)
        return 2
    if salt is None:
        err.print(
            f"[red]✗[/red] CASE_SALT_MISSING: no salt_hex in {case_dir / 'CASE.yaml'}",
            highlight=False,
        )
        return 2

    # Load ledger — security posture check first.
    try:
        ledger = HMACLedger(ledger_dir=ledger_dir, case_id=case_id)
    except LedgerSecurityError as exc:
        err.print(f"[red]✗[/red] LEDGER_DIR_PERMISSIONS_WEAK: {exc}", highlight=False)
        return 2
    except OSError as exc:
        err.print(f"[red]✗[/red] ledger error: {exc}", highlight=False)
        return 2

    try:
        entries = ledger.read_all()
    except LedgerCorruptionError as exc:
        err.print(f"[red]✗[/red] LEDGER_CORRUPT: {exc}", highlight=False)
        return 2

    if not entries:
        console.print(
            "[yellow]⚠[/yellow] no entries to verify (no findings approved yet)",
            highlight=False,
        )
        return 0

    # Load findings.
    try:
        findings = read_findings(case_dir)
    except Exception as exc:
        err.print(f"[red]✗[/red] findings.json parse error: {exc}", highlight=False)
        return 2

    # Prompt for password — same TTY contract as approve.
    try:
        password = _read_password()
    except _NoTTYError:
        err.print(
            f"[red]✗[/red] verify requires a TTY (use: silentwitness verify {case_id} < /dev/tty)",
            highlight=False,
        )
        return 2
    except KeyboardInterrupt:
        console.print(highlight=False)
        return 130

    # Derive HMAC key into a mutable bytearray so we can zero it after use.
    key_buf = bytearray(HMACLedger.derive_key(password, salt, _PBKDF2_ITER))

    rows: list[tuple[str, str, str, str]] = []  # (item_id, item_type, outcome, ledger_line)
    try:
        # Forward pass: every ledger entry → verify against live findings text.
        for line_no, entry in enumerate(entries, start=1):
            content_bytes = _build_content_bytes(entry.item_type.value, findings, entry.item_id)
            if content_bytes is None:
                rows.append(
                    (entry.item_id, entry.item_type.value, _VERIFICATION_NO_FINDING, str(line_no))
                )
                continue
            ok = ledger.verify_entry(bytes(key_buf), entry, content_bytes)
            outcome = _VERIFIED if ok else _DESCRIPTION_MISMATCH
            rows.append((entry.item_id, entry.item_type.value, outcome, str(line_no)))

        # Reverse pass: every APPROVED finding must have a ledger entry.
        ledger_ids = {e.item_id for e in entries}
        for item in findings:
            if not isinstance(item, dict):
                continue
            if item.get("status") != "APPROVED":
                continue
            fid = item.get("finding_id", "")
            if fid and fid not in ledger_ids:
                rows.append((fid, "finding", _APPROVED_NO_VERIFICATION, "-"))
    finally:
        HMACLedger.zero_key(key_buf)

    # Render per-entry table.
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("item_id")
    table.add_column("item_type")
    table.add_column("outcome")
    table.add_column("ledger_line")
    for item_id, item_type, outcome, line_ref in rows:
        style = "green" if outcome == _VERIFIED else "red"
        table.add_row(item_id, item_type, f"[{style}]{outcome}[/{style}]", line_ref)
    console.print(table)

    mismatches = [r for r in rows if r[2] != _VERIFIED]
    n_verified = len(rows) - len(mismatches)
    n_total = len(rows)

    if not mismatches:
        first_ts = min(e.ts for e in entries)
        last_ts = max(e.ts for e in entries)

        def _fmt(dt: datetime) -> str:
            return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        console.print(
            f"[green]✓[/green] ledger intact — {n_total} entries verified\n"
            f"       PBKDF2-SHA256, 600,000 iter\n"
            f"       window: {_fmt(first_ts)} → {_fmt(last_ts)}",
            highlight=False,
        )
        return 0

    # Check if ALL entries failed — likely wrong password.
    if all(r[2] == _DESCRIPTION_MISMATCH for r in rows if r[2] != _APPROVED_NO_VERIFICATION):
        console.print(
            "[yellow]⚠[/yellow] all entries failed — most likely wrong password, not tamper."
            " Re-run.",
            highlight=False,
        )

    console.print(
        f"[red]✗[/red] verification FAILED — {n_verified}/{n_total} entries reconciled "
        f"({len(mismatches)} mismatches)",
        highlight=False,
    )
    return 3 if strict else 1
