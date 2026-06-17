"""Live critic regression coverage for shared run-wide usage limits."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_ai import RunUsage

from silentwitness_agent.critic import CriticReport
from silentwitness_agent.critic_trigger import CriticTrigger
from silentwitness_agent.hypothesis.budget import BudgetEnforcer
from silentwitness_agent.hypothesis.stack import HypothesisStack
from silentwitness_agent.investigator import InvestigatorDeps
from silentwitness_agent.live_critic import build_critic_hooks

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
    return InvestigatorDeps(
        case_dir=case_dir,
        examiner="aj",
        stack=HypothesisStack(case_dir=case_dir, examiner="aj"),
        budget=BudgetEnforcer(),
    )


async def test_hook_passes_shared_usage_and_limits_to_critic(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _write_findings(case_dir, 3)
    deps = _make_deps(case_dir)
    deps.request_limit = 7
    deps.total_token_limit = 123_456
    seen: dict[str, object] = {}

    async def _capture(cdir, examiner, findings, **kwargs):  # type: ignore[no-untyped-def]
        seen.update(kwargs)
        return CriticReport(verdicts=[], tokens_spent=0, time_elapsed_ms=0.0)

    trigger = CriticTrigger(case_dir=case_dir, examiner="aj", interval_findings=2)
    hooks = build_critic_hooks(case_dir, "aj", trigger, critique_fn=_capture)

    class _Ctx:
        def __init__(self, d: InvestigatorDeps) -> None:
            self.deps = d
            self.usage = RunUsage()

    ctx = _Ctx(deps)
    await hooks.after_model_request(ctx, request_context=None, response="resp")  # type: ignore[arg-type]

    assert seen["usage"] is ctx.usage
    assert seen["request_limit"] == 7
    assert seen["total_token_limit"] == 123_456
