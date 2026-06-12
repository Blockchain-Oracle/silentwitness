"""Unit tests for memory specialist factory — ≥6 scenarios per story spec."""

from __future__ import annotations

import pytest
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

from silentwitness_agent.specialists.memory import (
    _DEFAULT_MODEL,
    _HIGH_QUALITY_MODEL,
    MEMORY_TOOL_ALLOWLIST,
    build_memory_specialist,
    register_as_investigator_tool,
)

_EXPECTED_VOL_TOOLS = {
    "vol_pslist",
    "vol_pstree",
    "vol_psscan",
    "vol_malfind",
    "vol_netscan",
    "vol_cmdline",
    "vol_dlllist",
    "vol_handles",
    "vol_lsadump",
}
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
    "zeek_run",
    "suricata_run",
    "parse_evtx",
    "hayabusa_csv_timeline",
    "chainsaw_hunt",
}

# ---------------------------------------------------------------------------
# 1. Allowlist — exact count
# ---------------------------------------------------------------------------


def test_allowlist_has_13_tools() -> None:
    assert len(MEMORY_TOOL_ALLOWLIST) == 13


# ---------------------------------------------------------------------------
# 2. Allowlist — all vol_* and record tools present
# ---------------------------------------------------------------------------


def test_allowlist_contains_all_vol_tools() -> None:
    assert _EXPECTED_VOL_TOOLS <= MEMORY_TOOL_ALLOWLIST


def test_allowlist_contains_all_record_tools() -> None:
    assert _EXPECTED_RECORD_TOOLS <= MEMORY_TOOL_ALLOWLIST


# ---------------------------------------------------------------------------
# 3. Allowlist — no disk/log/network tools
# ---------------------------------------------------------------------------


def test_allowlist_excludes_banned_tools() -> None:
    assert not (MEMORY_TOOL_ALLOWLIST & _BANNED_TOOLS), (
        f"Banned tools leaked into allowlist: {MEMORY_TOOL_ALLOWLIST & _BANNED_TOOLS}"
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
# 8. SILENTWITNESS_MODEL_QUALITY=high → model string resolves to opus constant
# ---------------------------------------------------------------------------


def test_factory_quality_high_resolves_to_opus_constant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SILENTWITNESS_SPECIALIST_MODEL_MEMORY", raising=False)
    monkeypatch.setenv("SILENTWITNESS_MODEL_QUALITY", "high")
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
    from silentwitness_agent.specialists._base import _load_specialist_prompt

    prompt = _load_specialist_prompt("memory")
    assert "memory forensics specialist" in prompt
    assert "cite the specific tool-execution audit_id" in prompt


def test_system_prompt_excludes_forbidden_phrases() -> None:
    from silentwitness_agent.specialists._base import _load_specialist_prompt

    prompt = _load_specialist_prompt("memory")
    assert "court-admissible" not in prompt
    assert "Ralph Wiggum" not in prompt
    assert "autonomous SOC" not in prompt
