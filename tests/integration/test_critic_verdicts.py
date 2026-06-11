"""Integration tests — critic agent verdict scenarios.

Three BDD scenarios using FunctionModel to deterministically produce verdicts.
No real model or network calls needed — FunctionModel intercepts the model
request and returns a structured CriticReport via the output tool protocol.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from silentwitness_agent.critic import (
    CriticDeps,
    CriticReport,
    StagedFinding,
    _load_blob,
    critique,
)
from silentwitness_common.types import Confidence


def _make_finding(
    finding_id: str = "f-001",
    observation: str = "Wireshark installed at C:\\Program Files\\Wireshark\\",
    interpretation: str = "Attacker installed a network capture tool.",
    confidence: Confidence = Confidence.HIGH,
    cited_audit_ids: list[str] | None = None,
) -> StagedFinding:
    return StagedFinding(
        finding_id=finding_id,
        observation_text=observation,
        interpretation_text=interpretation,
        confidence=confidence,
        cited_audit_ids=cited_audit_ids or [],
    )


def _make_agent(response_payload: dict) -> Agent[CriticDeps, CriticReport]:  # type: ignore[type-arg]
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool = info.output_tools[0]
        return ModelResponse(parts=[ToolCallPart(tool_name=tool.name, args=response_payload)])

    return Agent(FunctionModel(_fn), deps_type=CriticDeps, output_type=CriticReport)


# ---------------------------------------------------------------------------
# 1. AGREE scenario
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_agree_scenario_verdict_is_agree(tmp_path: Path) -> None:
    """Well-grounded finding → critic returns AGREE."""
    finding = _make_finding(
        finding_id="f-agree-001",
        observation="File C:\\Windows\\system32\\nc.exe present (hash matches known netcat).",
        interpretation="Netcat binary installed; consistent with lateral-movement staging.",
        confidence=Confidence.HIGH,
        cited_audit_ids=["sift-aj-20260613-001"],
    )
    agree_payload = {
        "verdicts": [
            {
                "finding_id": "f-agree-001",
                "verdict": "AGREE",
                "reason": "Cited blob confirms netcat binary at stated path with matching hash.",
                "suggested_revision": None,
                "missing_corroboration": [],
            }
        ],
        "tokens_spent": 80,
        "time_elapsed_ms": 120.0,
    }
    test_agent = _make_agent(agree_payload)

    with patch("silentwitness_agent.critic.build_critic", return_value=test_agent):
        report = await critique(tmp_path, "aj", [finding])

    assert len(report.verdicts) == 1
    v = report.verdicts[0]
    assert v.verdict == "AGREE"
    assert v.finding_id == "f-agree-001"
    assert report.tokens_spent >= 0  # SDK-authoritative; FunctionModel yields 0


# ---------------------------------------------------------------------------
# 2. CHALLENGE scenario
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_challenge_scenario_has_missing_corroboration(tmp_path: Path) -> None:
    """Overconfident interpretation with thin evidence → CHALLENGE with populated fields."""
    finding = _make_finding(
        finding_id="f-chal-001",
        observation="Ethereal.exe found in C:\\Tools\\. Wardriving adapter plugged in.",
        interpretation="Attacker was actively exfiltrating credit card numbers via wifi.",
        confidence=Confidence.HIGH,
        cited_audit_ids=["sift-aj-20260613-002"],
    )
    challenge_payload = {
        "verdicts": [
            {
                "finding_id": "f-chal-001",
                "verdict": "CHALLENGE",
                "reason": (
                    "The cited blob shows tool installation only; "
                    "no captured traffic or credential exfiltration evidence present."
                ),
                "suggested_revision": (
                    "Downgrade confidence to MEDIUM and qualify: "
                    "'tool installed consistent with potential capture activity; "
                    "no pcap evidence of active exfiltration.'"
                ),
                "missing_corroboration": [
                    "pcap analysis confirming plaintext credential capture via Zeek smtp.log",
                    "network traffic showing POST data with card numbers",
                ],
            }
        ],
        "tokens_spent": 120,
        "time_elapsed_ms": 200.0,
    }
    test_agent = _make_agent(challenge_payload)

    with patch("silentwitness_agent.critic.build_critic", return_value=test_agent):
        report = await critique(tmp_path, "aj", [finding])

    v = report.verdicts[0]
    assert v.verdict == "CHALLENGE"
    assert len(v.missing_corroboration) >= 1
    assert v.suggested_revision is not None


# ---------------------------------------------------------------------------
# 3. REJECT scenario
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_reject_scenario_names_hallucinated_entity(tmp_path: Path) -> None:
    """Interpretation introduces entity not present in cited blob → REJECT."""
    finding = _make_finding(
        finding_id="f-rej-001",
        observation="Ethereal installed.",
        interpretation=(
            "Attacker used C:\\Tools\\Ethereal\\ to capture credentials; "
            "shortcut found in C:\\Users\\victim\\Desktop\\Ethereal.lnk."
        ),
        confidence=Confidence.MEDIUM,
        cited_audit_ids=["sift-aj-20260613-003"],
    )
    reject_payload = {
        "verdicts": [
            {
                "finding_id": "f-rej-001",
                "verdict": "REJECT",
                "reason": (
                    "Path 'C:\\\\Tools\\\\Ethereal\\\\' not present in cited blob; "
                    "only 'C:\\\\Program Files\\\\Ethereal\\\\' appears. "
                    "Desktop shortcut path not mentioned in any cited evidence."
                ),
                "suggested_revision": None,
                "missing_corroboration": [],
            }
        ],
        "tokens_spent": 90,
        "time_elapsed_ms": 150.0,
    }
    test_agent = _make_agent(reject_payload)

    with patch("silentwitness_agent.critic.build_critic", return_value=test_agent):
        report = await critique(tmp_path, "aj", [finding])

    v = report.verdicts[0]
    assert v.verdict == "REJECT"
    assert len(v.reason) > 0
    assert "C:\\\\Tools\\\\Ethereal\\\\" in v.reason or "path" in v.reason.lower()


# ---------------------------------------------------------------------------
# 4. blob loading helpers
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_critique_empty_findings_returns_empty_report(tmp_path: Path) -> None:
    """critique() with no findings must short-circuit without calling the LLM."""
    report = await critique(tmp_path, "aj", [])
    assert report.verdicts == []
    assert report.tokens_spent == 0
    assert report.time_elapsed_ms == 0.0


def test_load_blob_returns_empty_for_missing_file(tmp_path: Path) -> None:
    result = _load_blob(tmp_path / "nonexistent.txt")
    assert result == ""


def test_load_blob_reads_small_file(tmp_path: Path) -> None:
    blob = tmp_path / "small.txt"
    blob.write_text("netcat binary present at C:\\Windows\\nc.exe", encoding="utf-8")
    result = _load_blob(blob)
    assert "netcat" in result
    assert "[TRUNCATED]" not in result


def test_load_blob_truncates_large_file(tmp_path: Path) -> None:
    from silentwitness_agent.critic import _BLOB_TRUNCATION_BYTES

    blob = tmp_path / "big.txt"
    blob.write_bytes(b"A" * (_BLOB_TRUNCATION_BYTES + 100))
    result = _load_blob(blob)
    assert "[TRUNCATED]" in result
    assert len(result) < _BLOB_TRUNCATION_BYTES + 200


# ---------------------------------------------------------------------------
# 5. critique() loads blobs from disk and cited_blob_paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_critique_loads_blob_from_audit_dir(tmp_path: Path) -> None:
    """critique() reads audit/blobs/<audit_id>.txt and passes content inline."""
    blobs_dir = tmp_path / "audit" / "blobs"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / "sift-aj-20260613-004.txt").write_text("nc.exe SHA256: deadbeef", encoding="utf-8")
    finding = _make_finding(finding_id="f-blob-001", cited_audit_ids=["sift-aj-20260613-004"])
    agree_payload = {
        "verdicts": [
            {
                "finding_id": "f-blob-001",
                "verdict": "AGREE",
                "reason": "blob confirms binary.",
                "suggested_revision": None,
                "missing_corroboration": [],
            }
        ],
        "tokens_spent": 10,
        "time_elapsed_ms": 50.0,
    }
    test_agent = _make_agent(agree_payload)

    with patch("silentwitness_agent.critic.build_critic", return_value=test_agent):
        report = await critique(tmp_path, "aj", [finding])

    assert report.verdicts[0].verdict == "AGREE"


@pytest.mark.anyio
async def test_critique_loads_blob_via_cited_blob_path(tmp_path: Path) -> None:
    """critique() reads arbitrary blob paths in finding.cited_blob_paths."""
    blob_file = tmp_path / "custom_blob.txt"
    blob_file.write_text("MFT record confirms file creation.", encoding="utf-8")
    finding = StagedFinding(
        finding_id="f-bpath-001",
        observation_text="MFT entry present.",
        interpretation_text="File was created by attacker.",
        confidence=Confidence.MEDIUM,
        cited_blob_paths=[blob_file],
    )
    agree_payload = {
        "verdicts": [
            {
                "finding_id": "f-bpath-001",
                "verdict": "AGREE",
                "reason": "MFT confirms creation.",
                "suggested_revision": None,
                "missing_corroboration": [],
            }
        ],
        "tokens_spent": 10,
        "time_elapsed_ms": 50.0,
    }
    test_agent = _make_agent(agree_payload)

    with patch("silentwitness_agent.critic.build_critic", return_value=test_agent):
        report = await critique(tmp_path, "aj", [finding])

    assert report.verdicts[0].verdict == "AGREE"


@pytest.mark.anyio
async def test_critique_patches_zero_elapsed_ms(tmp_path: Path) -> None:
    """When the model returns time_elapsed_ms=0.0, critique() substitutes wall-clock elapsed."""
    finding = _make_finding()
    zero_time_payload = {
        "verdicts": [
            {
                "finding_id": "f-001",
                "verdict": "AGREE",
                "reason": "ok.",
                "suggested_revision": None,
                "missing_corroboration": [],
            }
        ],
        "tokens_spent": 5,
        "time_elapsed_ms": 0.0,
    }
    test_agent = _make_agent(zero_time_payload)

    with patch("silentwitness_agent.critic.build_critic", return_value=test_agent):
        report = await critique(tmp_path, "aj", [finding])

    assert report.time_elapsed_ms > 0.0
