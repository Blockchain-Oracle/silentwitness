"""Deterministic contradiction detectors — model-free CHALLENGE floor."""

from __future__ import annotations

from silentwitness_agent.contradiction_detectors import (
    detect_execution_overclaim,
    detect_ghost_process,
    detect_timestamp_paradox,
    run_contradiction_detectors,
)
from silentwitness_agent.critic import StagedFinding
from silentwitness_common.types import Confidence


def _finding(
    interpretation: str,
    evidence: tuple[str, ...],
    *,
    finding_id: str = "O-001",
    observation: str = "observation text",
) -> StagedFinding:
    return StagedFinding(
        finding_id=finding_id,
        observation_text=observation,
        interpretation_text=interpretation,
        confidence=Confidence.HIGH,
        cited_evidence=evidence,
    )


# ---------------------------------------------------------------------------
# EXECUTION_OVERCLAIM
# ---------------------------------------------------------------------------


def test_execution_overclaim_fires_on_presence_only_evidence() -> None:
    f = _finding(
        "The attacker executed nc.exe to open a reverse shell.",
        ("MFT path=Users/fredr/Downloads/nc.exe size=45056",),
    )
    v = detect_execution_overclaim(f)
    assert v is not None
    assert v.verdict == "CHALLENGE"
    assert "EXECUTION_OVERCLAIM" in v.reason
    assert v.missing_corroboration


def test_execution_overclaim_silent_when_execution_artifact_cited() -> None:
    f = _finding(
        "The attacker executed nc.exe.",
        ("Prefetch NC.EXE-1234.pf run count=3 last run 2024-11-12",),
    )
    assert detect_execution_overclaim(f) is None


def test_execution_overclaim_silent_without_execution_claim() -> None:
    f = _finding(
        "nc.exe was present in the Downloads folder.",
        ("MFT path=Users/fredr/Downloads/nc.exe",),
    )
    assert detect_execution_overclaim(f) is None


def test_execution_overclaim_silent_without_presence_evidence() -> None:
    # Execution claim but the cited evidence is neither presence nor execution —
    # nothing to overclaim from; leave it to the LLM critic.
    f = _finding("The attacker executed a tool.", ("zeek conn 10.0.0.5 -> evil.example.com",))
    assert detect_execution_overclaim(f) is None


# ---------------------------------------------------------------------------
# GHOST_PROCESS
# ---------------------------------------------------------------------------


def test_ghost_process_fires_without_memory_evidence() -> None:
    f = _finding(
        "A malicious process was running in memory at the time of capture.",
        ("MFT path=Windows/Temp/svc.exe",),
    )
    v = detect_ghost_process(f)
    assert v is not None
    assert "GHOST_PROCESS" in v.reason


def test_ghost_process_silent_with_memory_evidence() -> None:
    f = _finding(
        "A malicious process was running in memory.",
        ("vol pslist: PID 1208 svc.exe EPROCESS 0xfffe...",),
    )
    assert detect_ghost_process(f) is None


# ---------------------------------------------------------------------------
# TIMESTAMP_PARADOX
# ---------------------------------------------------------------------------


def test_timestamp_paradox_fires_on_ungrounded_timestamp() -> None:
    f = _finding(
        "The file was created on 2024-11-12 during the intrusion.",
        ("MFT path=x size=10 created 2023-01-01",),
    )
    v = detect_timestamp_paradox(f)
    assert v is not None
    assert "TIMESTAMP_PARADOX" in v.reason
    assert "2024-11-12" in v.reason


def test_timestamp_paradox_silent_when_timestamp_grounded() -> None:
    f = _finding(
        "The file was created on 2024-11-12.",
        ("MFT path=x created 2024-11-12T08:30:00 modified 2024-11-12",),
    )
    assert detect_timestamp_paradox(f) is None


def test_timestamp_paradox_silent_without_named_timestamp() -> None:
    f = _finding("The file was created during the intrusion.", ("MFT path=x",))
    assert detect_timestamp_paradox(f) is None


# ---------------------------------------------------------------------------
# run_contradiction_detectors — aggregate
# ---------------------------------------------------------------------------


def test_run_detectors_collects_multiple_contradictions() -> None:
    findings = [
        _finding(
            "Attacker executed nc.exe.",
            ("MFT path=nc.exe",),
            finding_id="O-001",
        ),
        _finding(
            "A process was running in memory; activity seen 2025-06-01.",
            ("MFT path=svc.exe",),
            finding_id="O-002",
        ),
        _finding("nc.exe was present.", ("MFT path=nc.exe",), finding_id="O-003"),
    ]
    verdicts = run_contradiction_detectors(findings)
    ids = sorted(v.finding_id for v in verdicts)
    # O-001 execution overclaim; O-002 ghost process + timestamp paradox; O-003 clean.
    assert ids == ["O-001", "O-002", "O-002"]
    assert all(v.verdict == "CHALLENGE" for v in verdicts)
