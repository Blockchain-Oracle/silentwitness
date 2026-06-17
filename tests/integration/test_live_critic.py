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
from pydantic_ai import RunUsage

from silentwitness_agent.critic import CriticReport, CriticVerdictRecord, StagedFinding
from silentwitness_agent.critic_trigger import CriticTrigger
from silentwitness_agent.investigator import InvestigatorDeps
from silentwitness_agent.live_critic import (
    build_critic_hooks,
    build_live_critic_hooks,
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

    async def _stub_critique(cdir, examiner, findings, **kwargs):  # type: ignore[no-untyped-def]
        captured["findings"] = findings
        return report

    trigger = CriticTrigger(case_dir=case_dir, examiner="aj", interval_findings=2)
    hooks = build_critic_hooks(case_dir, "aj", trigger, critique_fn=_stub_critique)

    class _Ctx:
        def __init__(self, d: InvestigatorDeps) -> None:
            self.deps = d
            self.usage = RunUsage()

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

    async def _boom(cdir, examiner, findings, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("critic model unavailable")

    trigger = CriticTrigger(case_dir=case_dir, examiner="aj", interval_findings=2)
    hooks = build_critic_hooks(case_dir, "aj", trigger, critique_fn=_boom)

    class _Ctx:
        def __init__(self, d: InvestigatorDeps) -> None:
            self.deps = d
            self.usage = RunUsage()

    # Must not raise.
    out = await hooks.after_model_request(_Ctx(deps), request_context=None, response="resp")  # type: ignore[arg-type]
    assert out == "resp"
    assert deps.pending_critiques == []


# ---------------------------------------------------------------------------
# watermark discipline — the Critical fix
# ---------------------------------------------------------------------------


async def test_routing_failure_does_not_advance_watermark(tmp_path: Path) -> None:
    """If routing fails, the window must NOT be marked reviewed — it re-fires."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _write_findings(case_dir, 3)
    deps = _make_deps(case_dir)

    async def _stub(cdir, examiner, findings, **kwargs):  # type: ignore[no-untyped-def]
        return CriticReport(
            verdicts=[CriticVerdictRecord(finding_id="O-001", verdict="AGREE", reason="ok")],
            tokens_spent=0,
            time_elapsed_ms=0.0,
        )

    trigger = CriticTrigger(case_dir=case_dir, examiner="aj", interval_findings=2)
    before = trigger._state.last_critic_finding_count
    hooks = build_critic_hooks(case_dir, "aj", trigger, critique_fn=_stub)

    class _Ctx:
        def __init__(self, d: InvestigatorDeps) -> None:
            self.deps = d
            self.usage = RunUsage()

    import silentwitness_agent.live_critic as lc

    def _boom_route(*a: object, **k: object) -> int:
        raise OSError("disk full")

    original = lc.route_live_verdicts
    lc.route_live_verdicts = _boom_route  # type: ignore[assignment]
    try:
        await hooks.after_model_request(_Ctx(deps), request_context=None, response="r")  # type: ignore[arg-type]
    finally:
        lc.route_live_verdicts = original  # type: ignore[assignment]
    # Watermark untouched → the window will be re-reviewed, not silently lost.
    assert trigger._state.last_critic_finding_count == before


def test_advance_after_review_stops_at_uninterpreted_record(tmp_path: Path) -> None:
    """The watermark advances past the leading interpreted run only — an
    observation awaiting its interpretation stays eligible."""
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    findings = [
        {"observation_id": "O-001", "text": "a", "interpretations": [{"text": "i"}]},
        {"observation_id": "O-002", "text": "b", "interpretations": []},  # not yet interpreted
        {"observation_id": "O-003", "text": "c", "interpretations": [{"text": "i"}]},
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    trigger = CriticTrigger(case_dir=case_dir, examiner="aj")
    trigger.advance_after_review(case_dir / "findings.json")
    # Advanced past O-001 only; stopped at the uninterpreted O-002.
    assert trigger._state.last_critic_finding_count == 1


# ---------------------------------------------------------------------------
# deterministic detector floor reaches pending even when the LLM critic fails
# ---------------------------------------------------------------------------


async def test_detector_floor_routes_when_llm_fails(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    # A finding that trips EXECUTION_OVERCLAIM (execution claim + presence-only).
    findings = [
        {
            "observation_id": "O-001",
            "text": "nc.exe in Downloads",
            "cited_spans": [{"record_id": 1, "span_text": "MFT path=Downloads/nc.exe"}],
            "interpretations": [{"text": "the attacker executed nc.exe", "confidence": "HIGH"}],
        },
        {
            "observation_id": "O-002",
            "text": "second",
            "cited_spans": [{"record_id": 2, "span_text": "MFT path=x"}],
            "interpretations": [{"text": "benign", "confidence": "LOW"}],
        },
    ]
    (case_dir / "findings.json").write_text(json.dumps(findings), encoding="utf-8")
    deps = _make_deps(case_dir)

    async def _boom(cdir, examiner, fs, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("no API key")

    trigger = CriticTrigger(case_dir=case_dir, examiner="aj", interval_findings=2)
    hooks = build_critic_hooks(case_dir, "aj", trigger, critique_fn=_boom)

    class _Ctx:
        def __init__(self, d: InvestigatorDeps) -> None:
            self.deps = d
            self.usage = RunUsage()

    await hooks.after_model_request(_Ctx(deps), request_context=None, response="r")  # type: ignore[arg-type]
    # The deterministic floor still produced a CHALLENGE for the overclaim.
    assert any(v.finding_id == "O-001" for v in deps.pending_critiques)
    # And a critic_error breadcrumb was written.
    assert "critic_error" in (case_dir / "audit" / "critic.jsonl").read_text()


def test_route_live_verdicts_dedupes_by_finding_id() -> None:
    pending = [CriticVerdictRecord(finding_id="O-001", verdict="CHALLENGE", reason="first")]
    verdicts = [
        CriticVerdictRecord(finding_id="O-001", verdict="CHALLENGE", reason="again"),
        CriticVerdictRecord(finding_id="O-002", verdict="CHALLENGE", reason="new"),
    ]
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        n = route_live_verdicts(Path(d), "aj", verdicts, pending)
    assert n == 1  # O-001 already pending → only O-002 added
    assert [v.finding_id for v in pending] == ["O-001", "O-002"]


# ---------------------------------------------------------------------------
# the dynamic instruction registers and renders against live deps
# ---------------------------------------------------------------------------


async def test_instruction_renders_challenges_into_a_real_run(tmp_path: Path) -> None:
    """End-to-end: a pre-seeded CHALLENGE is rendered into the model prompt by the
    dynamic instruction during an actual agent run."""
    from pydantic_ai import Agent, capture_run_messages
    from pydantic_ai.messages import ModelRequest
    from pydantic_ai.models.test import TestModel

    from silentwitness_agent.investigator import InvestigatorResult

    case_dir = tmp_path / "case"
    case_dir.mkdir()
    agent: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(),
        deps_type=InvestigatorDeps,
        output_type=InvestigatorResult,
    )
    register_pending_critique_instruction(agent)
    deps = _make_deps(case_dir)
    deps.pending_critiques.append(
        CriticVerdictRecord(
            finding_id="O-007", verdict="CHALLENGE", reason="overstates the cloud exfil claim"
        )
    )
    with capture_run_messages() as messages:
        await agent.run("go", deps=deps)
    instructions = "\n".join(m.instructions or "" for m in messages if isinstance(m, ModelRequest))
    assert "O-007" in instructions
    assert "overstates the cloud exfil claim" in instructions


def test_build_live_critic_hooks_composes_onto_a_real_agent(tmp_path: Path) -> None:
    """The composition seam: build_live_critic_hooks returns a usable Hooks and
    register_pending_critique_instruction attaches to a real investigator agent."""
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    from silentwitness_agent.investigator import InvestigatorResult

    hooks = build_live_critic_hooks(tmp_path, "aj", model="test")
    assert "after_model_request" in hooks._registry  # type: ignore[attr-defined]

    agent: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(), deps_type=InvestigatorDeps, output_type=InvestigatorResult
    )
    before = len(agent._instructions)  # type: ignore[attr-defined]
    register_pending_critique_instruction(agent)
    assert len(agent._instructions) == before + 1  # type: ignore[attr-defined]
