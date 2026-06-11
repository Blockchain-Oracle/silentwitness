"""Gap-filling unit tests for suricata_run — round-2 review findings."""

from __future__ import annotations

import asyncio
import secrets
from pathlib import Path
from typing import Any

import pytest

from silentwitness_common.types import EvidenceType
from silentwitness_mcp._lifecycle import MountCheckResult
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import (
    EvidenceNotRegisteredError,
    EvidenceRegistry,
)
from silentwitness_mcp.tools._network_common import (
    NetworkFailureReason,
    _NetworkResult,
    _tally_eve_events,
)
from silentwitness_mcp.tools._network_suricata import suricata_run

MODEL = "claude-sonnet-4-6"
_FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "network"
_EVE_SAMPLE = _FIXTURE_DIR / "suricata_eve_sample.json"
_RULES_SAMPLE = _FIXTURE_DIR / "suricata_minimal.rules"


@pytest.fixture
def pcap_file(tmp_path: Path) -> Path:
    p = tmp_path / "evidence" / "wardrive.pcap"
    p.parent.mkdir()
    p.write_bytes(secrets.token_bytes(256))
    return p


@pytest.fixture
def rules_file(tmp_path: Path) -> Path:
    p = tmp_path / "evidence" / "suricata.rules"
    p.write_bytes(_RULES_SAMPLE.read_bytes())
    return p


@pytest.fixture
def env(
    tmp_path: Path, pcap_file: Path, rules_file: Path
) -> tuple[Path, Path, AuditLogger, EvidenceRegistry]:
    case_dir = tmp_path / "case-extra-01"
    case_dir.mkdir()
    out_dir = case_dir / "tmp" / "suricata-out"
    registry = EvidenceRegistry(case_dir=case_dir)
    registry.register(pcap_file, EvidenceType.PCAP, audit_id="sift-aj-20260611-070")
    registry.register(rules_file, EvidenceType.IDS_RULES, audit_id="sift-aj-20260611-071")
    return (case_dir, out_dir, AuditLogger(case_dir, examiner="aj"), registry)


def _invoke(env: tuple[Path, Path, AuditLogger, EvidenceRegistry], pcap: Path, rules: Path) -> Any:
    case_dir, out_dir, logger, registry = env
    return asyncio.run(
        suricata_run(
            pcap,
            rules,
            out_dir,
            case_dir=case_dir,
            evidence_registry=registry,
            audit_logger=logger,
            model_used=MODEL,
        )
    )


def _force_gates_ok(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(
        "silentwitness_mcp.tools._network_suricata.check_mount",
        lambda: MountCheckResult(ok=True, advisories=[]),
    )
    fake_bin = tmp_path / "suricata"
    fake_bin.touch()
    monkeypatch.setattr(
        "silentwitness_mcp.tools._network_suricata.get_suricata_bin", lambda: fake_bin
    )
    return fake_bin


def _mock_suricata(
    monkeypatch: pytest.MonkeyPatch,
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    *,
    exit_code: int = 0,
    eve_content: bytes | None = None,
) -> None:
    _case_dir, out_dir, *_ = env

    async def _fake(*_a: Any, **_kw: Any) -> _NetworkResult:
        if exit_code == 0:
            out_dir.mkdir(parents=True, exist_ok=True)
            content = eve_content if eve_content is not None else _EVE_SAMPLE.read_bytes()
            (out_dir / "eve.json").write_bytes(content)
        return _NetworkResult(exit_code=exit_code, stdout=b"", stderr=b"", elapsed_ms=1.0)

    monkeypatch.setattr("silentwitness_mcp.tools._network_suricata._run_suricata", _fake)


# ---------------------------------------------------------------------------
# BDD: rules-file tamper
# ---------------------------------------------------------------------------


def test_tampered_rules_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """SHA256 mismatch on rules file → EVIDENCE_TAMPERED naming the rules path."""
    _force_gates_ok(monkeypatch, tmp_path)
    rules_file.write_bytes(secrets.token_bytes(256))  # tamper after registration

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("EVIDENCE_TAMPERED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.EVIDENCE_TAMPERED.value
    assert any(str(rules_file) in a for a in resp.advisories)


# ---------------------------------------------------------------------------
# Spawn OSError → TOOL_FAILED with cmd_argv
# ---------------------------------------------------------------------------


def test_spawn_oserror_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """OSError from _run_suricata → TOOL_SPAWN_FAILED with cmd_argv in provenance."""
    _force_gates_ok(monkeypatch, tmp_path)

    async def _raise(*_a: Any, **_kw: Any) -> _NetworkResult:
        raise OSError("exec permission denied")

    monkeypatch.setattr("silentwitness_mcp.tools._network_suricata._run_suricata", _raise)
    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("TOOL_SPAWN_FAILED" in a for a in resp.advisories)
    assert len(resp.data_provenance.cmd_argv) > 0


# ---------------------------------------------------------------------------
# Malformed JSON advisory surfaced
# ---------------------------------------------------------------------------


def test_malformed_eve_lines_surfaces_advisory(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Malformed JSON lines in eve.json → success=True with OUTPUT_PARTIAL advisory."""
    _force_gates_ok(monkeypatch, tmp_path)
    mixed = _EVE_SAMPLE.read_bytes() + b"\nnot-json\n"
    _mock_suricata(monkeypatch, env, eve_content=mixed)

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is True
    assert any("OUTPUT_PARTIAL" in a for a in resp.advisories)
    assert any("malformed JSON line" in a for a in resp.advisories)


# ---------------------------------------------------------------------------
# Blob persist failure → TOOL_FAILED
# ---------------------------------------------------------------------------


def test_blob_persist_failure_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """persist_blob raises OSError → BLOB_PERSIST_FAILED."""
    _force_gates_ok(monkeypatch, tmp_path)
    _mock_suricata(monkeypatch, env)
    monkeypatch.setattr(
        "silentwitness_mcp.tools._network_suricata.persist_blob",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("disk full")),
    )

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("BLOB_PERSIST_FAILED" in a for a in resp.advisories)
    assert resp.advisories[1] == NetworkFailureReason.TOOL_FAILED.value


# ---------------------------------------------------------------------------
# Audit write failure → TOOL_FAILED, orphan blob deleted
# ---------------------------------------------------------------------------


def test_audit_write_failure_refuses_and_deletes_orphan(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """append_jsonl_line raises on success path → AUDIT_WRITE_FAILED, orphan deleted."""
    _force_gates_ok(monkeypatch, tmp_path)
    _mock_suricata(monkeypatch, env)
    deleted: list[Path] = []
    monkeypatch.setattr(
        "silentwitness_mcp.tools._network_suricata.append_jsonl_line",
        lambda *_a, **_kw: (_ for _ in ()).throw(OSError("write failed")),
    )
    monkeypatch.setattr(
        "silentwitness_mcp.tools._network_suricata.delete_orphan_blob",
        lambda p: deleted.append(p),
    )

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert any("AUDIT_WRITE_FAILED" in a for a in resp.advisories)
    assert len(deleted) == 1


# ---------------------------------------------------------------------------
# Specific caveat / corroboration content
# ---------------------------------------------------------------------------


def test_caveats_contain_required_strings(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """BDD: required caveat + corroboration strings present verbatim."""
    _force_gates_ok(monkeypatch, tmp_path)
    _mock_suricata(monkeypatch, env)

    resp = _invoke(env, pcap_file, rules_file)

    assert any("corroborate against ET Open ruleset version" in c for c in resp.caveats)
    assert any("zeek_run" in c for c in resp.corroboration)


# ---------------------------------------------------------------------------
# Registry exception on rules path specifically
# ---------------------------------------------------------------------------


def test_registry_exception_on_rules_path_refuses(
    env: tuple[Path, Path, AuditLogger, EvidenceRegistry],
    pcap_file: Path,
    rules_file: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """EvidenceNotRegisteredError on rules_path → EVIDENCE_TAMPERED."""
    _force_gates_ok(monkeypatch, tmp_path)
    _case_dir, _out_dir, _logger, registry = env
    original = registry.assert_registered

    def _raise_on_rules(path: Path) -> None:
        if path == rules_file:
            raise EvidenceNotRegisteredError(str(path))
        original(path)

    monkeypatch.setattr(registry, "assert_registered", _raise_on_rules)

    resp = _invoke(env, pcap_file, rules_file)

    assert resp.success is False
    assert resp.advisories[1] in (
        NetworkFailureReason.EVIDENCE_NOT_REGISTERED.value,
        NetworkFailureReason.EVIDENCE_TAMPERED.value,
    )


# ---------------------------------------------------------------------------
# _tally_eve_events direct tests (bytes-based API)
# ---------------------------------------------------------------------------


def test_tally_eve_clean_parse() -> None:
    """Valid 8-event fixture returns correct counts with 0 malformed."""
    eve_bytes = _EVE_SAMPLE.read_bytes()
    counts, malformed = _tally_eve_events(eve_bytes)
    assert malformed == 0
    assert counts["alert"] == 1
    assert counts["dns"] == 1
    assert sum(counts.values()) == 8


def test_tally_eve_malformed_lines_counted() -> None:
    """Malformed JSON lines are counted, valid lines still parse."""
    eve_bytes = b'{"event_type":"alert"}\nnot-json\n{"event_type":"dns"}\n'
    counts, malformed = _tally_eve_events(eve_bytes)
    assert malformed == 1
    assert counts["alert"] == 1
    assert counts["dns"] == 1


def test_tally_eve_non_utf8_bytes_handled() -> None:
    """Non-UTF-8 bytes decoded with errors=replace — no exception raised."""
    eve_bytes = b'{"event_type":"alert"}\n\xff\xfe\n'
    counts, malformed = _tally_eve_events(eve_bytes)
    # The non-UTF-8 line may decode to garbage that fails JSON parse → malformed
    assert isinstance(counts, dict)
    assert isinstance(malformed, int)


def test_tally_eve_empty_bytes() -> None:
    """Empty input returns empty counts, 0 malformed."""
    counts, malformed = _tally_eve_events(b"")
    assert counts == {}
    assert malformed == 0
