"""Examiner review workflow: list DRAFT findings or prompt per finding."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

from silentwitness_common.atomic_io import append_jsonl_line, write_json_atomic
from silentwitness_mcp.findings._approval_store import (
    findings_lock,
    locate_finding,
    materialize_findings,
    read_findings,
)

_LOG = logging.getLogger(__name__)

_PROMPT = "[a]pprove  [r]eject  [m]odify  [s]kip  [q]uit  > "
_DIVIDER = "─" * 41
_CONF_STYLE: dict[str, str] = {"HIGH": "green", "MEDIUM": "yellow", "LOW": "dim"}


def _find_obs(findings: list[Any], oid: str) -> dict[str, Any]:
    return next((x for x in findings if isinstance(x, dict) and x.get("observation_id") == oid), {})


def _find_interp(obs: dict[str, Any], iid: str) -> dict[str, Any]:
    it: list[Any] = obs.get("interpretations") or []
    return next((i for i in it if isinstance(i, dict) and i.get("interpretation_id") == iid), {})


def _staged_fmt(finding: dict[str, Any]) -> str:
    ts = str(finding.get("staged_at") or "")
    try:
        return datetime.fromisoformat(ts).strftime("%H:%M:%SZ") if ts else "-"
    except (ValueError, OverflowError):
        return ts[:8] or "-"


def _print_block(
    finding: dict[str, Any],
    obs: dict[str, Any],
    interp: dict[str, Any],
    pos: int,
    total: int,
    *,
    console: Console,
) -> None:
    fid = finding.get("finding_id", "?")
    obs_text = obs.get("text") or ""
    interp_text = interp.get("text") or ""
    audit_ids = ", ".join(obs.get("audit_ids") or [])
    caveats = finding.get("caveats") or interp.get("caveats") or ""
    mitre = finding.get("mitre") or interp.get("mitre") or ""
    console.print(f"[{pos}/{total}] {fid}  staged {_staged_fmt(finding)}", highlight=False)
    console.print(_DIVIDER, highlight=False)
    console.print(f'observation: "{obs_text}"', highlight=False)
    console.print(f'interpretation: "{interp_text}"', highlight=False)
    console.print(f"cited:     {audit_ids}", highlight=False)
    if caveats:
        console.print(f'caveats:   "{caveats}"', highlight=False)
    if mitre:
        console.print(f"mitre:     {mitre}", highlight=False)
    console.print(highlight=False)


def _reject(case_dir: Path, finding_id: str, reason: str, examiner: str, *, err: Console) -> None:
    # First block: state mutation. If this fails, nothing is committed.
    try:
        with findings_lock(case_dir):
            findings = read_findings(case_dir)
            located = locate_finding(findings, finding_id)
            if located is None:
                return
            idx, finding = located
            findings[idx] = {**finding, "status": "REJECTED", "rejection_reason": reason}
            write_json_atomic(case_dir / "findings.json", findings)
    except (OSError, ValueError) as exc:
        err.print(f"[red]✗[/red] reject write failed: {exc}", highlight=False)
        return
    # Second block: audit write. findings.json is already committed at this point.
    cli_log = case_dir / "audit" / "cli.jsonl"
    cli_log.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps(
        {
            "ts": datetime.now(UTC).isoformat(),
            "tool": "cli.review.reject",
            "finding_id": finding_id,
            "reason": reason,
            "examiner": examiner,
        }
    )
    try:
        append_jsonl_line(cli_log, entry)
    except (OSError, ValueError) as exc:
        err.print(
            f"[red]✗[/red] rejection committed but audit write failed: {exc}",
            highlight=False,
        )


def _modify(
    case_dir: Path,
    finding_id: str,
    obs: dict[str, Any],
    interp: dict[str, Any],
    *,
    err: Console,
) -> bool:
    editor = os.environ.get("EDITOR") or shutil.which("vi") or shutil.which("nano")
    if not editor:
        err.print("[red]✗[/red] no editor available; set $EDITOR", highlight=False)
        return False
    obs_text = obs.get("text") or ""
    interp_text = interp.get("text") or ""
    yaml_content = (
        "# edits are saved to findings.json; original observation text is HMAC-signed\n"
        f"observation: |\n  {obs_text}\ninterpretation: |\n  {interp_text}\n"
    )
    # delete=False: file must be closed before the editor process opens it by path;
    # finally ensures cleanup even if subprocess or yaml parse raises.
    tf_path: str | None = None
    edited: dict[str, Any] = {}
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", encoding="utf-8", delete=False
        ) as tf:
            tf.write(yaml_content)
            tf_path = tf.name
        rc = subprocess.run([editor, tf_path]).returncode  # noqa: S603
        if rc != 0:
            err.print("[red]✗[/red] editor exited non-zero; modify aborted", highlight=False)
            return False
        raw = yaml.safe_load(Path(tf_path).read_text(encoding="utf-8"))
        edited = raw if isinstance(raw, dict) else {}
    except (OSError, yaml.YAMLError) as exc:
        err.print(f"[red]✗[/red] editor failed: {exc}", highlight=False)
        return False
    finally:
        if tf_path is not None:
            Path(tf_path).unlink(missing_ok=True)
    try:
        with findings_lock(case_dir):
            findings = read_findings(case_dir)
            located = locate_finding(findings, finding_id)
            if located is None:
                return False
            idx, finding = located
            mc = int(finding.get("modification_count") or 0) + 1
            update: dict[str, Any] = {"modification_count": mc}
            new_obs = (edited.get("observation") or "").strip()
            new_interp = (edited.get("interpretation") or "").strip()
            if new_obs and new_obs != obs_text:
                update["edited_observation"] = new_obs
            if new_interp and new_interp != interp_text:
                update["edited_interpretation"] = new_interp
            findings[idx] = {**finding, **update}
            write_json_atomic(case_dir / "findings.json", findings)
    except (OSError, ValueError) as exc:
        err.print(f"[red]✗[/red] modify write failed: {exc}", highlight=False)
        return False
    return True


def _run_critic_pass(case_dir: Path, examiner: str, *, err: Console) -> None:
    """Best-effort closed-loop critic over un-reviewed DRAFT findings.

    Materialization already created the DRAFT Finding records; here we run the
    fresh-context critic over the ones not yet carrying a ``critic_status`` and
    route its verdicts (AGREE keeps DRAFT, REJECT archives). Best-effort by
    design: if the model is unavailable (no key / offline — e.g. CI listing the
    table), we log and fall through to a plain listing rather than failing the
    command."""
    from silentwitness_agent.critic import StagedFinding, critique
    from silentwitness_agent.critic_handler import handle_critic_verdicts
    from silentwitness_common.types import Confidence

    try:
        findings = read_findings(case_dir)
    except (json.JSONDecodeError, ValueError, OSError):
        return
    staged: list[StagedFinding] = []
    for f in findings:
        if not (isinstance(f, dict) and f.get("finding_id") and f.get("status") == "DRAFT"):
            continue
        if f.get("critic_status"):  # already reviewed — don't re-spend tokens
            continue
        obs = _find_obs(findings, f.get("observation_id", ""))
        interp = _find_interp(obs, f.get("interpretation_id", ""))
        obs_text, interp_text = obs.get("text"), interp.get("text")
        if not obs_text or not interp_text:
            continue
        try:
            confidence = Confidence(str(interp.get("confidence", "LOW")).upper())
        except ValueError:
            confidence = Confidence.LOW
        staged.append(
            StagedFinding(
                finding_id=str(f["finding_id"]),
                observation_text=str(obs_text),
                interpretation_text=str(interp_text),
                confidence=confidence,
                cited_audit_ids=list(obs.get("audit_ids") or []),
            )
        )
    if not staged:
        return
    # Best-effort applies ONLY to the model call (no key / offline → list anyway).
    try:
        report = asyncio.run(critique(case_dir, examiner, staged))
    except Exception as exc:
        _LOG.warning("review: critic model unavailable (%s: %s)", type(exc).__name__, exc)
        err.print(
            f"[yellow]![/yellow] critic pass skipped ({type(exc).__name__}); "
            "listing un-reviewed findings",
            highlight=False,
        )
        return
    # Verdict routing writes findings.json/archived.json; a failure here is a
    # data-integrity event and MUST surface (handle_critic_verdicts raises on
    # persistence failure) — do not swallow it. pending_critiques is a throwaway
    # list: the CLI review has no live investigator loop to feed CHALLENGEs back to.
    handle_critic_verdicts(case_dir, examiner, report.verdicts, [])


def run_list(case_dir: Path, status_filter: str, *, console: Console, err: Console) -> int:
    # NOTE: callers (run()) materialize DRAFT findings before delegating here,
    # so the table is non-empty. run_list itself is pure read+render.
    try:
        findings = read_findings(case_dir)
    except (json.JSONDecodeError, ValueError, OSError) as exc:
        err.print(f"[red]✗[/red] findings.json parse error: {exc}", highlight=False)
        return 2
    target = status_filter.upper()
    f_records = sorted(
        [
            f
            for f in findings
            if isinstance(f, dict) and "finding_id" in f and f.get("status", "").upper() == target
        ],
        key=lambda f: f.get("staged_at") or "",
    )
    tbl = Table(show_header=True, header_style="bold")
    tbl.add_column("ID", no_wrap=True)
    tbl.add_column("staged_at", no_wrap=True)
    tbl.add_column("confidence", no_wrap=True)
    tbl.add_column("observation_snippet")
    tbl.add_column("cited")
    for f in f_records:
        obs = _find_obs(findings, f.get("observation_id", ""))
        interp = _find_interp(obs, f.get("interpretation_id", ""))
        conf = interp.get("confidence", "-")
        style = _CONF_STYLE.get(conf.upper(), "")
        conf_cell = f"[{style}]{conf}[/{style}]" if style else conf
        tbl.add_row(
            f.get("finding_id", "?"),
            _staged_fmt(f),
            conf_cell,
            (obs.get("text") or "")[:60],
            ", ".join(obs.get("audit_ids") or [])[:40],
        )
    console.print(tbl)
    return 0


def run_detail(
    case_dir: Path,
    case_id: str,
    finding_id: str,
    *,
    non_interactive: bool,
    console: Console,
    err: Console,
    examiner: str,
) -> int:
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
    obs = _find_obs(findings, finding.get("observation_id", ""))
    interp = _find_interp(obs, finding.get("interpretation_id", ""))
    _print_block(finding, obs, interp, 1, 1, console=console)
    if non_interactive:
        return 0
    # input() rather than rich.Prompt: CliRunner patches sys.stdin for test isolation;
    # rich.Prompt reads from Console.file, bypassing the runner's stdin capture.
    while True:
        try:
            key = input(_PROMPT).strip().lower()[:1]
        except (EOFError, KeyboardInterrupt):
            return 0
        if key in ("q", "s"):
            return 0
        if key == "a":
            console.print(
                f"to approve: silentwitness approve {case_id} {finding_id}", highlight=False
            )
            return 0
        if key == "r":
            try:
                reason = input("rejection reason: ").strip()
            except (EOFError, KeyboardInterrupt):
                return 0
            if reason:
                _reject(case_dir, finding_id, reason, examiner, err=err)
            return 0
        if key == "m":
            if _modify(case_dir, finding_id, obs, interp, err=err):
                # Re-read so _print_block reflects the committed edits on disk.
                try:
                    refreshed = read_findings(case_dir)
                except (json.JSONDecodeError, ValueError, OSError):
                    refreshed = findings
                loc2 = locate_finding(refreshed, finding_id)
                if loc2 is not None:
                    _, finding = loc2
                    obs = _find_obs(refreshed, finding.get("observation_id", ""))
                    interp = _find_interp(obs, finding.get("interpretation_id", ""))
            console.print(highlight=False)
            _print_block(finding, obs, interp, 1, 1, console=console)


def run(
    case_dir: Path,
    case_id: str,
    finding_id: str | None,
    status_filter: str,
    *,
    non_interactive: bool,
    no_color: bool,
    examiner: str,
) -> int:
    console, err = Console(no_color=no_color), Console(stderr=True, no_color=no_color)
    if finding_id is None:
        # Materialize DRAFT findings once, then run the critic over the
        # un-reviewed ones, before listing — so the examiner sees critic-annotated
        # DRAFTs. run_list does NOT re-materialize (it is pure read+render).
        try:
            materialize_findings(case_dir)
        except (OSError, ValueError) as exc:
            err.print(f"[yellow]![/yellow] finding materialization skipped: {exc}", highlight=False)
        _run_critic_pass(case_dir, examiner, err=err)
        return run_list(case_dir, status_filter, console=console, err=err)
    return run_detail(
        case_dir,
        case_id,
        finding_id,
        non_interactive=non_interactive,
        console=console,
        err=err,
        examiner=examiner,
    )
