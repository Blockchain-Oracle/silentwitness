"""Examiner approve command — password-gated HMAC ledger write (ux-spec §2.4)."""

from __future__ import annotations

import getpass
import hashlib
import hmac as _hmac
import json
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
from silentwitness_common.atomic_io import append_jsonl_line, write_json_atomic
from silentwitness_mcp.audit.ledger import HMACLedger, LedgerSecurityError
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings._approval_store import (
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

_DEFAULT_LEDGER_DIR = Path("/var/lib/silentwitness/verification")
_MAX_ATTEMPTS = 3
_PBKDF2_ITER = 600_000


class _NoTTYError(Exception):
    pass


def _read_password(prompt: str = "examiner password: ") -> str:
    # _SILENTWITNESS_TEST_PASSWORD: test-only bypass for TTY requirement.
    # Only active when pytest is loaded — never in production.
    if "pytest" in sys.modules and (tp := os.environ.get("_SILENTWITNESS_TEST_PASSWORD")):
        return tp
    if not sys.stdin.isatty():
        raise _NoTTYError()
    return getpass.getpass(prompt)


def _load_verifier(case_dir: Path) -> tuple[bytes, bytes] | None:
    """Return (verifier_salt, verifier_hash) from CASE.yaml if both fields present."""
    path = case_dir / "CASE.yaml"
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    vs = data.get("verifier_salt_hex")
    vh = data.get("verifier_hex")
    if not (isinstance(vs, str) and isinstance(vh, str)):
        return None
    try:
        return bytes.fromhex(vs), bytes.fromhex(vh)
    except ValueError:
        return None


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
    entry = json.dumps(
        {
            "ts": datetime.now(UTC).isoformat(),
            "tool": "cli.approve",
            "finding_id": finding_id,
            "case_id": case_id,
            "examiner": examiner,
            "outcome": outcome,
        }
    )
    try:
        append_jsonl_line(cli_log, entry)
    except (OSError, ValueError):
        pass  # audit write failure does not block the approval outcome


def _ledger_info(ledger_dir: Path, case_id: str) -> tuple[int, str]:
    """Return (1-indexed line count, hmac abbreviation) by reading the last entry."""
    try:
        ledger = HMACLedger(ledger_dir=ledger_dir, case_id=case_id)
        entries = ledger.read_all()
        if not entries:
            return 1, "????"
        last = entries[-1]
        hmac_short = last.hmac[:4] + "..." + last.hmac[-4:]
        return len(entries), hmac_short
    except Exception:
        return 0, "????"


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

    # Pre-checks (before password prompt): salt, ledger dir, finding existence.
    salt = load_case_salt(case_dir)
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

        check = _check_verifier(password, case_dir)
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

        # Password passed verifier check (or no verifier stored) — call approve_finding.
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
            audit_log.close()

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
            except (OSError, ValueError):
                pass  # note write failure does not invalidate the approval

        _write_cli_audit(cli_log, finding_id, case_id, examiner, "approved")
        line_no, hmac_short = _ledger_info(ledger_dir, case_id)
        ledger_path = ledger_dir / f"{case_id}.jsonl"
        line_ref = f"#{line_no}" if line_no else ""
        console.print(
            f"[green]✓[/green] {finding_id} APPROVED\n"
            f"       ledger:  {ledger_path}{line_ref}\n"
            f"       hmac:    sha256:{hmac_short}  (PBKDF2-SHA256, 600,000 iter)\n"
            f"       report.md update deferred (Epic 11 not installed)",
            highlight=False,
        )
        return 0

    return 4  # unreachable — loop exits via return
