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


# ---------------------------------------------------------------------------
# Wrapper-input invariant shared across tools with --pid filter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["vol_cmdline", "vol_malfind", "vol_dlllist", "vol_handles"])
@pytest.mark.parametrize("bad_pid", [0, -1, -1234])
def test_pid_filter_rejects_zero_and_negative_synchronously(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    bad_pid: int,
) -> None:
    """PID 0 (System Idle) and negative pids have no _EPROCESS — Vol3
    returns empty or errors confusingly. _validate_pid_filter rejects
    at the wrapper boundary so an LLM-driven typo gets a clean
    diagnostic; a refactor dropping it from ONE tool only would
    otherwise slip past CI."""
    from silentwitness_mcp.tools import memory as _memory

    _install_proc(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    fn = getattr(_memory, tool)
    with pytest.raises(ValueError, match="pid must be >= 1"):
        asyncio.run(
            fn(
                evidence,
                case_dir=case_dir,
                evidence_registry=registry,
                audit_logger=logger,
                model_used=MODEL,
                pid=bad_pid,
            )
        )


# ---------------------------------------------------------------------------
# Wrapper-input invariant — vol_handles object_types filter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_object_types",
    [
        [],  # empty list — caller-side typo
        [""],  # empty string entry
        [" "],  # whitespace-only entry
        ["\t"],  # tab-only entry
        ["File "],  # trailing-space (would silently match zero in Vol3)
        [" File"],  # leading-space
        ["File\n"],  # embedded newline
        ["File,Mutant"],  # pre-joined string from a bad caller
        ["Bogus"],  # not in action-shaping catalogue
        ["File", "Bogus"],  # one valid + one bogus
    ],
)
def test_object_types_filter_rejects_malformed_lists_synchronously(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    bad_object_types: list[str],
) -> None:
    """``object_types=[]`` / whitespace / pre-joined / non-allowlist
    entries must reject pre-spawn. A success envelope with zero rows
    would otherwise mask an LLM-driven slop input as real ground truth."""
    from silentwitness_mcp.tools.memory import vol_handles

    _install_proc(monkeypatch, _FakeProc(stdout=b"[]"))
    case_dir, evidence, logger, registry = env
    with pytest.raises(ValueError):
        asyncio.run(
            vol_handles(
                evidence,
                case_dir=case_dir,
                evidence_registry=registry,
                audit_logger=logger,
                model_used=MODEL,
                object_types=bad_object_types,
            )
        )


# ---------------------------------------------------------------------------
# Wrapper-input invariant — direct pid/object_types type-guard pins
# ---------------------------------------------------------------------------


def test_validate_pid_filter_rejects_bool_via_int_subclass_trap() -> None:
    """``True`` and ``False`` are ``isinstance(True, int) == True`` in
    Python — without the explicit ``bool`` exclusion they would round-
    trip to ``str(True)`` and Vol3 would reject ``--pid True`` with a
    cryptic message. Pin the bool-as-int trap branch."""
    from silentwitness_mcp.tools._peb_helpers import validate_pid_filter

    with pytest.raises(TypeError, match="pid must be int"):
        validate_pid_filter("vol_cmdline", True)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="pid must be int"):
        validate_pid_filter("vol_cmdline", False)  # type: ignore[arg-type]


def test_validate_pid_filter_rejects_float_and_str() -> None:
    """Non-int non-bool inputs must fail with the same TypeError shape
    (catches a regression that loosened the guard to ``isinstance(..., int)``
    only — float and str-bearing pids would slip past)."""
    from silentwitness_mcp.tools._peb_helpers import validate_pid_filter

    with pytest.raises(TypeError, match="pid must be int"):
        validate_pid_filter("vol_cmdline", 1.5)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="pid must be int"):
        validate_pid_filter("vol_cmdline", "1234")  # type: ignore[arg-type]


def test_refuse_path_propagates_caveats_and_classification_metadata(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cross-cutting regression: ``refuse()`` MUST propagate the
    wrapper's caveat block on every refuse path so an agent reading
    a refused envelope still gets the action-shaping guidance. A
    regression that dropped ``caveats=`` from the ``refuse_kw`` splat
    would silently ship empty caveats on every non-credential
    wrapper's refuse path. ``vol_netscan`` represents the non-
    credential family (no discipline_reminder); pin it through a
    TOOL_FAILED refuse."""
    _install_proc(monkeypatch, _FakeProc(stdout=b"", stderr=b"Vol3 broken", returncode=2))
    envelope = _run(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    # caveats MUST propagate on refuse, the action-shaping guidance for
    # the netscan family (pool-tag scan caveat, build-fragility caveat).
    assert len(envelope.caveats) >= 1
    assert any("pool-tag" in c for c in envelope.caveats)
    # vol_netscan does not set discipline_reminder; should be None.
    assert envelope.discipline_reminder is None


def test_blob_persist_oserror_carries_refuse_metadata(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A disk-full / EACCES OSError during blob persistence is one of
    the production failure modes for the credential-material path.
    Pin: the wrapper surfaces TOOL_FAILED with the structured
    _format_oserror advisory, AND caveats + (where applicable)
    discipline_reminder propagate through the refuse splat."""
    import os

    _install_proc(monkeypatch, _FakeProc(stdout=b"[]"))

    def _enospc(*_a: Any, **_k: Any) -> Path:
        raise OSError(28, os.strerror(28), str(env[0] / "audit" / "stdout-stub"))

    monkeypatch.setattr("silentwitness_mcp.tools._vol_pipeline.persist_blob", _enospc)
    envelope = _run(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == VolFailureReason.TOOL_FAILED.value
    assert "blob persist failed" in envelope.advisories[0]
    assert "errno=28" in envelope.advisories[0]
    # caveats propagate through the OSError refuse path too.
    assert len(envelope.caveats) >= 1
    # vol_netscan does not set discipline_reminder.
    assert envelope.discipline_reminder is None
