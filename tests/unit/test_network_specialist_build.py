"""Unit tests for network specialist factory — ≥6 scenarios per story spec."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from silentwitness_agent.specialists._base import (
    SpecialistDeps,
    SpecialistReport,
    _load_specialist_prompt,
)
from silentwitness_agent.specialists.network import (
    _DEFAULT_MODEL,
    _HIGH_QUALITY_MODEL,
    NETWORK_TOOL_ALLOWLIST,
    build_network_specialist,
    register_as_investigator_tool,
)

_EXPECTED_NETWORK_TOOLS = {"zeek_run", "suricata_run"}
_EXPECTED_RECORD_TOOLS = {
    "record_observation",
    "record_interpretation",
    "register_evidence",
    "verify_evidence_hash",
}
_BANNED_TOOLS = {
    "parse_mft",
    "parse_amcache",
    "parse_shimcache",
    "parse_prefetch",
    "parse_shellbags",
    "regripper_run",
    "vol_pslist",
    "vol_pstree",
    "vol_psscan",
    "vol_malfind",
    "parse_evtx",
    "hayabusa_csv_timeline",
    "chainsaw_hunt",
}

# ---------------------------------------------------------------------------
# 1. Allowlist — exact count
# ---------------------------------------------------------------------------


def test_allowlist_has_7_tools() -> None:
    assert len(NETWORK_TOOL_ALLOWLIST) == 7


# ---------------------------------------------------------------------------
# 2. Allowlist — all network and record tools present
# ---------------------------------------------------------------------------


def test_allowlist_contains_all_network_tools() -> None:
    assert _EXPECTED_NETWORK_TOOLS <= NETWORK_TOOL_ALLOWLIST


def test_allowlist_contains_all_record_tools() -> None:
    assert _EXPECTED_RECORD_TOOLS <= NETWORK_TOOL_ALLOWLIST


# ---------------------------------------------------------------------------
# 3. Allowlist — no disk/memory/log tools
# ---------------------------------------------------------------------------


def test_allowlist_excludes_banned_tools() -> None:
    assert not (NETWORK_TOOL_ALLOWLIST & _BANNED_TOOLS), (
        f"Banned tools leaked into allowlist: {NETWORK_TOOL_ALLOWLIST & _BANNED_TOOLS}"
    )


# ---------------------------------------------------------------------------
# 4. Default model constant is haiku
# ---------------------------------------------------------------------------


def test_default_model_constant_is_haiku() -> None:
    assert _DEFAULT_MODEL == "anthropic:claude-haiku-4-5"


# ---------------------------------------------------------------------------
# 5. High-quality model constant is opus
# ---------------------------------------------------------------------------


def test_high_quality_model_constant_is_opus() -> None:
    assert _HIGH_QUALITY_MODEL == "anthropic:claude-opus-4-7"


# ---------------------------------------------------------------------------
# 6. SILENTWITNESS_SPECIALIST_MODEL_NETWORK uses TestModel when set to "test"
# ---------------------------------------------------------------------------


def test_factory_honours_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_NETWORK", "test")
    monkeypatch.delenv("SILENTWITNESS_MODEL_QUALITY", raising=False)
    agent = build_network_specialist()
    assert isinstance(agent.model, TestModel)


# ---------------------------------------------------------------------------
# 7. Explicit model arg overrides env vars
# ---------------------------------------------------------------------------


def test_factory_explicit_model_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_NETWORK", "anthropic:claude-haiku-4-5")
    monkeypatch.setenv("SILENTWITNESS_MODEL_QUALITY", "high")
    agent = build_network_specialist(model="test")
    assert isinstance(agent.model, TestModel)


# ---------------------------------------------------------------------------
# 8. SILENTWITNESS_MODEL_QUALITY=high → model name contains "opus"
# ---------------------------------------------------------------------------


def test_factory_quality_high_resolves_to_opus(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SILENTWITNESS_SPECIALIST_MODEL_NETWORK", raising=False)
    monkeypatch.setenv("SILENTWITNESS_MODEL_QUALITY", "high")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from silentwitness_agent.specialists.network import _resolve_specialist_model

    model = _resolve_specialist_model(None)
    assert hasattr(model, "model_name"), f"unexpected model type {type(model)}"
    assert "opus" in model.model_name  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# 9. Default model is haiku when both env vars are unset (behavioural)
# ---------------------------------------------------------------------------


def test_factory_default_model_is_haiku(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SILENTWITNESS_SPECIALIST_MODEL_NETWORK", raising=False)
    monkeypatch.delenv("SILENTWITNESS_MODEL_QUALITY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from silentwitness_agent.specialists.network import _resolve_specialist_model

    model = _resolve_specialist_model(None)
    assert hasattr(model, "model_name"), f"unexpected model type {type(model)}"
    assert "haiku" in model.model_name  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# 10. Blank env var falls through to default
# ---------------------------------------------------------------------------


def test_blank_network_model_env_falls_through_to_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_NETWORK", "")
    monkeypatch.delenv("SILENTWITNESS_MODEL_QUALITY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from silentwitness_agent.specialists.network import _resolve_specialist_model

    model = _resolve_specialist_model(None)
    assert hasattr(model, "model_name"), f"unexpected model type {type(model)}"
    assert "haiku" in model.model_name  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# 11. Invalid model env var raises ValueError with env-var name in message
# ---------------------------------------------------------------------------


def test_factory_invalid_model_env_raises_with_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_NETWORK", "bogus:nonexistent")
    monkeypatch.delenv("SILENTWITNESS_MODEL_QUALITY", raising=False)
    with pytest.raises(ValueError, match="SILENTWITNESS_SPECIALIST_MODEL_NETWORK"):
        build_network_specialist()


# ---------------------------------------------------------------------------
# 12. register_as_investigator_tool adds dispatch_network_specialist tool
# ---------------------------------------------------------------------------


def test_register_adds_dispatch_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_NETWORK", "test")
    from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult

    investigator: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(),
        deps_type=InvestigatorDeps,
        output_type=InvestigatorResult,
    )
    specialist = build_network_specialist(model="test")
    register_as_investigator_tool(investigator, specialist)
    tool_names = list(investigator._function_toolset.tools)
    assert "dispatch_network_specialist" in tool_names


# ---------------------------------------------------------------------------
# 13. System prompt contains required phrases and omits forbidden ones
# ---------------------------------------------------------------------------


def test_system_prompt_contains_required_phrases() -> None:
    prompt = _load_specialist_prompt("network")
    assert "network forensics specialist" in prompt
    assert "Beacon detection" in prompt
    assert "cite the specific tool-execution" in prompt


def test_system_prompt_excludes_forbidden_phrases() -> None:
    prompt = _load_specialist_prompt("network")
    assert "court-admissible" not in prompt
    assert "Ralph Wiggum" not in prompt
    assert "autonomous SOC" not in prompt


# ---------------------------------------------------------------------------
# 14. _load_specialist_prompt — network slug loads and error path
# ---------------------------------------------------------------------------


def test_load_specialist_prompt_network_slug_loads() -> None:
    prompt = _load_specialist_prompt("network")
    assert len(prompt) > 100


def test_load_specialist_prompt_missing_slug_raises() -> None:
    with pytest.raises(FileNotFoundError, match="nonexistent_slug"):
        _load_specialist_prompt("nonexistent_slug")


# ---------------------------------------------------------------------------
# 14. dispatch_network_specialist tool body executes via TestModel
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_network_specialist_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive dispatch_network_specialist end-to-end using TestModel.

    The specialist is built without MCPServerStdio to avoid spinning up the
    real MCP subprocess in a unit test.
    """
    from silentwitness_agent.hypothesis.budget import BudgetEnforcer
    from silentwitness_agent.hypothesis.stack import HypothesisStack
    from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult

    specialist: Agent[SpecialistDeps, SpecialistReport] = Agent(
        TestModel(call_tools=[]),
        deps_type=SpecialistDeps,
        output_type=SpecialistReport,
    )

    investigator: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(
            call_tools=["dispatch_network_specialist"],
            custom_output_args={
                "hypotheses_formed": 0,
                "hypotheses_confirmed": 0,
                "hypotheses_pivoted": 0,
                "hypotheses_abandoned": 0,
                "findings_staged": 0,
                "total_tool_calls": 1,
                "total_tokens_consumed": 5,
                "time_elapsed_ms": 1.0,
                "final_state": "COMPLETED",
                "model_used": "test",
            },
        ),
        deps_type=InvestigatorDeps,
        output_type=InvestigatorResult,
    )
    register_as_investigator_tool(investigator, specialist)

    case_dir = tmp_path / "case"
    case_dir.mkdir()
    deps = InvestigatorDeps(
        case_dir=case_dir,
        examiner="analyst",
        stack=HypothesisStack(case_dir=case_dir, examiner="analyst"),
        budget=BudgetEnforcer(),
    )
    result = await investigator.run("test question", deps=deps)
    assert result.output.total_tool_calls == 1
    assert result.output.final_state == "COMPLETED"
