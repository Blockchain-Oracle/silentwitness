"""Unit coverage for review._run_critic_pass branch behavior.

The critic pass is best-effort over the model call but must surface verdict-write
failures; it also skips already-reviewed / malformed findings. These drive those
branches without a real model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from rich.console import Console

from silentwitness_agent.cli_commands.review import _run_critic_pass
from silentwitness_agent.config import BudgetConfig, SilentWitnessConfig
from silentwitness_agent.critic import CriticReport


def _write(case_dir: Path, records: list[dict]) -> None:  # type: ignore[type-arg]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")


def _obs(oid: str, iid: str, conf: str = "MEDIUM") -> dict:  # type: ignore[type-arg]
    return {
        "observation_id": oid,
        "text": f"observation {oid}",
        "audit_ids": ["aid-1"],
        "interpretations": [
            {"interpretation_id": iid, "text": f"interp {iid}", "confidence": conf}
        ],
    }


def _finding(fid: str, oid: str, iid: str, **extra: object) -> dict:  # type: ignore[type-arg]
    return {
        "finding_id": fid,
        "observation_id": oid,
        "interpretation_id": iid,
        "status": "DRAFT",
        **extra,
    }


def test_critic_pass_swallows_model_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path, [_obs("O-001", "I-001"), _finding("F-001", "O-001", "I-001")])

    async def _boom(*_a: object, **_k: object) -> CriticReport:
        raise RuntimeError("no API key")

    monkeypatch.setattr("silentwitness_agent.critic.critique", _boom)
    # Must NOT raise — best-effort degrades to listing.
    _run_critic_pass(tmp_path, "aj", err=Console(stderr=True))


def test_critic_pass_skips_reviewed_and_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, int] = {}

    async def _capture(  # type: ignore[type-arg]
        case_dir: Path, examiner: str, staged: list, **kwargs: object
    ) -> CriticReport:
        seen["n"] = len(staged)
        return CriticReport(verdicts=[], tokens_spent=0, time_elapsed_ms=0.0)

    monkeypatch.setattr("silentwitness_agent.critic.critique", _capture)
    _write(
        tmp_path,
        [
            _obs("O-001", "I-001"),
            _obs("O-002", "I-002", conf="not-a-confidence"),  # bad confidence → LOW fallback
            _finding("F-001", "O-001", "I-001"),  # fresh → staged
            _finding(
                "F-002", "O-002", "I-002"
            ),  # fresh, bad-confidence interp → still staged at LOW
            _finding("F-003", "O-404", "I-404"),  # missing obs/interp → skipped
            _finding(
                "F-004", "O-001", "I-001", critic_status="AGREED"
            ),  # already reviewed → skipped
        ],
    )
    _run_critic_pass(tmp_path, "aj", err=Console(stderr=True))
    assert seen["n"] == 2  # F-001 + F-002 only


def test_critic_pass_uses_configured_usage_limits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    async def _capture(  # type: ignore[type-arg]
        case_dir: Path, examiner: str, staged: list, **kwargs: object
    ) -> CriticReport:
        seen.update(kwargs)
        return CriticReport(verdicts=[], tokens_spent=0, time_elapsed_ms=0.0)

    monkeypatch.setattr("silentwitness_agent.critic.critique", _capture)
    _write(tmp_path, [_obs("O-001", "I-001"), _finding("F-001", "O-001", "I-001")])
    config = SilentWitnessConfig(budget=BudgetConfig(max_steps=9, max_tokens=123_456))

    _run_critic_pass(tmp_path, "aj", err=Console(stderr=True), config=config)

    assert seen["request_limit"] == 9
    assert seen["total_token_limit"] == 123_456


def test_critic_pass_no_drafts_is_noop(tmp_path: Path) -> None:
    _write(tmp_path, [_obs("O-001", "I-001")])  # observation but no Finding record
    _run_critic_pass(tmp_path, "aj", err=Console(stderr=True))  # returns early, no error
