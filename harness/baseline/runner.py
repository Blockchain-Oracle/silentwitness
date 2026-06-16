"""Baseline runner: drives vanilla Protocol SIFT 2026 in plan mode against pinned evidence.

Runs with --plan-mode (--dry-run fallback); model + temperature are pinned.
Repin SHA256: sha256sum install.sh -> update install-script-sha256.txt.
Exit codes: 0 ok, 2 config, 3 install, 4 timeout, 5 error.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

_INSTALL_SCRIPT_SHA256_FILE = Path(__file__).resolve().parent / "install-script-sha256.txt"
_RESULTS_DIR = Path(__file__).resolve().parents[2] / "harness" / "results"
INSTALL_SCRIPT_SHA256 = _INSTALL_SCRIPT_SHA256_FILE.read_text(encoding="utf-8").strip()
_DatasetId = Literal["nitroba", "nist-data-leakage", "nist-hacking-case", "case-trapdoor"]
_DEFAULT_MODEL = "anthropic:claude-opus-4-7"


class BaselineInstallError(Exception):
    """Raised when the Protocol SIFT install script fails or SHA256 mismatches."""


class BaselineTimeoutError(Exception):
    """Raised when the baseline run exceeds timeout_seconds."""


class BaselineRunConfig(BaseModel):
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
    work_dir: Path | None = None


class BaselineFinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    type: Literal["finding"]
    id: str
    text: str
    cited_artifact_paths: list[str] = Field(default_factory=list)
    cited_at_offset_seconds: float = 0.0


class BaselineToolCall(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    type: Literal["tool_call"]
    seq: int
    tool_name: str
    argv: list[str] = Field(default_factory=list)
    elapsed_ms: int = 0
    exit_code: int = 0


class BaselineRunResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_id: _DatasetId
    started_at: datetime
    finished_at: datetime
    elapsed_seconds: float = Field(ge=0.0)
    exit_code: int
    model: str
    temperature: float = Field(ge=0.0, le=1.0)
    commit_sha: str
    findings: list[BaselineFinding]
    tool_calls: list[BaselineToolCall]
    stdout_path: Path
    stderr_path: Path
    report_md_path: Path | None
    notes: list[str]

    @model_validator(mode="after")
    def _check_temporal_consistency(self) -> BaselineRunResult:
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        return self


def install_baseline(
    work_dir: Path,
    *,
    install_url: str = "https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh",
) -> Path:
    """Fetch, verify SHA256, and run the Protocol SIFT install script. Returns sift_dir.

    Raises BaselineInstallError on httpx absence, SHA256 mismatch, or non-zero exit.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    script_path = work_dir / "install.sh"
    log_path = work_dir / "install.log"

    if httpx is None:
        raise BaselineInstallError("httpx is required. Run `uv add httpx` or pre-stage the script.")
    try:
        response = httpx.get(install_url, follow_redirects=True, timeout=60.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise BaselineInstallError(f"Network error fetching {install_url}: {exc!r}") from exc

    script_bytes = response.content
    actual_sha = hashlib.sha256(script_bytes).hexdigest()
    if actual_sha != INSTALL_SCRIPT_SHA256:
        raise BaselineInstallError(
            f"install.sh SHA256 mismatch: got {actual_sha!r}, expected {INSTALL_SCRIPT_SHA256!r}. "
            f"Update {_INSTALL_SCRIPT_SHA256_FILE} if intentional."
        )
    script_path.write_bytes(script_bytes)

    sift_env = {**os.environ, "PROTOCOL_SIFT_HOME": str(work_dir / "protocol-sift")}
    with log_path.open("wb") as log_fh:
        result = subprocess.run(  # noqa: S603 — script is SHA256-verified before execution
            ["bash", str(script_path)],  # noqa: S607 — bash resolves via PATH
            cwd=str(work_dir),
            env=sift_env,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
        )
    if result.returncode != 0:
        raise BaselineInstallError(f"Install script exited {result.returncode}. See {log_path}.")

    sift_dir = work_dir / "protocol-sift"
    if not sift_dir.exists():
        raise BaselineInstallError(
            f"Install script exited 0 but {sift_dir} not created. See {log_path}."
        )
    return sift_dir


def _get_commit_sha(sift_dir: Path) -> str:
    try:
        r = subprocess.run(  # noqa: S603 — git is a trusted system binary
            ["git", "-C", str(sift_dir), "rev-parse", "HEAD"],  # noqa: S607 — git resolves via PATH
            capture_output=True,
            text=True,
            timeout=10,
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


def _probe_plan_mode_flag(sift_bin: Path) -> str:
    """Return --plan-mode if supported, else --dry-run, else empty string."""
    try:
        r = subprocess.run(  # noqa: S603 — sift_bin is from the pinned install dir
            [str(sift_bin), "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError as exc:
        raise BaselineInstallError(
            f"protocol-sift binary not found at {sift_bin}. Check install.log."
        ) from exc
    except PermissionError as exc:
        raise BaselineInstallError(f"protocol-sift binary at {sift_bin} not executable.") from exc
    except subprocess.TimeoutExpired:
        return ""  # --help hung; degrade gracefully, caller records a note
    if "--plan-mode" in r.stdout + r.stderr:
        return "--plan-mode"
    if "--dry-run" in r.stdout + r.stderr:
        return "--dry-run"
    return ""


def run_baseline(config: BaselineRunConfig) -> BaselineRunResult:
    """Invoke Protocol SIFT investigate with --json-events; parse event stream.

    Raises BaselineInstallError, BaselineTimeoutError, or RuntimeError.
    """
    work_dir = config.work_dir or Path(tempfile.mkdtemp(prefix="protocol-sift-baseline-"))
    sift_dir = work_dir / "protocol-sift"
    sift_bin = sift_dir / "bin" / "protocol-sift"

    stdout_path = work_dir / "baseline.stdout"
    stderr_path = work_dir / "baseline.stderr"

    commit_sha = _get_commit_sha(sift_dir)
    plan_flag = _probe_plan_mode_flag(sift_bin)

    notes: list[str] = []
    if not plan_flag:
        notes.append("Neither --plan-mode nor --dry-run in --help; no containment flag used")
    elif plan_flag == "--dry-run":
        notes.append("--plan-mode not supported; fell back to --dry-run")

    cmd = [
        str(sift_bin),
        "investigate",
        str(config.evidence_path),
        "--model",
        config.model,
        "--temperature",
        str(config.temperature),
        "--examiner",
        config.examiner,
        "--json-events",
    ]
    if plan_flag:
        cmd.append(plan_flag)

    sift_env = {
        **os.environ,
        "SILENTWITNESS_MODEL": config.model,
        "XDG_CACHE_HOME": str(work_dir / "cache"),
    }

    findings: list[BaselineFinding] = []
    tool_calls: list[BaselineToolCall] = []
    dropped_lines = 0
    started_at = datetime.now(UTC)
    t0 = time.monotonic()

    with stdout_path.open("wb") as stdout_fh, stderr_path.open("wb") as stderr_fh:
        proc = subprocess.Popen(  # noqa: S603 — cmd is built from config-validated paths
            cmd,
            stdout=subprocess.PIPE,
            stderr=stderr_fh,
            env=sift_env,
        )
        if proc.stdout is None:
            raise RuntimeError("subprocess.Popen stdout pipe was None (process launch failure)")
        try:
            for raw_line in iter(proc.stdout.readline, b""):
                stdout_fh.write(raw_line)
                offset = time.monotonic() - t0
                if time.monotonic() - t0 > config.timeout_seconds:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    raise BaselineTimeoutError(
                        f"Baseline exceeded timeout_seconds={config.timeout_seconds}"
                    )
                line = raw_line.decode(errors="replace").strip()
                if not line:
                    continue
                try:
                    evt_raw = json.loads(line)
                    evt_type = evt_raw.get("type", "")
                    if evt_type == "finding":
                        evt_raw.setdefault("cited_at_offset_seconds", offset)
                        findings.append(BaselineFinding.model_validate(evt_raw))
                    elif evt_type == "tool_call":
                        tool_calls.append(BaselineToolCall.model_validate(evt_raw))
                except json.JSONDecodeError:
                    dropped_lines += 1
                except ValidationError as exc:
                    raise RuntimeError(
                        f"Protocol SIFT event schema drift at offset {offset:.1f}s: {exc}\n"
                        f"Line: {line[:200]}"
                    ) from exc
        finally:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    finished_at = datetime.now(UTC)
    elapsed = (finished_at - started_at).total_seconds()
    exit_code = proc.returncode if proc.returncode is not None else 0

    if dropped_lines:
        notes.append(f"{dropped_lines} non-JSON stdout line(s) skipped.")

    candidate = work_dir / "cases" / config.dataset_id / "report.md"
    report_md_path: Path | None = candidate if candidate.exists() else None

    return BaselineRunResult(
        dataset_id=config.dataset_id,
        started_at=started_at,
        finished_at=finished_at,
        elapsed_seconds=elapsed,
        exit_code=exit_code,
        model=config.model,
        temperature=config.temperature,
        commit_sha=commit_sha,
        findings=findings,
        tool_calls=tool_calls,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        report_md_path=report_md_path,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run vanilla Protocol SIFT baseline.")
    parser.add_argument("--dataset", required=True, help="Dataset ID")
    parser.add_argument("--evidence", required=True, type=Path, help="Evidence directory path")
    parser.add_argument("--examiner", default="sansforensics")
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--out", type=Path, default=None, help="Output directory override")
    args = parser.parse_args(argv)

    if not args.evidence.exists():
        print(
            f"config/validation error: evidence_path {args.evidence!r} does not exist",
            file=sys.stderr,
        )
        return 2

    try:
        config = BaselineRunConfig(
            dataset_id=args.dataset,
            evidence_path=args.evidence,
            examiner=args.examiner,
            model=args.model or os.environ.get("SILENTWITNESS_MODEL", _DEFAULT_MODEL),
            temperature=args.temperature,
            work_dir=args.out,
        )
    except ValidationError as exc:
        print(f"config/validation error: {exc}", file=sys.stderr)
        return 2

    work_dir = config.work_dir or Path(tempfile.mkdtemp(prefix="protocol-sift-baseline-"))
    config = config.model_copy(update={"work_dir": work_dir})

    try:
        install_baseline(work_dir)
    except BaselineInstallError as exc:
        print(f"install failure: {exc}", file=sys.stderr)
        return 3

    try:
        result = run_baseline(config)
    except BaselineInstallError as exc:
        print(f"install failure: {exc}", file=sys.stderr)
        return 3
    except BaselineTimeoutError as exc:
        print(f"timeout: {exc}", file=sys.stderr)
        return 4
    except Exception as exc:
        print(f"baseline error ({type(exc).__name__}): {exc}", file=sys.stderr)
        return 5

    if result.exit_code != 0:
        print(f"baseline exited {result.exit_code}", file=sys.stderr)

    out_dir = _RESULTS_DIR / config.dataset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    out_path = out_dir / f"baseline-{ts}.json"

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
