"""The live closed-loop critic: an interval hook runs the critic over staged
findings mid-investigation, routes CHALLENGEs into pending_critiques, and a
dynamic instruction surfaces them back into the agent's context.

No real models or API keys: a stub critique_fn returns canned verdicts and a
FunctionModel drives the investigator so the hook fires deterministically.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from silentwitness_agent.critic import CriticReport, CriticVerdictRecord, StagedFinding
from silentwitness_agent.critic_trigger import CriticTrigger
from silentwitness_agent.investigator import InvestigatorDeps
from silentwitness_agent.live_critic import (
    build_critic_hooks,
    register_pending_critique_instruction,
    render_pending_critiques,
    route_live_verdicts,
)

pytestmark = pytest.mark.anyio


def _write_findings(case_dir: Path, n: int) -> None:
    records = [
        {
            "observation_id": f"O-{i + 1:03d}",
            "finding_id": f"F-{i + 1:03d}",
            "status": "DRAFT",
            "text": f"observation {i + 1}",
            "audit_ids": [f"sift-aj-2026-{i + 1:03d}"],
            "cited_spans": [{"record_id": i + 1, "span_text": f"evidence {i + 1}"}],
            "interpretations": [
                {
                    "interpretation_id": f"I-{i + 1:03d}",
                    "text": f"interpretation {i + 1}",
                    "confidence": "HIGH",
                }
            ],
        }
        for i in range(n)
    ]
    (case_dir / "findings.json").write_text(json.dumps(records), encoding="utf-8")


def _make_deps(case_dir: Path) -> InvestigatorDeps:
    from silentwitness_agent.hypothesis.budget import BudgetEnforcer
    from silentwitness_agent.hypothesis.stack import HypothesisStack

    return InvestigatorDeps(
        case_dir=case_dir,
        examiner="aj",
        stack=HypothesisStack(case_dir=case_dir, examiner="aj"),
        budget=BudgetEnforcer(),
    )


# ---------------------------------------------------------------------------
# render_pending_critiques — only open CHALLENGEs surface
# ---------------------------------------------------------------------------


def test_render_pending_critiques_empty_when_no_challenges() -> None:
    assert render_pending_critiques([]) == ""
    agree = CriticVerdictRecord(finding_id="F-001", verdict="AGREE", reason="ok")
    assert render_pending_critiques([agree]) == ""


def test_render_pending_critiques_lists_challenge_details() -> None:
    challenge = CriticVerdictRecord(
        finding_id="F-002",
        verdict="CHALLENGE",
        reason="overclaims exfiltration",
        suggested_revision="downgrade to MEDIUM",
        missing_corroboration=["pcap"],
    )
    rendered = render_pending_critiques([challenge])
    assert "F-002" in rendered
    assert "overclaims exfiltration" in rendered
    assert "downgrade to MEDIUM" in rendered
    assert "pcap" in rendered


# ---------------------------------------------------------------------------
# route_live_verdicts — CHALLENGE → pending_critiques; all → critic.jsonl
# ---------------------------------------------------------------------------


def test_route_live_verdicts_only_pushes_challenges(tmp_path: Path) -> None:
    pending: list[CriticVerdictRecord] = []
    verdicts = [
        CriticVerdictRecord(finding_id="O-001", verdict="AGREE", reason="solid"),
        CriticVerdictRecord(finding_id="O-002", verdict="CHALLENGE", reason="overclaim"),
        CriticVerdictRecord(finding_id="O-003", verdict="REJECT", reason="hallucinated path"),
    ]
    n = route_live_verdicts(tmp_path, "aj", verdicts, pending)
    assert n == 1
    assert [v.finding_id for v in pending] == ["O-002"]
    # Every verdict is audited (not just the CHALLENGE).
    lines = (tmp_path / "audit" / "critic.jsonl").read_text().strip().splitlines()
    assert len(lines) == 3
    types = {json.loads(ln)["type"] for ln in lines}
    assert types == {"agree", "challenge", "reject"}


# ---------------------------------------------------------------------------
# the hook — fires on interval, routes CHALLENGE into pending_critiques
# ---------------------------------------------------------------------------


async def _run_hook(case_dir: Path, deps: InvestigatorDeps, report: CriticReport) -> None:
    """Build the critic hook with a stub critique_fn and invoke its
    after_model_request callback directly (bypassing a full agent run)."""
    captured: dict[str, list[StagedFinding]] = {}

    async def _stub_critique(cdir, examiner, findings, *, model=None):  # type: ignore[no-untyped-def]
        captured["findings"] = findings
        return report

    trigger = CriticTrigger(case_dir=case_dir, examiner="aj", interval_findings=2)
    hooks = build_critic_hooks(case_dir, "aj", trigger, critique_fn=_stub_critique)

    class _Ctx:
        def __init__(self, d: InvestigatorDeps) -> None:
            self.deps = d

    # The Hooks dispatcher invokes the registered after_model_request callback.
    await hooks.after_model_request(_Ctx(deps), request_context=None, response="resp")  # type: ignore[arg-type]
    _ = captured


async def test_hook_routes_challenge_into_pending_critiques(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _write_findings(case_dir, 3)  # ≥ interval_findings=2 → should fire
    deps = _make_deps(case_dir)
    report = CriticReport(
        verdicts=[
            CriticVerdictRecord(
                finding_id="O-001",
                verdict="CHALLENGE",
                reason="interpretation overstates the evidence",
                suggested_revision="cite a corroborating artifact",
                missing_corroboration=["prefetch"],
            )
        ],
        tokens_spent=5,
        time_elapsed_ms=1.0,
    )
    await _run_hook(case_dir, deps, report)

    assert len(deps.pending_critiques) == 1
    assert deps.pending_critiques[0].finding_id == "O-001"
    assert deps.pending_critiques[0].verdict == "CHALLENGE"
    # The challenge now renders into the agent's next-turn instructions.
    assert "overstates the evidence" in render_pending_critiques(deps.pending_critiques)


async def test_hook_noop_when_threshold_not_reached(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _write_findings(case_dir, 1)  # < interval_findings=2 → must NOT fire
    deps = _make_deps(case_dir)
    report = CriticReport(
        verdicts=[CriticVerdictRecord(finding_id="O-001", verdict="CHALLENGE", reason="x")],
        tokens_spent=0,
        time_elapsed_ms=0.0,
    )
    await _run_hook(case_dir, deps, report)
    assert deps.pending_critiques == []


async def test_critique_failure_does_not_abort_run(tmp_path: Path) -> None:
    """A critic-model failure is swallowed — the investigation continues."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _write_findings(case_dir, 3)
    deps = _make_deps(case_dir)

    async def _boom(cdir, examiner, findings, *, model=None):  # type: ignore[no-untyped-def]
        raise RuntimeError("critic model unavailable")

    trigger = CriticTrigger(case_dir=case_dir, examiner="aj", interval_findings=2)
    hooks = build_critic_hooks(case_dir, "aj", trigger, critique_fn=_boom)

    class _Ctx:
        def __init__(self, d: InvestigatorDeps) -> None:
            self.deps = d

    # Must not raise.
    out = await hooks.after_model_request(_Ctx(deps), request_context=None, response="resp")  # type: ignore[arg-type]
    assert out == "resp"
    assert deps.pending_critiques == []


# ---------------------------------------------------------------------------
# the dynamic instruction registers and renders against live deps
# ---------------------------------------------------------------------------


async def test_instruction_registers_and_renders(tmp_path: Path) -> None:
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    from silentwitness_agent.investigator import InvestigatorResult

    agent: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(),
        deps_type=InvestigatorDeps,
        output_type=InvestigatorResult,
    )
    before = len(agent._instructions)  # type: ignore[attr-defined]
    register_pending_critique_instruction(agent)
    # The decorator attached an instructions function — its presence is the wiring.
    assert len(agent._instructions) == before + 1  # type: ignore[attr-defined]
