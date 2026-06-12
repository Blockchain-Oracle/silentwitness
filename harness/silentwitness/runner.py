"""SilentWitness harness runner: invokes the SW investigator against pinned evidence.

Runs the installed `silentwitness` CLI with SILENTWITNESS_MODEL + temperature
pinned identically to the baseline runner (PRD §14 fair-compare discipline).
Exit codes: 0 ok, 2 config/validation, 4 timeout, 5 investigator non-zero exit or write failure.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_DatasetId = Literal["nitroba", "nist-data-leakage", "nist-hacking-case", "case-trapdoor"]
_DEFAULT_MODEL = "anthropic:claude-opus-4-7-1m"
_RESULTS_DIR = Path(__file__).resolve().parents[2] / "harness" / "results"

# Literal sets match values written by the SW agent to audit JSONL files.
_HypothesisEventType = Literal["form", "dispatch", "confirm", "pivot", "abandon"]
_CriticVerdictType = Literal["agree", "challenge", "reject"]  # lowercase in JSONL output


class SwFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    id: str = Field(min_length=1)
    observation_id: str = ""
    interpretation_id: str = ""
    status: str = "DRAFT"
    title: str = ""
    cited_audit_ids: list[str] = Field(default_factory=list)
    cited_artifact_paths: list[str] = Field(default_factory=list)
    staged_at_offset_seconds: float = Field(default=0.0, ge=0.0)


class SwHypothesisEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    ts: datetime
    type: _HypothesisEventType
    hypothesis_id: str
    reason: str = ""


class SwToolCall(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    ts: datetime
    audit_id: str = Field(min_length=1)
    tool: str
    result_sha256: str = ""
    elapsed_ms: float = Field(default=0.0, ge=0.0)
    result_summary: dict[str, object] = Field(default_factory=dict)


class SwCriticVerdict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    ts: datetime
    type: _CriticVerdictType
    finding_id: str
    reason: str = ""
    examiner: str = ""


class SilentWitnessRunConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: _DatasetId
    evidence_path: Path
    examiner: str = Field(default="sansforensics", min_length=1)
    model: str = Field(
        default_factory=lambda: os.environ.get("SILENTWITNESS_MODEL", _DEFAULT_MODEL),
        min_length=1,
    )
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    timeout_seconds: int = Field(default=1800, gt=0)
    case_dir: Path | None = None


class SilentWitnessRunResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: _DatasetId
    started_at: datetime
    finished_at: datetime
    elapsed_seconds: float = Field(ge=0.0)
    exit_code: int
    model: str
    temperature: float = Field(ge=0.0, le=1.0)
    commit_sha: str = Field(min_length=1)
    findings: list[SwFinding]
    hypothesis_events: list[SwHypothesisEvent]
    pivots: list[SwHypothesisEvent]
    tool_calls: list[SwToolCall]
    critic_verdicts: list[SwCriticVerdict]
    report_md_path: Path | None
    report_md_sha256: str | None
    entity_gate_rejections: int = Field(ge=0)
    epistemic_honesty_count: int = Field(ge=0)
    time_to_first_finding_seconds: float | None
    time_to_handoff_ready_report_seconds: float | None
    notes: list[str]

    @model_validator(mode="after")
    def _check_invariants(self) -> SilentWitnessRunResult:
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        if (self.report_md_path is None) != (self.report_md_sha256 is None):
            raise ValueError(
                "report_md_path and report_md_sha256 must both be None or both non-None"
            )
        return self


def _get_commit_sha() -> str:
    repo_root = str(Path(__file__).resolve().parents[2])
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_root,
        )
        if r.returncode == 0:
            return r.stdout.strip()
        return f"unknown (git exit {r.returncode})"
    except FileNotFoundError:
        return "unknown (git not found on PATH)"
    except (PermissionError, OSError) as exc:
        return f"unknown ({type(exc).__name__}: {exc})"
    except subprocess.TimeoutExpired:
        return "unknown (git rev-parse timed out)"


def _check_executive_summary(report_md: Path, t0: float) -> float | None:
    """Return elapsed seconds since t0 if report.md has content before the next ## heading.

    Returns None if the file is absent, unreadable, or the section is empty.
    """
    try:
        content = report_md.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^## Executive Summary\b", content, re.MULTILINE)
        if m:
            after = content[m.end() :].lstrip()
            if after and not after.startswith("##"):
                return time.monotonic() - t0
    except OSError:
        pass
    return None


def run_silentwitness(config: SilentWitnessRunConfig) -> SilentWitnessRunResult:
    """Invoke the SilentWitness investigator; parse case directory artifacts.

    Returns SilentWitnessRunResult with exit_code=4 on timeout.
    Raises RuntimeError on unexpected process failure.
    """
    from harness.silentwitness import case_dir_reader  # lazy: avoids circular import

    if config.case_dir is None:
        parent = Path(tempfile.mkdtemp(prefix="silentwitness-harness-"))
        # Match the CLI's case resolution: SILENTWITNESS_CASES_DIR/cases/<dataset_id>/
        actual_case_dir = parent / "cases" / config.dataset_id
        notes: list[str] = [f"auto-created case_dir: {actual_case_dir}"]
    else:
        actual_case_dir = config.case_dir
        parent = actual_case_dir.parent
        notes = []

    actual_case_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = actual_case_dir / ".harness-stdout.log"
    stderr_log = actual_case_dir / ".harness-stderr.log"
    report_md = actual_case_dir / "report.md"

    if config.temperature != 0.0:
        notes.append(
            f"warning: SILENTWITNESS_TEMPERATURE={config.temperature} set "
            "but SW CLI does not read this env var — temperature pin not enforced"
        )

    cmd = [
        "silentwitness",
        "investigate",
        config.dataset_id,
        "--evidence",
        str(config.evidence_path),
        "--examiner",
        config.examiner,
        "--auto-approve",
    ]
    env = {
        **os.environ,
        "SILENTWITNESS_MODEL": config.model,
        "SILENTWITNESS_TEMPERATURE": str(config.temperature),
        "SILENTWITNESS_CASES_DIR": str(parent),
        "XDG_CACHE_HOME": str(parent / ".cache"),
    }

    commit_sha = _get_commit_sha()
    started_at = datetime.now(UTC)
    t0 = time.monotonic()
    handoff_ts: float | None = None
    timed_out = False

    with stdout_log.open("wb") as out_fh, stderr_log.open("wb") as err_fh:
        proc = subprocess.Popen(  # noqa: S603
            cmd,
            stdout=out_fh,
            stderr=err_fh,
            env=env,
        )
        try:
            while proc.poll() is None:
                time.sleep(0.25)
                if time.monotonic() - t0 > config.timeout_seconds:
                    timed_out = True
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        try:
                            proc.wait(timeout=30)
                        except subprocess.TimeoutExpired:
                            print(
                                f"warning: process {proc.pid} did not exit after SIGKILL+30s",
                                file=sys.stderr,
                            )
                    break
                if handoff_ts is None:
                    handoff_ts = _check_executive_summary(report_md, t0)
        finally:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    print(
                        f"warning: process {proc.pid} did not exit after SIGKILL+30s",
                        file=sys.stderr,
                    )

    if handoff_ts is None and not timed_out:
        handoff_ts = _check_executive_summary(report_md, t0)

    finished_at = datetime.now(UTC)
    elapsed = (finished_at - started_at).total_seconds()

    if timed_out:
        exit_code = 4
        notes.append(f"silentwitness timeout after {elapsed:.1f}s")
    elif proc.returncode is None:
        notes.append("warning: proc.returncode was None after wait(); recording exit_code=-1")
        exit_code = -1
    else:
        exit_code = proc.returncode
        if exit_code != 0:
            notes.append(f"silentwitness exited {exit_code}")

    findings = case_dir_reader.read_findings_json(actual_case_dir)
    hypothesis_events, h_notes = case_dir_reader.read_hypothesis_jsonl(actual_case_dir)
    tool_calls, audit_notes = case_dir_reader.read_audit_jsonl(actual_case_dir)
    critic_verdicts, c_notes = case_dir_reader.read_critic_jsonl(actual_case_dir)
    notes.extend(h_notes)
    notes.extend(audit_notes)
    notes.extend(c_notes)

    pivots = [e for e in hypothesis_events if e.type == "pivot"]
    entity_gate_rejections = sum(
        1
        for tc in tool_calls
        if tc.tool == "record_observation"
        and tc.result_summary.get("success") is False
        and "entit" in str(tc.result_summary.get("reason", "")).lower()
    )
    epistemic_honesty_count = case_dir_reader.count_gaps_in_report(report_md)

    first_finding_ts = min(
        (f.staged_at_offset_seconds for f in findings if f.staged_at_offset_seconds > 0),
        default=None,
    )

    report_md_sha256: str | None = None
    report_md_final: Path | None = None
    if report_md.exists():
        report_md_sha256 = hashlib.sha256(report_md.read_bytes()).hexdigest()
        report_md_final = report_md

    if handoff_ts is None and not timed_out:
        notes.append("handoff-ready threshold not reached within timeout")

    return SilentWitnessRunResult(
        dataset_id=config.dataset_id,
        started_at=started_at,
        finished_at=finished_at,
        elapsed_seconds=elapsed,
        exit_code=exit_code,
        model=config.model,
        temperature=config.temperature,
        commit_sha=commit_sha,
        findings=findings,
        hypothesis_events=hypothesis_events,
        pivots=pivots,
        tool_calls=tool_calls,
        critic_verdicts=critic_verdicts,
        report_md_path=report_md_final,
        report_md_sha256=report_md_sha256,
        entity_gate_rejections=entity_gate_rejections,
        epistemic_honesty_count=epistemic_honesty_count,
        time_to_first_finding_seconds=first_finding_ts,
        time_to_handoff_ready_report_seconds=handoff_ts,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run SilentWitness investigator harness.")
    parser.add_argument("--dataset", required=True, help="Dataset ID")
    parser.add_argument("--evidence", required=True, type=Path, help="Evidence directory path")
    parser.add_argument("--examiner", default="sansforensics")
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--case-dir", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None, help="Results output directory")
    args = parser.parse_args(argv)

    if not args.evidence.exists():
        print(
            f"config/validation error: evidence_path {args.evidence!r} does not exist",
            file=sys.stderr,
        )
        return 2

    try:
        from pydantic import ValidationError

        config = SilentWitnessRunConfig(
            dataset_id=args.dataset,
            evidence_path=args.evidence,
            examiner=args.examiner,
            model=args.model or os.environ.get("SILENTWITNESS_MODEL", _DEFAULT_MODEL),
            temperature=args.temperature,
            case_dir=args.case_dir,
        )
    except ValidationError as exc:
        print(f"config/validation error: {exc}", file=sys.stderr)
        return 2

    try:
        result = run_silentwitness(config)
    except Exception as exc:
        print(f"runner error ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 5

    out_dir = (args.out or _RESULTS_DIR) / config.dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    out_path = out_dir / f"silentwitness-{ts}.json"

    text = result.model_dump_json(indent=2)
    fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        Path(tmp).replace(out_path)
    except OSError as exc:
        print(f"failed to write result: {exc}", file=sys.stderr)
        try:
            os.unlink(tmp)
        except OSError as cleanup_exc:
            print(f"warning: failed to remove temp file {tmp}: {cleanup_exc}", file=sys.stderr)
        return 5

    print(f"result written to {out_path}", file=sys.stderr)
    return 0 if result.exit_code == 0 else 5


if __name__ == "__main__":
    sys.exit(main())
