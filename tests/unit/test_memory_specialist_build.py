"""Unit tests for memory specialist factory — ≥6 scenarios per story spec."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from silentwitness_agent.specialists._base import (
    SpecialistDeps,
    SpecialistFinding,
    SpecialistReport,
    _load_specialist_prompt,
)
from silentwitness_agent.specialists.memory import (
    _DEFAULT_MODEL,
    _HIGH_QUALITY_MODEL,
    MEMORY_TOOL_ALLOWLIST,
    build_memory_specialist,
    register_as_investigator_tool,
)
from silentwitness_common.types import Confidence, CriticVerdict

# Firewall #1 (Phase 2/3): the specialist is an INDEX querier — it has the index query
# tools, not the raw vol_* tools (those are demoted to ingest feeders).
_EXPECTED_INDEX_TOOLS = {"search_evidence", "timeline", "get_record"}
_EXPECTED_RECORD_TOOLS = {
    "record_observation",
    "record_interpretation",
    "register_evidence",
    "verify_evidence_hash",
}
_BANNED_TOOLS = {
    "vol_pslist",
    "vol_pstree",
    "vol_psscan",
    "vol_malfind",
    "vol_netscan",
    "vol_cmdline",
    "vol_dlllist",
    "vol_handles",
    "vol_lsadump",
    "parse_mft",
    "parse_amcache",
    "parse_shimcache",
    "parse_prefetch",
    "parse_shellbags",
    "regripper_run",
    "zeek_run",
    "suricata_run",
    "parse_evtx",
    "hayabusa_csv_timeline",
    "chainsaw_hunt",
}

# ---------------------------------------------------------------------------
# 1. Allowlist — exact count (the shared index-query surface)
# ---------------------------------------------------------------------------


def test_allowlist_has_8_tools() -> None:
    assert len(MEMORY_TOOL_ALLOWLIST) == 8


# ---------------------------------------------------------------------------
# 2. Allowlist — index query + record tools present
# ---------------------------------------------------------------------------


def test_allowlist_contains_index_query_tools() -> None:
    assert _EXPECTED_INDEX_TOOLS <= MEMORY_TOOL_ALLOWLIST


def test_allowlist_contains_all_record_tools() -> None:
    assert _EXPECTED_RECORD_TOOLS <= MEMORY_TOOL_ALLOWLIST


# ---------------------------------------------------------------------------
# 3. Allowlist — NO raw-evidence tools (firewall #1)
# ---------------------------------------------------------------------------


def test_allowlist_excludes_banned_tools() -> None:
    assert not (MEMORY_TOOL_ALLOWLIST & _BANNED_TOOLS), (
        f"Banned tools leaked into allowlist: {MEMORY_TOOL_ALLOWLIST & _BANNED_TOOLS}"
    )


def test_allowlist_is_exactly_index_plus_record_tools() -> None:
    # Exact-equality is the real firewall-#1 guard: a future demoted tool that is not
    # in _BANNED_TOOLS could not slip in undetected, unlike a count + finite denylist.
    assert MEMORY_TOOL_ALLOWLIST == (
        _EXPECTED_INDEX_TOOLS | _EXPECTED_RECORD_TOOLS | {"read_tool_output"}
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
# 6. SILENTWITNESS_SPECIALIST_MODEL_MEMORY uses TestModel when set to "test"
# ---------------------------------------------------------------------------


def test_factory_honours_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_MEMORY", "test")
    monkeypatch.delenv("SILENTWITNESS_MODEL_QUALITY", raising=False)
    agent = build_memory_specialist()
    assert isinstance(agent.model, TestModel)


# ---------------------------------------------------------------------------
# 7. Explicit model arg overrides env vars
# ---------------------------------------------------------------------------


def test_factory_explicit_model_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_MEMORY", "anthropic:claude-haiku-4-5")
    monkeypatch.setenv("SILENTWITNESS_MODEL_QUALITY", "high")
    agent = build_memory_specialist(model="test")
    assert isinstance(agent.model, TestModel)


# ---------------------------------------------------------------------------
# 8. SILENTWITNESS_MODEL_QUALITY=high → model name contains "opus"
# ---------------------------------------------------------------------------


def test_factory_quality_high_resolves_to_opus(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SILENTWITNESS_SPECIALIST_MODEL_MEMORY", raising=False)
    monkeypatch.setenv("SILENTWITNESS_MODEL_QUALITY", "high")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    from silentwitness_agent.specialists.memory import _resolve_specialist_model

    model = _resolve_specialist_model(None)
    assert hasattr(model, "model_name"), f"unexpected model type {type(model)}"
    assert "opus" in model.model_name  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# 9. register_as_investigator_tool adds dispatch_memory_specialist tool
# ---------------------------------------------------------------------------


def test_register_adds_dispatch_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SILENTWITNESS_SPECIALIST_MODEL_MEMORY", "test")
    from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult

    investigator: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(),
        deps_type=InvestigatorDeps,
        output_type=InvestigatorResult,
    )
    specialist = build_memory_specialist(model="test")
    register_as_investigator_tool(investigator, specialist)
    tool_names = list(investigator._function_toolset.tools)
    assert "dispatch_memory_specialist" in tool_names


# ---------------------------------------------------------------------------
# 10. System prompt contains required phrases and omits forbidden ones
# ---------------------------------------------------------------------------


def test_system_prompt_contains_required_phrases() -> None:
    prompt = _load_specialist_prompt("memory")
    assert "memory forensics specialist" in prompt
    assert "cite the specific tool-execution audit_id" in prompt


def test_system_prompt_excludes_forbidden_phrases() -> None:
    prompt = _load_specialist_prompt("memory")
    assert "court-admissible" not in prompt
    assert "Ralph Wiggum" not in prompt
    assert "autonomous SOC" not in prompt


# ---------------------------------------------------------------------------
# 11. _load_specialist_prompt error path
# ---------------------------------------------------------------------------


def test_load_specialist_prompt_missing_slug_raises() -> None:
    with pytest.raises(FileNotFoundError, match="nonexistent_slug"):
        _load_specialist_prompt("nonexistent_slug")


# ---------------------------------------------------------------------------
# 12. SpecialistReport and related types instantiate correctly
# ---------------------------------------------------------------------------


def test_specialist_report_construction(tmp_path: Path) -> None:
    report = SpecialistReport(
        findings=[],
        tokens_spent=10,
        tool_calls=[],
        time_elapsed_ms=123.4,
        confidence_assessment=Confidence.HIGH,
    )
    assert report.tokens_spent == 10
    assert report.confidence_assessment == Confidence.HIGH
    assert report.next_specialist_suggested is None
    assert report.notes_for_investigator == ""


def test_specialist_report_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SpecialistReport(
            tokens_spent=0,
            time_elapsed_ms=0.0,
            confidence_assessment=Confidence.LOW,
            unknown_field="bad",  # type: ignore[call-arg]
        )


def test_specialist_finding_uses_confidence_enum() -> None:
    finding = SpecialistFinding(
        observation_id="O-001",
        interpretation_id="I-001",
        confidence=Confidence.MEDIUM,
        summary="test finding",
    )
    assert finding.confidence == Confidence.MEDIUM
    assert isinstance(finding.confidence, Confidence)


def test_specialist_deps_absolute_path_enforced(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="absolute path"):
        SpecialistDeps(
            case_dir=Path("relative/path"),
            examiner="analyst",
            hypothesis_id="H-001",
        )


def test_specialist_deps_frozen_with_tuple_lists(tmp_path: Path) -> None:
    deps = SpecialistDeps(
        case_dir=tmp_path,
        examiner="analyst",
        hypothesis_id="H-001",
        evidence_paths=(tmp_path / "ev.img",),
        pending_critiques=(CriticVerdict.CHALLENGE,),
    )
    assert isinstance(deps.evidence_paths, tuple)
    assert isinstance(deps.pending_critiques, tuple)


# ---------------------------------------------------------------------------
# 13. dispatch_memory_specialist tool body executes via TestModel
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_dispatch_memory_specialist_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drive dispatch_memory_specialist end-to-end using TestModel.

    The specialist is built without MCPServerStdio to avoid spinning up the
    real MCP subprocess in a unit test. MCP filtering is covered separately
    by tests/integration/test_memory_specialist_allowlist.py.
    """
    from pydantic_ai.models.test import TestModel

    from silentwitness_agent.hypothesis.budget import BudgetEnforcer
    from silentwitness_agent.hypothesis.stack import HypothesisStack
    from silentwitness_agent.investigator import InvestigatorDeps, InvestigatorResult

    # Minimal specialist with no MCP toolset — just TestModel producing a SpecialistReport.
    specialist: Agent[SpecialistDeps, SpecialistReport] = Agent(
        TestModel(call_tools=[]),
        deps_type=SpecialistDeps,
        output_type=SpecialistReport,
    )

    # Wire a fresh investigator with a TestModel that calls dispatch_memory_specialist
    investigator: Agent[InvestigatorDeps, InvestigatorResult] = Agent(
        TestModel(
            call_tools=["dispatch_memory_specialist"],
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
