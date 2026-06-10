"""Unit tests for :func:`parse_mft` — EZ-Tools MFTECmd CSV wrapper.

The dotnet subprocess + the MFTECmd CSV-write are both mocked. Real
end-to-end coverage lives in
``tests/integration/tools/test_disk_parse_mft_integration.py`` (skipped
on non-SIFT runners)."""

from __future__ import annotations

import asyncio
import secrets
import shutil
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DiskFailureReason
from silentwitness_mcp.tools.disk import parse_mft

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"
_MFT_SAMPLE = _FIXTURE_DIR / "mft_sample.csv"
_MFT_TRUNCATED = _FIXTURE_DIR / "mft_truncated.csv"


class _FakeProc:
    """Stand-in for :class:`asyncio.subprocess.Process` — MFTECmd's
    subprocess is mocked at the asyncio layer."""

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


def _install_dotnet_mock(
    monkeypatch: pytest.MonkeyPatch,
    *,
    csv_fixture: Path,
    csv_out_dir: Path,
    csv_filename: str = "20260610150000_MFTECmd_$MFT_Output.csv",
    proc: _FakeProc | None = None,
) -> list[tuple[str, ...]]:
    """Mock :func:`asyncio.create_subprocess_exec` so the dotnet
    subprocess never spawns. Side-effect: copy the chosen fixture CSV
    into ``csv_out_dir`` under ``csv_filename`` so the wrapper's glob
    finds it."""
    calls: list[tuple[str, ...]] = []
    proc = proc or _FakeProc(stdout=b"", stderr=b"", returncode=0)

    async def _fake(*argv: str, **_kw: Any) -> _FakeProc:
        calls.append(argv)
        if proc.returncode == 0:
            csv_out_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(csv_fixture, csv_out_dir / csv_filename)
        return proc

    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_common.asyncio.create_subprocess_exec", _fake
    )
    return calls


def _force_dotnet_exists(monkeypatch: pytest.MonkeyPatch, exists: bool = True) -> None:
    """Mock the :data:`DOTNET_BIN` existence check so the test doesn't
    depend on the dev host having /usr/bin/dotnet installed."""
    real_exists = Path.exists

    def _patched(self: Path) -> bool:
        from silentwitness_mcp.tools._disk_common import DOTNET_BIN

        if self == DOTNET_BIN:
            return exists
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", _patched)


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    """Registered evidence + case dir + dedicated csv_out dir.

    The ``$MFT`` fixture is synthetic random bytes (the registry only
    hashes content; MFTECmd's parser sees the fixture CSV via the
    subprocess mock)."""
    case_dir = tmp_path / "case-mft-01"
    case_dir.mkdir()
    evidence = tmp_path / "MFT"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = tmp_path / "mft_csv_out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(evidence, EvidenceType.OTHER, audit_id="sift-aj-20260610-001")
    return (
        case_dir,
        evidence,
        csv_out,
        AuditLogger(case_dir, examiner="aj"),
        EvidenceRegistry(case_dir),
    )


def _invoke(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    *,
    evidence_override: Path | None = None,
) -> Any:
    case_dir, evidence, csv_out, logger, registry = env
    return asyncio.run(
        parse_mft(
            evidence_override or evidence,
            csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


# ---------------------------------------------------------------------------
# Success-path: parse, derive IsDeleted+SiFnDelta, propagate caveats
# ---------------------------------------------------------------------------


def test_parse_mft_canonical_csv_parses_with_caveats(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A canonical MFTECmd CSV round-trips into typed entries with the
    SI/FN timestomp action-shaping caveat at index 0."""
    _force_dotnet_exists(monkeypatch)
    csv_out = env[2]
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=csv_out)
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count == 5
    assert envelope.data.truncated is False
    # Action-shaping caveat[0] is the timestomp directive.
    assert "SI/FN divergence" in envelope.caveats[0]
    # cmd_argv records the dotnet + MFTECmd.dll path for the audit log.
    assert envelope.data_provenance.cmd_argv[0] == "/usr/bin/dotnet"
    assert envelope.data_provenance.cmd_argv[1] == "/opt/zimmermantools/MFTECmd.dll"


def test_parse_mft_derives_isdeleted_and_sifndelta(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The deleted row in the fixture (``InUse=False``) surfaces as
    ``IsDeleted=True``; the timestomp row (``Timestomped=True``)
    surfaces as ``SiFnDelta=True`` — server-side-derived columns are
    populated by the @model_validator, not by the CSV."""
    _force_dotnet_exists(monkeypatch)
    csv_out = env[2]
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=csv_out)
    envelope = _invoke(env)
    assert envelope.success is True
    by_entry = {e.EntryNumber: e for e in envelope.data.entries}
    # Entry 123 (oldproject) has InUse=False → IsDeleted=True.
    assert by_entry[123].IsDeleted is True
    assert by_entry[123].InUse is False
    # Entry 99 (suspicious.exe) has Timestomped=True → SiFnDelta=True.
    assert by_entry[99].SiFnDelta is True
    assert by_entry[99].Timestomped is True
    assert by_entry[99].uSecZeros is True


# ---------------------------------------------------------------------------
# Refuse-path: pre-spawn gates
# ---------------------------------------------------------------------------


def test_parse_mft_unregistered_evidence_refuses_without_spawning(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unregistered evidence path MUST surface as
    EVIDENCE_NOT_REGISTERED before any dotnet subprocess is spawned."""
    _force_dotnet_exists(monkeypatch)
    unreg = env[0].parent / "MFT_HALLUCINATED"
    unreg.write_bytes(b"x")
    calls = _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env, evidence_override=unreg)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []
    # caveats still propagate on refuse — the agent narrating the
    # refusal must know this was the MFT/timestomp surface.
    assert len(envelope.caveats) == 4


def test_parse_mft_dotnet_missing_refuses_with_install_sh_hint(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing :data:`DOTNET_BIN` surfaces DOTNET_NOT_FOUND with an
    advisory pointing at ``install.sh``."""
    _force_dotnet_exists(monkeypatch, exists=False)
    calls = _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.DOTNET_NOT_FOUND.value
    assert "install.sh" in envelope.advisories[0]
    assert calls == []


def test_parse_mft_tampered_evidence_returns_evidence_tampered(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-registration content drift (the file's SHA256 no longer
    matches what was registered) surfaces as EVIDENCE_TAMPERED."""
    _force_dotnet_exists(monkeypatch)
    env[1].write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_TAMPERED.value
    assert calls == []


def test_parse_mft_tool_failed_surfaces_truncated_stderr(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MFTECmd is the only EZ Tool with a reliable exit code; a
    non-zero return surfaces stderr verbatim (truncated to the
    advisory cap) as the TOOL_FAILED advisory."""
    _force_dotnet_exists(monkeypatch)
    stderr = b"MFTECmd: unrecognised $MFT signature; aborting\n" + b"X" * 1000
    _install_dotnet_mock(
        monkeypatch,
        csv_fixture=_MFT_SAMPLE,
        csv_out_dir=env[2],
        proc=_FakeProc(stdout=b"", stderr=stderr, returncode=2),
    )
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.TOOL_FAILED.value
    assert "unrecognised $MFT signature" in envelope.advisories[0]
    assert len(envelope.advisories[0]) <= 500


# ---------------------------------------------------------------------------
# Truncation: partial-success
# ---------------------------------------------------------------------------


def test_parse_mft_truncated_csv_returns_partial_success(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A CSV cut mid-row (MFTECmd killed before flush) parses as
    success=True with truncated=True and a 'partial parse: N rows
    recovered' advisory — partial-success is forensically preferable
    to a hard reject."""
    _force_dotnet_exists(monkeypatch)
    csv_out = env[2]
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_TRUNCATED, csv_out_dir=csv_out)
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    # First two rows fully parsed; third row truncated mid-record.
    assert envelope.data.row_count == 2
    assert envelope.data.truncated is True
    assert any("partial parse" in a for a in envelope.advisories)
