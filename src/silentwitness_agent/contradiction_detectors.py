"""Deterministic contradiction detectors (architecture §5.5).

These complement the LLM critic with cheap, model-free checks for the three
classic DFIR overclaims. Each detector inspects a staged finding (its
interpretation text + the verbatim cited evidence) and, on a hit, returns a
``CriticVerdictRecord`` with ``verdict="CHALLENGE"``. They run on every critic
fire regardless of model availability, so the self-correction loop has a
deterministic floor.

The detectors are intentionally conservative: they fire only when an overclaim
is paired with evidence that demonstrably does NOT support it (presence-only
artifacts for an execution claim, no memory artifact for a live-process claim,
a named timestamp absent from all cited evidence). A finding that already cites
the corroborating artifact is left for the LLM critic to judge.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from silentwitness_agent.critic import CriticVerdictRecord, StagedFinding

# Execution language in an interpretation ("the binary was executed / ran").
_EXECUTION_CLAIM = re.compile(
    r"\b(execut|ran\b|was run\b|were run\b|launch|invok|double[- ]?click|"
    r"started running|process creat|spawned)",
    re.IGNORECASE,
)
# Presence-only artifacts — prove a file EXISTED, not that it ran.
_PRESENCE_EVIDENCE = re.compile(
    r"\b(MFT\b|\$MFT|Amcache|Shimcache|AppCompatCache|Shellbag|UsnJrnl|\$J\b)",
    re.IGNORECASE,
)
# Artifacts that DO prove execution — if any is cited, no overclaim.
_EXECUTION_EVIDENCE = re.compile(
    r"\b(Prefetch|last run|run count|EventID\s*4688|\b4688\b|EventID\s*4624|\b4624\b|"
    r"ProcessCreat|BAM\b|DAM\b|UserAssist|pslist|psscan|cmdline)",
    re.IGNORECASE,
)

# Live/running-process language.
_LIVE_PROCESS_CLAIM = re.compile(
    r"\b(running process|active process|process is running|process was running|"
    r"live process|currently running|in memory|resident in memory|injected into)",
    re.IGNORECASE,
)
# Memory-derived artifacts that could corroborate a live process.
_MEMORY_EVIDENCE = re.compile(
    r"\b(pslist|psscan|pstree|malfind|netscan|EPROCESS|ImageFileName|memory image|"
    r"\bPID\s*\d+|handles|dlllist)",
    re.IGNORECASE,
)

# ISO-8601-ish timestamps (date, optional time): 2024-11-12 or 2024-11-12T08:30:00.
_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?\b")


def _evidence_blob(finding: StagedFinding) -> str:
    return "\n".join(finding.cited_evidence)


def _challenge(finding: StagedFinding, reason: str, missing: Iterable[str]) -> CriticVerdictRecord:
    return CriticVerdictRecord(
        finding_id=finding.finding_id,
        verdict="CHALLENGE",
        reason=reason,
        suggested_revision=None,
        missing_corroboration=list(missing),
    )


def detect_execution_overclaim(finding: StagedFinding) -> CriticVerdictRecord | None:
    """CHALLENGE when an interpretation claims execution but the cited evidence is
    presence-only (MFT/Amcache/Shimcache/Shellbags) with no execution artifact."""
    if not _EXECUTION_CLAIM.search(finding.interpretation_text):
        return None
    evidence = _evidence_blob(finding)
    if _EXECUTION_EVIDENCE.search(evidence):
        return None  # execution is actually corroborated
    if not _PRESENCE_EVIDENCE.search(evidence):
        return None  # no presence-only artifact to overclaim from — leave to LLM
    return _challenge(
        finding,
        "EXECUTION_OVERCLAIM: the interpretation asserts execution, but the cited "
        "evidence proves only file PRESENCE (MFT/Amcache/Shimcache/Shellbags), which "
        "does not establish that the program ran.",
        ["an execution artifact (Prefetch run, EventID 4688, BAM/DAM, or UserAssist)"],
    )


def detect_ghost_process(finding: StagedFinding) -> CriticVerdictRecord | None:
    """CHALLENGE when an interpretation claims a live/running process but no
    memory-derived artifact is cited to corroborate it."""
    if not _LIVE_PROCESS_CLAIM.search(finding.interpretation_text):
        return None
    if _MEMORY_EVIDENCE.search(_evidence_blob(finding)):
        return None
    return _challenge(
        finding,
        "GHOST_PROCESS: the interpretation asserts a running/in-memory process, but "
        "no memory-derived artifact (pslist/psscan/netscan/malfind) is cited to show "
        "the process was actually resident.",
        ["a memory analysis artifact (Volatility pslist/psscan/netscan)"],
    )


def detect_timestamp_paradox(finding: StagedFinding) -> CriticVerdictRecord | None:
    """CHALLENGE when the interpretation names a specific timestamp that appears in
    NONE of the cited evidence — an ungrounded temporal claim."""
    interp_ts = set(_TIMESTAMP.findall(finding.interpretation_text))
    if not interp_ts:
        return None
    evidence_ts = set(_TIMESTAMP.findall(_evidence_blob(finding)))
    ungrounded = sorted(t for t in interp_ts if t not in evidence_ts)
    if not ungrounded:
        return None
    return _challenge(
        finding,
        "TIMESTAMP_PARADOX: the interpretation states timestamp(s) "
        f"{', '.join(ungrounded)} that do not appear in any cited evidence — the "
        "temporal claim is not grounded in the bytes you cited.",
        ["a cited record whose timestamp matches the stated time"],
    )


_DETECTORS = (detect_execution_overclaim, detect_ghost_process, detect_timestamp_paradox)


def run_contradiction_detectors(
    findings: Sequence[StagedFinding],
) -> list[CriticVerdictRecord]:
    """Run all detectors over every staged finding; return the CHALLENGE verdicts.

    At most one verdict per (finding, detector) — a finding can collect multiple
    distinct contradictions."""
    verdicts: list[CriticVerdictRecord] = []
    for finding in findings:
        for detector in _DETECTORS:
            verdict = detector(finding)
            if verdict is not None:
                verdicts.append(verdict)
    return verdicts


__all__ = [
    "detect_execution_overclaim",
    "detect_ghost_process",
    "detect_timestamp_paradox",
    "run_contradiction_detectors",
]
