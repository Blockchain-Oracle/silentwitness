"""register-evidence command — filesystem file registration with audit trail."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from rich.console import Console

from silentwitness_agent.cli_commands._evidence_types import (
    detect_evidence_type,
    human_size,
    sha256_hex,
)
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceContentDriftError,
    EvidenceRegistry,
    EvidenceRegistryError,
)


def run(
    case_dir: Path,
    case_id: str,
    path: Path,
    *,
    dry_run: bool,
    recursive: bool,
    examiner: str,
    no_color: bool,
) -> int:
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)
    t0 = time.monotonic()

    if not path.exists():
        err.print(f"[red]✗[/red] '{path}' does not exist", highlight=False)
        return 1

    try:
        candidates = path.rglob("*") if recursive and path.is_dir() else [path]
        files = [p for p in candidates if p.is_file()]
    except PermissionError as exc:
        err.print(f"[red]✗[/red] permission denied traversing '{path}': {exc}", highlight=False)
        return 1
    except OSError as exc:
        err.print(f"[red]✗[/red] system error traversing '{path}': {exc}", highlight=False)
        return 2

    if not files:
        hint = (
            " (use --recursive to traverse subdirectories)"
            if path.is_dir() and not recursive
            else ""
        )
        err.print(f"[red]✗[/red] no files found under '{path}'{hint}", highlight=False)
        return 1

    if dry_run:
        for p in files:
            try:
                digest, _ = sha256_hex(p)
                out.print(
                    f"DRY-RUN sha256:{digest}  {p.name}  ({detect_evidence_type(p)})",
                    highlight=False,
                )
            except PermissionError as exc:
                err.print(f"[red]✗[/red] permission denied: {p.name}: {exc}", highlight=False)
            except OSError as exc:
                err.print(f"[red]✗[/red] system error reading {p.name}: {exc}", highlight=False)
        return 0

    try:
        registry = EvidenceRegistry(case_dir=case_dir)
        audit_log = AuditLogger(case_dir, examiner)
        invocation_audit_id = audit_log.next_audit_id()
    except RuntimeError as exc:
        err.print(f"[red]✗[/red] audit lock conflict for case '{case_id}': {exc}", highlight=False)
        return 2
    except OSError as exc:
        err.print(
            f"[red]✗[/red] system error initialising case '{case_id}': {exc}", highlight=False
        )
        return 2

    registered = 0
    failed = 0
    for p in files:
        try:
            record = registry.register(p, detect_evidence_type(p), invocation_audit_id)
            if record.registered_audit_id != invocation_audit_id:
                out.print(
                    f"[yellow]⚠[/yellow] already registered (sha256 matches): {p.name}",
                    highlight=False,
                )
            else:
                sha_s = f"{record.sha256[:4]}...{record.sha256[-4:]}"
                out.print(
                    f"[green]✓[/green] registered {p.name}\n"
                    f"       sha256: {sha_s}    size: {human_size(record.size_bytes)}",
                    highlight=False,
                )
            registered += 1
        except EvidenceContentDriftError as exc:
            err.print(
                f"[red]✗[/red] sha256_mismatch_on_reregister: {p.name}: {exc}",
                highlight=False,
            )
            failed += 1
        except (EvidenceRegistryError, PermissionError, OSError) as exc:
            err.print(f"[red]✗[/red] {p.name}: {exc}", highlight=False)
            failed += 1

    result_summary: dict[str, object] = {"registered": registered, "errors": failed}
    try:
        audit_log.emit(
            backend="cli",
            tool="cli.register-evidence",
            params={"case_id": case_id, "paths": [str(p) for p in files], "recursive": recursive},
            result_summary=result_summary,
            result_sha256=hashlib.sha256(
                json.dumps(result_summary, sort_keys=True).encode()
            ).hexdigest(),
            stdout_path=case_dir / "audit" / "cli.jsonl",
            elapsed_ms=(time.monotonic() - t0) * 1000,
            model_used="cli",
        )
    except (OSError, ValueError) as exc:
        err.print(f"[red]✗[/red] system error writing audit entry: {exc}", highlight=False)
        return 2
    finally:
        try:
            audit_log.close()
        except OSError as close_exc:
            err.print(
                f"[red]✗[/red] system error releasing audit log lock: {close_exc}",
                highlight=False,
            )

    # Partial success exits 0; only an all-failure run is a hard error.
    return 1 if (failed and not registered) else 0
