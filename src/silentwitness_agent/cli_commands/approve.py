"""Examiner approve command — password-gated HMAC ledger write."""

from __future__ import annotations

import getpass
import hashlib
import hmac as _hmac
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import SecretStr
from rich.console import Console

from silentwitness_agent.cli_commands.review import (
    _find_interp,
    _find_obs,
    _print_block,
)
from silentwitness_common.atomic_io import write_json_atomic
from silentwitness_mcp.audit.chained_jsonl import append_chained_jsonl
from silentwitness_mcp.audit.ledger import HMACLedger, LedgerCorruptionError, LedgerSecurityError
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._approval_store import (
    CaseSaltMalformedError,
    findings_lock,
    load_case_salt,
    locate_finding,
    read_findings,
)
from silentwitness_mcp.findings.approval import (
    ApproveInput,
    ApproveRejectReason,
    approve_finding,
)

_LOG = logging.getLogger(__name__)

_DEFAULT_LEDGER_DIR = Path("/var/lib/silentwitness/verification")
_MAX_ATTEMPTS = 3
_PBKDF2_ITER = 600_000


class _NoTTYError(Exception):
    pass


class _VerifierCorruptError(Exception):
    """CASE.yaml has verifier fields that exist but are unreadable or malformed."""


def _read_password(prompt: str = "examiner password: ") -> str:
    # _SILENTWITNESS_TEST_PASSWORD: test-only bypass for TTY requirement.
    # Only active when pytest is loaded — never in production.
    if "pytest" in sys.modules and (tp := os.environ.get("_SILENTWITNESS_TEST_PASSWORD")):
        return tp
    if not sys.stdin.isatty():
        raise _NoTTYError()
    return getpass.getpass(prompt)


def _load_verifier(case_dir: Path) -> tuple[bytes, bytes] | None:
    """Return (verifier_salt, verifier_hash) from CASE.yaml, or None if not enrolled.

    Raises _VerifierCorruptError when fields exist but are unreadable or malformed —
    mirrors the load_case_salt discipline: absent != corrupt.
    """
    path = case_dir / "CASE.yaml"
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise _VerifierCorruptError(f"CASE.yaml is not valid YAML: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise _VerifierCorruptError(f"CASE.yaml unreadable: {exc}") from exc
    if not isinstance(data, dict):
        return None
    vs = data.get("verifier_salt_hex")
    vh = data.get("verifier_hex")
    if vs is None and vh is None:
        return None  # verifier never enrolled
    if not (isinstance(vs, str) and isinstance(vh, str)):
        raise _VerifierCorruptError(
            f"CASE.yaml has partial or non-string verifier fields: "
            f"verifier_salt_hex={vs!r}, verifier_hex={vh!r}"
        )
    try:
        return bytes.fromhex(vs), bytes.fromhex(vh)
    except ValueError as exc:
        raise _VerifierCorruptError(
            f"CASE.yaml verifier hex fields are not valid hex: {exc}"
        ) from exc


def _check_verifier(password: str, case_dir: Path) -> bool | None:
    """None = no verifier stored (proceed); True/False = match result."""
    entry = _load_verifier(case_dir)
    if entry is None:
        return None
    v_salt, v_hash = entry
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), v_salt, _PBKDF2_ITER)
    return _hmac.compare_digest(derived, v_hash)


def _write_cli_audit(
    cli_log: Path,
    finding_id: str,
    case_id: str,
    examiner: str,
    outcome: str,
) -> None:
    cli_log.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(UTC).isoformat(),
        "tool": "cli.approve",
        "finding_id": finding_id,
        "case_id": case_id,
        "examiner": examiner,
        "outcome": outcome,
    }
    try:
        append_chained_jsonl(cli_log, entry)
    except (OSError, ValueError) as exc:
        # cli.jsonl is secondary; the tamper-evident record is the HMACLedger entry.
        Console(stderr=True).print(
            f"[yellow]![/yellow] cli audit write failed ({type(exc).__name__}: {exc}); "
            "approval outcome is unaffected",
            highlight=False,
        )


def _ledger_info(ledger_dir: Path, case_id: str) -> tuple[int, str]:
    """Return (entry count, hmac abbreviation) after a successful approve_finding append.

    Precondition: called after approve_finding has already appended the entry.
    Re-raises LedgerCorruptionError — tamper evidence must not be silenced.
    """
    try:
        ledger = HMACLedger(ledger_dir=ledger_dir, case_id=case_id)
        entries = ledger.read_all()
        if not entries:
            return 0, "????"
        last = entries[-1]
        hmac_short = last.hmac[:4] + "..." + last.hmac[-4:]
        return len(entries), hmac_short
    except LedgerCorruptionError:
        raise
    except Exception:
        return 0, "????"


def _render_report(case_dir: Path, examiner: str, *, err: Console) -> bool:
    """Compose report.md from APPROVED findings (replaces the old deferral).

    ``ReportWriter.render()`` reads findings.json, partitions APPROVED Findings,
    joins each to its observation/interpretation, and composes all sections via
    the ``compose_*`` functions. Best-effort: a render failure must not undo the
    committed approval (the HMAC ledger is authoritative). Returns True on a
    successful render so the caller can report honestly."""
    try:
        from silentwitness_agent.report.template import parse_frontmatter
        from silentwitness_agent.report.writer import ReportWriter
        from silentwitness_common.version import __version__ as sw_version

        model_used = "unknown"
        report_path = case_dir / "report.md"
        if report_path.exists():
            try:
                frontmatter, _ = parse_frontmatter(report_path.read_text(encoding="utf-8"))
                model_used = frontmatter.model_used or model_used
            except (ValueError, OSError):
                pass
        ReportWriter(
            case_dir,
            examiner=examiner,
            model_used=model_used,
            silentwitness_version=sw_version,
        ).render()
        return True
    except Exception as exc:
        _LOG.error("approve: report.md render failed after approval", exc_info=True)
        err.print(
            f"[yellow]![/yellow] report.md render skipped ({type(exc).__name__}: {exc}); "
            "approval is committed to the ledger — re-render via `export`",
            highlight=False,
        )
        return False


def run(
    case_dir: Path,
    case_id: str,
    finding_id: str,
    *,
    ledger_dir: Path,
    note: str | None,
    no_color: bool,
    examiner: str,
) -> int:
    console = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)
    cli_log = case_dir / "audit" / "cli.jsonl"

    # Pre-checks before password prompt: salt presence/malformed, ledger dir
    # permissions, findings.json parse, finding existence, already-approved guard.
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

    try:
        HMACLedger(ledger_dir=ledger_dir, case_id=case_id)
    except LedgerSecurityError as exc:
        err.print(f"[red]✗[/red] LEDGER_DIR_PERMISSIONS_WEAK: {exc}", highlight=False)
        return 2
    except OSError as exc:
        err.print(f"[red]✗[/red] ledger error: {exc}", highlight=False)
        return 2

    try:
        findings = read_findings(case_dir)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        err.print(f"[red]✗[/red] findings.json parse error: {exc}", highlight=False)
        return 2

    located = locate_finding(findings, finding_id)
    if located is None:
        err.print(
            f"[red]✗[/red] finding '{finding_id}' not found in case {case_id}",
            highlight=False,
        )
        return 1
    _, finding = located
    if finding.get("status") == "APPROVED":
        err.print(
            f"[red]✗[/red] ALREADY_APPROVED: finding '{finding_id}' is already approved",
            highlight=False,
        )
        return 1

    obs = _find_obs(findings, finding.get("observation_id", ""))
    interp = _find_interp(obs, finding.get("interpretation_id", ""))
    _print_block(finding, obs, interp, 1, 1, console=console)

    # Password loop — max 3 attempts.
    attempts_remaining = _MAX_ATTEMPTS
    while attempts_remaining > 0:
        try:
            password = _read_password()
        except _NoTTYError:
            err.print(
                "[red]✗[/red] approve requires a TTY (use: silentwitness approve "
                f"{case_id} {finding_id} < /dev/tty)",
                highlight=False,
            )
            return 2
        except KeyboardInterrupt:
            console.print(highlight=False)
            return 130

        try:
            check = _check_verifier(password, case_dir)
        except _VerifierCorruptError as exc:
            err.print(f"[red]✗[/red] VERIFIER_CORRUPT: {exc}", highlight=False)
            _write_cli_audit(cli_log, finding_id, case_id, examiner, "error_VERIFIER_CORRUPT")
            return 2
        if check is False:
            attempts_remaining -= 1
            _write_cli_audit(cli_log, finding_id, case_id, examiner, "error_INVALID_PASSWORD")
            if attempts_remaining > 0:
                err.print(
                    f"[red]✗[/red] incorrect ({attempts_remaining} attempts remain)",
                    highlight=False,
                )
            else:
                err.print("[red]✗[/red] approval denied (0 attempts remain)", highlight=False)
                return 4
            continue

        # Password passed verifier check (or no verifier registered).
        # Note: approve_finding does NOT re-authenticate — it uses the password
        # directly as the HMAC key derivation input (via salt_hex, not verifier_salt_hex).
        # This verifier check is the sole UI authentication gate.
        audit_log = AuditLogger(case_dir, examiner)
        try:
            envelope = approve_finding(
                ApproveInput(finding_id=finding_id, password=SecretStr(password)),
                case_dir=case_dir,
                ledger_dir=ledger_dir,
                case_id=case_id,
                audit_logger=audit_log,
                model_used="cli",
            )
        finally:
            try:
                audit_log.close()
            except OSError as close_exc:
                err.print(
                    f"[yellow]![/yellow] audit-lock release failed: {close_exc} "
                    "(approval outcome unaffected)",
                    highlight=False,
                )

        result = envelope.data
        if result is None or not result.success:
            reason = result.reason if result is not None else None
            outcome = f"error_{reason.value if reason else 'unknown'}"
            _write_cli_audit(cli_log, finding_id, case_id, examiner, outcome)
            _t1 = ApproveRejectReason.ALREADY_APPROVED
            _t2 = ApproveRejectReason.FINDING_NOT_FOUND
            if reason in (_t1, _t2):
                err.print(f"[red]✗[/red] {reason.value}", highlight=False)
                return 1
            err.print(f"[red]✗[/red] {reason.value if reason else 'error'}", highlight=False)
            return 2

        # Success — write note if provided, then display sealed-entry block.
        if note is not None:
            try:
                with findings_lock(case_dir):
                    refreshed = read_findings(case_dir)
                    loc2 = locate_finding(refreshed, finding_id)
                    if loc2 is not None:
                        idx2, f2 = loc2
                        refreshed[idx2] = {**f2, "approval_note": note}
                        write_json_atomic(case_dir / "findings.json", refreshed)
            except Exception as note_exc:
                # approval_note is cosmetic; the authoritative record is already on the HMAC ledger.
                err.print(
                    f"[yellow]![/yellow] note not saved ({type(note_exc).__name__}: {note_exc}); "
                    "approval is committed to the ledger",
                    highlight=False,
                )

        _write_cli_audit(cli_log, finding_id, case_id, examiner, "approved")
        try:
            line_no, hmac_short = _ledger_info(ledger_dir, case_id)
        except LedgerCorruptionError as lce:
            err.print(
                f"[yellow]![/yellow] LEDGER_CORRUPT after approval: {lce}\n"
                "       Approval was written. Inspect the ledger file manually.",
                highlight=False,
            )
            return 2
        ledger_path = ledger_dir / f"{case_id}.jsonl"
        line_ref = f"#{line_no}" if line_no else ""
        rendered = _render_report(case_dir, examiner, err=err)
        report_line = (
            "report.md updated" if rendered else "report.md NOT updated — re-render via `export`"
        )
        console.print(
            f"[green]✓[/green] {finding_id} APPROVED\n"
            f"       ledger:  {ledger_path}{line_ref}\n"
            f"       hmac:    sha256:{hmac_short}  (PBKDF2-SHA256, 600,000 iter)\n"
            f"       {report_line}",
            highlight=False,
        )
        return 0

    return 4  # unreachable — loop exits via return
