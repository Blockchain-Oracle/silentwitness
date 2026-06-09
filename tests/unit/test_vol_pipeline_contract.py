"""Cross-cutting tests for the shared Vol3 orchestrator
(:mod:`silentwitness_mcp.tools._vol_pipeline`). The contract pinned
here applies to every ``vol_*`` tool — we exercise it through
``vol_netscan`` as the representative caller, but a regression here
would silently affect pslist / psscan / pstree / malfind too."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._vol_common import VolFailureReason
from silentwitness_mcp.tools.memory import vol_netscan

MODEL = "claude-sonnet-4-6"


class _FakeProc:
    def __init__(self, *, stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> None:
        self._stdout, self._stderr = stdout, stderr
        self.returncode: int | None = returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr

    def terminate(self) -> None: ...
    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        return self.returncode if self.returncode is not None else -1


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-pipeline-01"
    case_dir.mkdir()
    evidence = tmp_path / "memdump.vmem"
    evidence.write_bytes(secrets.token_bytes(128))
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.MEMORY_DUMP, audit_id="sift-aj-20260609-001")
    return case_dir, evidence, AuditLogger(case_dir, examiner="aj"), EvidenceRegistry(case_dir)


def _install_proc(monkeypatch: pytest.MonkeyPatch, proc: _FakeProc) -> None:
    async def _fake(*_a: str, **_k: Any) -> _FakeProc:
        return proc

    monkeypatch.setattr("silentwitness_mcp.tools._vol_common.asyncio.create_subprocess_exec", _fake)


def _run(env: tuple[Path, Path, AuditLogger, EvidenceRegistry]) -> Any:
    case_dir, evidence, logger, registry = env
    return asyncio.run(
        vol_netscan(
            evidence,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def test_run_wrapper_forwards_tool_name_as_normalizer_key(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: every vol_* tool used to share the ``vol_pslist``
    normalizer key by default — citation-gate divergence at the first
    per-tool rule addition. Pipeline MUST forward ``tool_name``."""
    from silentwitness_mcp.verification import normalizer as _norm

    captured: list[str] = []
    real = _norm.normalize_output
    monkeypatch.setattr(
        "silentwitness_mcp.tools._vol_common.normalize_output",
        lambda raw, tool: (captured.append(tool), real(raw, tool))[1],
    )
    _install_proc(monkeypatch, _FakeProc(stdout=b"[]"))
    envelope = _run(env)
    assert envelope.success is True
    assert captured == ["vol_netscan"]


def test_tool_failed_with_empty_stderr_yields_synthetic_advisory(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Vol3 process killed before any stderr (SIGSEGV, OOM, closed
    pipe) used to surface as TOOL_FAILED with ``advisories[0] == ""`` —
    the agent saw "tool failed" with no diagnostic. The pipeline now
    substitutes a synthetic advisory naming exit code + plugin."""
    _install_proc(monkeypatch, _FakeProc(stdout=b"", stderr=b"", returncode=-9))
    envelope = _run(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "exited -9" in envelope.advisories[0]
    assert "windows.netscan.NetScan" in envelope.advisories[0]
    assert "no stderr output" in envelope.advisories[0]
