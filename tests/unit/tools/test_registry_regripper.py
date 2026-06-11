"""Unit tests for :func:`regripper_run` — rip.pl wrapper."""

from __future__ import annotations

import asyncio
import json
import secrets
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceMissingOnDiskError,
    EvidenceRegistry,
    EvidenceRegistryError,
)
from silentwitness_mcp.tools.registry import (
    REGRIPPER_CAVEATS,
    RegripperOutput,
    regripper_run,
)

MODEL = "claude-sonnet-4-6"

_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "registry"
_COMPNAME_FIXTURE = _FIXTURE_DIR / "rip_compname.txt"
_PLUGINS_FIXTURE = _FIXTURE_DIR / "rip_plugins_list.txt"

_KNOWN_PLUGINS = frozenset(
    line.strip() for line in _PLUGINS_FIXTURE.read_text().splitlines() if line.strip()
)


class FakeProc:
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


@pytest.fixture(autouse=True)
def _reset_plugin_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset process-lifetime plugin cache between tests to prevent cross-test pollution."""
    monkeypatch.setattr("silentwitness_mcp.tools.registry._KNOWN_PLUGINS", None)


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-rr-01"
    case_dir.mkdir()
    hive = tmp_path / "SYSTEM"
    hive.write_bytes(secrets.token_bytes(256))
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(hive, EvidenceType.OTHER, audit_id="sift-aj-20260611-020")
    return case_dir, hive, AuditLogger(case_dir, examiner="aj"), registry


def _invoke(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    plugin: str = "compname",
    *,
    hive_override: Path | None = None,
) -> Any:
    case_dir, hive, logger, registry = env
    return asyncio.run(
        regripper_run(
            hive_override or hive,
            plugin,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def force_rip_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, exists: bool = True) -> None:
    fake = tmp_path / "fake_rip.pl"
    if exists:
        fake.touch()
    monkeypatch.setattr("silentwitness_mcp.tools.registry.RIP_BIN", fake)


def force_plugins(
    monkeypatch: pytest.MonkeyPatch, plugins: frozenset[str] = _KNOWN_PLUGINS
) -> None:
    async def _fake() -> frozenset[str]:
        return plugins

    monkeypatch.setattr("silentwitness_mcp.tools.registry._get_known_plugins", _fake)


def install_rip_mock(
    monkeypatch: pytest.MonkeyPatch,
    *,
    fixture: Path = _COMPNAME_FIXTURE,
    returncode: int = 0,
    stderr: bytes = b"",
) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []
    text = fixture.read_bytes()
    proc = FakeProc(stdout=text, stderr=stderr, returncode=returncode)

    async def _fake(*argv: str, **_kw: Any) -> FakeProc:
        calls.append(argv)
        return proc

    monkeypatch.setattr("silentwitness_mcp.tools.registry.asyncio.create_subprocess_exec", _fake)
    return calls


def force_mount_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    from silentwitness_mcp._lifecycle import MountCheckResult

    monkeypatch.setattr(
        "silentwitness_mcp.tools.registry.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )


def force_mount_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    from silentwitness_mcp._lifecycle import MountCheckResult

    monkeypatch.setattr(
        "silentwitness_mcp.tools.registry.check_mount",
        lambda: MountCheckResult(ok=False, advisories=["mount missing noexec"]),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_regripper_run_canonical_success(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Canonical compname run: success, correct caveats, cmd_argv, audit row."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    calls = install_rip_mock(monkeypatch)
    case_dir, _, _, _ = env
    envelope = _invoke(env)

    assert envelope.success is True
    assert isinstance(envelope.data, RegripperOutput)
    assert envelope.data.plugin_name == "compname"
    assert envelope.data.line_count > 0
    assert envelope.caveats == REGRIPPER_CAVEATS
    assert calls[0][1] == "-r"
    assert calls[0][3] == "-p"
    assert calls[0][4] == "compname"
    assert envelope.data_provenance.tool == "regripper_run"
    assert (case_dir / "audit" / "registry.jsonl").exists()


def test_regripper_run_parsed_keys_extracted(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """parsed_keys contains the 'Key path:' lines from the fixture."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    install_rip_mock(monkeypatch)
    envelope = _invoke(env)

    assert envelope.success is True
    assert len(envelope.data.parsed_keys) >= 2
    assert all("SYSTEM" in k for k in envelope.data.parsed_keys)


def test_regripper_run_audit_log_tool_name(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Audit JSONL row carries tool == 'regripper_run' and plugin_name."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    install_rip_mock(monkeypatch)
    case_dir = env[0]
    _invoke(env)
    rows = [
        json.loads(line)
        for line in (case_dir / "audit" / "registry.jsonl").read_text().splitlines()
        if line
    ]
    assert rows[-1]["tool"] == "regripper_run"
    assert rows[-1]["params"]["plugin_name"] == "compname"


def test_regripper_run_unknown_plugin_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unknown plugin → PLUGIN_NOT_FOUND; no subprocess spawn."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    calls = install_rip_mock(monkeypatch)
    envelope = _invoke(env, "totally_made_up_plugin")
    assert envelope.success is False
    assert "PLUGIN_NOT_FOUND: totally_made_up_plugin" in envelope.advisories[0]
    assert "rip.pl" in envelope.advisories[0]
    assert envelope.advisories[1] == "PLUGIN_NOT_FOUND"
    assert calls == []


def test_regripper_run_unregistered_hive_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Unregistered hive → EVIDENCE_NOT_REGISTERED; no subprocess spawn."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    calls = install_rip_mock(monkeypatch)
    ghost = tmp_path / "GHOST_HIVE"
    ghost.write_bytes(b"fake")
    envelope = _invoke(env, hive_override=ghost)
    assert envelope.success is False
    assert "EVIDENCE_NOT_REGISTERED" in envelope.advisories[0]
    assert envelope.advisories[1] == "EVIDENCE_NOT_REGISTERED"
    assert calls == []


def test_regripper_run_tampered_evidence_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SHA256 drift after registration → EVIDENCE_HASH_MISMATCH; no spawn."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    calls = install_rip_mock(monkeypatch)
    _, hive, _, _ = env
    hive.write_bytes(b"TAMPERED")
    envelope = _invoke(env)
    assert envelope.success is False
    assert "EVIDENCE_HASH_MISMATCH" in envelope.advisories[0]
    assert envelope.advisories[1] == "EVIDENCE_HASH_MISMATCH"
    assert calls == []


@pytest.mark.parametrize(
    "exc_factory,expected_text",
    [
        (lambda hive: EvidenceMissingOnDiskError(hive), "EVIDENCE_MISSING_ON_DISK"),
        (lambda _: EvidenceRegistryError("manifest corrupt"), "manifest corrupt"),
    ],
    ids=["missing_on_disk", "registry_error"],
)
def test_regripper_run_verify_hash_exception_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    exc_factory: Any,
    expected_text: str,
) -> None:
    """verify_hash exceptions → EVIDENCE_HASH_MISMATCH reason; no subprocess spawn."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    calls = install_rip_mock(monkeypatch)
    _, hive, _, registry = env
    exc = exc_factory(hive)
    monkeypatch.setattr(registry, "verify_hash", lambda _p: (_ for _ in ()).throw(exc))
    envelope = _invoke(env)
    assert envelope.success is False
    assert expected_text in envelope.advisories[0]
    assert envelope.advisories[1] == "EVIDENCE_HASH_MISMATCH"
    assert calls == []


def test_regripper_run_mount_fail_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Bad mount → MOUNT_NOT_RO_NOEXEC_NOSUID; no subprocess spawn; JSONL row written."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_fail(monkeypatch)
    calls = install_rip_mock(monkeypatch)
    case_dir = env[0]
    envelope = _invoke(env)
    assert envelope.success is False
    assert "MOUNT_NOT_RO_NOEXEC_NOSUID" in envelope.advisories[0]
    assert envelope.advisories[1] == "MOUNT_NOT_RO_NOEXEC_NOSUID"
    assert calls == []
    rows = [
        json.loads(line)
        for line in (case_dir / "audit" / "registry.jsonl").read_text().splitlines()
        if line
    ]
    assert rows[-1]["result_summary"]["reason"] == "MOUNT_NOT_RO_NOEXEC_NOSUID"
    assert rows[-1]["stdout_path"] == "/dev/null"


def test_regripper_run_parse_failed_on_nonzero_exit(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """rip.pl exit 1 with stderr → PARSE_FAILED; exit_code in audit params."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    install_rip_mock(monkeypatch, returncode=1, stderr=b"ERROR: unable to open hive: bad magic\n")
    case_dir = env[0]
    envelope = _invoke(env)
    assert envelope.success is False
    assert "PARSE_FAILED" in envelope.advisories[0]
    assert "exit 1" in envelope.advisories[0]
    assert "bad magic" in envelope.advisories[0]
    assert envelope.advisories[1] == "PARSE_FAILED"
    rows = [
        json.loads(line)
        for line in (case_dir / "audit" / "registry.jsonl").read_text().splitlines()
        if line
    ]
    assert rows[-1]["params"]["exit_code"] == 1


def test_regripper_run_timeout_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """rip.pl timeout → PARSE_FAILED 'timed out'; no success data returned."""
    force_rip_bin(monkeypatch, tmp_path)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    install_rip_mock(monkeypatch)

    async def _timeout(coro: Any, **_kw: Any) -> Any:
        coro.close()
        raise TimeoutError

    monkeypatch.setattr("silentwitness_mcp.tools.registry.asyncio.wait_for", _timeout)
    envelope = _invoke(env)
    assert envelope.success is False
    assert "PARSE_FAILED" in envelope.advisories[0]
    assert "timed out" in envelope.advisories[0]
    assert envelope.advisories[1] == "PARSE_FAILED"
    assert envelope.data is None


def test_regripper_run_rip_not_installed_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """rip.pl absent → REGRIPPER_NOT_INSTALLED; no subprocess spawn."""
    force_rip_bin(monkeypatch, tmp_path, exists=False)
    force_plugins(monkeypatch)
    force_mount_ok(monkeypatch)
    calls = install_rip_mock(monkeypatch)
    envelope = _invoke(env)
    assert envelope.success is False
    assert "REGRIPPER_NOT_INSTALLED" in envelope.advisories[0]
    assert "SIFT 2026 saltstack" in envelope.advisories[0]
    assert envelope.advisories[1] == "REGRIPPER_NOT_INSTALLED"
    assert calls == []
