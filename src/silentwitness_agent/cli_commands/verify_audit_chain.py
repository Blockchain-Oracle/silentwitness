"""`silentwitness verify --audit-chain` — walks every audit/<backend>.jsonl
and verifies the hash chain (Phase 6b).

Independent from the HMAC-ledger reconciliation in :mod:`verify` so each can
ship + evolve on its own surface. Returns 0 on a clean walk; 1 on any
detected break; 2 on filesystem / setup errors. Emits one audit row of its
own (``cli.verify.audit-chain``) so the verification itself is part of the
hash chain for the next run.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Final

from rich.console import Console
from rich.table import Table

from silentwitness_mcp.audit.chain import ChainVerifyResult, verify_chain_lines

_AUDIT_DIR_NAME: Final = "audit"


def _verify_one_backend(jsonl: Path) -> ChainVerifyResult:
    """Read one ``<backend>.jsonl`` and verify its chain.

    The whole file is streamed line-by-line — even a multi-MB audit log fits
    in memory because ``verify_chain_lines`` accepts an iterable."""
    with jsonl.open("r", encoding="utf-8") as fh:
        return verify_chain_lines(fh)


def _format_break_row(break_: object) -> tuple[str, str, str, str]:
    """Render one ChainBreak into a 4-column row for the rich Table."""
    # Local import keeps this module's deps tiny — chain.ChainBreak is a frozen
    # dataclass so attribute access is the documented surface.
    return (
        str(getattr(break_, "index", "?")),
        str(getattr(break_, "reason", "?")),
        str(getattr(break_, "expected", "") or ""),
        str(getattr(break_, "actual", "") or ""),
    )


def run_audit_chain(
    case_dir: Path,
    *,
    no_color: bool,
) -> int:
    """Verify the per-backend audit hash chain. Returns 0 / 1 / 2 (clean / break /
    setup-error). One advisory caveat: an existing pre-chain (legacy) audit file
    will fail with ``record_hash_missing`` until the AuditLogger has appended at
    least one chain-enabled row — that's the intended hard signal that the chain
    is not yet established, not a transient warning."""
    t0 = time.monotonic()
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)

    audit_dir = case_dir / _AUDIT_DIR_NAME
    if not audit_dir.is_dir():
        err.print(
            f"[red]✗[/red] audit directory not found: {audit_dir}",
            highlight=False,
        )
        return 2

    jsonl_files = sorted(
        p for p in audit_dir.glob("*.jsonl") if p.is_file() and not p.name.startswith(".")
    )
    if not jsonl_files:
        out.print(
            f"[yellow]⚠[/yellow] no audit/*.jsonl files in {audit_dir} — "
            "nothing to verify (case has no recorded activity yet)",
            highlight=False,
        )
        return 0

    total_breaks = 0
    total_rows = 0
    summary_table = Table(title="Audit hash-chain verification")
    summary_table.add_column("Backend")
    summary_table.add_column("Rows", justify="right")
    summary_table.add_column("Breaks", justify="right")
    summary_table.add_column("Verdict")

    for jsonl in jsonl_files:
        result = _verify_one_backend(jsonl)
        total_rows += result.rows_checked
        total_breaks += len(result.breaks)
        verdict = "[green]OK[/green]" if result.ok else "[red]BROKEN[/red]"
        summary_table.add_row(
            jsonl.name, str(result.rows_checked), str(len(result.breaks)), verdict
        )
        if not result.ok:
            detail = Table(title=f"Breaks in {jsonl.name}", show_header=True)
            detail.add_column("Line", justify="right")
            detail.add_column("Reason")
            detail.add_column("Expected")
            detail.add_column("Actual")
            for brk in result.breaks:
                detail.add_row(*_format_break_row(brk))
            err.print(detail, highlight=False)

    out.print(summary_table, highlight=False)
    elapsed = time.monotonic() - t0
    out.print(
        f"\nChecked {total_rows} rows across {len(jsonl_files)} backend(s) in {elapsed:.2f}s",
        highlight=False,
    )

    if total_breaks:
        err.print(
            f"[red]✗[/red] audit-chain VERIFICATION FAILED — {total_breaks} "
            "break(s) detected. The audit log has been tampered with or the "
            "case predates chain enforcement.",
            highlight=False,
        )
        return 1

    out.print("[green]✓[/green] audit-chain verified clean", highlight=False)
    return 0


__all__ = ["run_audit_chain"]
