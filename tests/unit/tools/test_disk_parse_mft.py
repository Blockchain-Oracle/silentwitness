"""Unit tests for :func:`parse_mft` — EZ-Tools MFTECmd CSV wrapper.

The dotnet subprocess and MFTECmd CSV-write are both mocked. Real
end-to-end coverage lives in
``tests/integration/tools/test_disk_parse_mft_integration.py``
(skipped on non-SIFT runners)."""

from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from typing import Any

import pytest
from tests.unit.tools._disk_test_helpers import (
    FakeProc as _FakeProc,
    force_dotnet as _force_dotnet,
    force_mount_ok as _force_mount_ok,
    install_dotnet_mock as _install_dotnet_mock,
)

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.tools._disk_common import DiskFailureReason
from silentwitness_mcp.tools._disk_models import MFT_CAVEATS
from silentwitness_mcp.tools.disk import parse_mft

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "disk"
_MFT_SAMPLE = _FIXTURE_DIR / "mft_sample.csv"
_MFT_TRUNCATED = _FIXTURE_DIR / "mft_truncated.csv"


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-mft-01"
    case_dir.mkdir()
    evidence = tmp_path / "MFT"
    evidence.write_bytes(secrets.token_bytes(256))
    csv_out = case_dir / "tmp" / "mft_csv_out"
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
    csv_out_override: Path | None = None,
) -> Any:
    case_dir, evidence, csv_out, logger, registry = env
    return asyncio.run(
        parse_mft(
            evidence_override or evidence,
            csv_out_override or csv_out,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def test_parse_mft_canonical_csv_parses_with_verbatim_caveats(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Canonical CSV round-trips; caveats == MFT_CAVEATS verbatim
    (story line 118 "Caveat text — verbatim discipline"); audit JSONL
    writes under case_dir/audit/; data_provenance pins
    tool+sha256+blob-under-blobs (story BDD lines 40-44)."""
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
    case_dir, _, csv_out, _, _ = env
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=csv_out)
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count == 5
    assert envelope.data.truncated is False
    assert envelope.caveats == MFT_CAVEATS
    assert envelope.data_provenance.tool == "parse_mft"
    assert envelope.data_provenance.cmd_argv[0].endswith("fake_dotnet")
    assert envelope.data_provenance.cmd_argv[1] == "/opt/zimmermantools/MFTECmd.dll"
    assert len(envelope.data_provenance.result_sha256) == 64
    assert envelope.data_provenance.stdout_path.parent == case_dir / "audit" / "blobs"
    assert (case_dir / "audit" / "disk.jsonl").exists()


def test_parse_mft_derives_is_deleted_and_si_fn_divergence(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The deleted row (InUse=False) → is_deleted=True; the timestomp
    row (Timestomped=True) → si_fn_delta=True AND Created0x10 vs
    Created0x30 diverge by > 1s (story BDD line 62-64)."""
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env)
    by_entry = {e.entry_number: e for e in envelope.data.entries}
    assert by_entry[123].is_deleted is True
    assert by_entry[123].in_use is False
    e99 = by_entry[99]
    assert e99.timestomped is True
    assert e99.si_fn_delta is True
    assert e99.u_sec_zeros is True
    assert e99.created_0x10 != e99.created_0x30
    assert (e99.created_0x30 - e99.created_0x10).total_seconds() > 1


def test_parse_mft_unregistered_evidence_refuses_without_spawning(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unregistered path → EVIDENCE_NOT_REGISTERED with no subprocess
    spawn and no csv_out_dir mkdir side-effect."""
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
    unreg = env[0].parent / "MFT_HALLUCINATED"
    unreg.write_bytes(b"x")
    calls = _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env, evidence_override=unreg)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_NOT_REGISTERED.value
    assert calls == []
    assert not env[2].exists()
    assert envelope.caveats == MFT_CAVEATS


def test_parse_mft_dotnet_missing_refuses_with_install_sh_hint(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _force_dotnet(monkeypatch, tmp_path, exists=False)
    _force_mount_ok(monkeypatch)
    calls = _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.DOTNET_NOT_FOUND.value
    assert "install.sh" in envelope.advisories[0]
    assert calls == []


def test_parse_mft_mount_not_ro_noexec_nosuid_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Story BDD §5: mount missing ro,noexec,nosuid → refuse pre-spawn."""
    _force_dotnet(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_common.check_mount",
        lambda: MountCheckResult(ok=False, advisories=["mount missing noexec"]),
    )
    calls = _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.MOUNT_NOT_RO_NOEXEC_NOSUID.value
    assert calls == []


def test_parse_mft_tampered_evidence_returns_evidence_hash_mismatch(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Story BDD §7 (line 81): SHA256 drift → EVIDENCE_HASH_MISMATCH."""
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
    env[1].write_bytes(b"DIFFERENT bytes after registration")
    calls = _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.EVIDENCE_HASH_MISMATCH.value
    assert calls == []


def test_parse_mft_tool_failed_surfaces_truncated_stderr(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
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
    assert envelope.caveats == MFT_CAVEATS


def test_parse_mft_truncated_csv_returns_partial_success(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_TRUNCATED, csv_out_dir=env[2])
    envelope = _invoke(env)
    assert envelope.success is True
    assert envelope.data is not None
    assert envelope.data.row_count == 2
    assert envelope.data.truncated is True
    assert any("partial parse" in a for a in envelope.advisories)


def test_parse_mft_csv_out_outside_case_dir_refuses(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Path-traversal guard: a csv_out outside case_dir MUST refuse
    without creating the directory tree."""
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
    bad_csv_out = tmp_path / "outside-case-dir"
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=bad_csv_out)
    envelope = _invoke(env, csv_out_override=bad_csv_out)
    assert envelope.success is False
    assert envelope.advisories[-1] == DiskFailureReason.OUTPUT_PARSE_FAILED.value
    assert "not under case_dir" in envelope.advisories[0]


def test_parse_mft_audit_row_tool_name_is_parse_mft(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Audit-trail integrity (precedent: PR #142 + #144 + #148): the
    success-path JSONL row's tool field MUST be parse_mft."""
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
    case_dir, _, csv_out, _, _ = env
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=csv_out)
    envelope = _invoke(env)
    assert envelope.success is True
    audit_log = case_dir / "audit" / "disk.jsonl"
    rows = [json.loads(line) for line in audit_log.read_text("utf-8").splitlines() if line]
    row = rows[-1]
    assert row["tool"] == "parse_mft"
    assert row["audit_id"] == envelope.audit_id


def test_parse_mft_normalizer_key_is_parse_mft_not_default(
    env: tuple[Path, Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Citation-gate regression — a future parse_amcache copy-paste
    would otherwise share parse_mft's normalizer key."""
    _force_dotnet(monkeypatch, tmp_path)
    _force_mount_ok(monkeypatch)
    from silentwitness_mcp.verification import normalizer as _norm

    captured: list[str] = []
    real = _norm.normalize_output
    monkeypatch.setattr(
        "silentwitness_mcp.tools._disk_pipeline.normalize_output",
        lambda raw, tool: (captured.append(tool), real(raw, tool))[1],
    )
    _install_dotnet_mock(monkeypatch, csv_fixture=_MFT_SAMPLE, csv_out_dir=env[2])
    envelope = _invoke(env)
    assert envelope.success is True
    assert captured == ["parse_mft"]
