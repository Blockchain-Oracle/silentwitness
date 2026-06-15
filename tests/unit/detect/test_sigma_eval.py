"""Unit tests for the Sigma detection engine (pysigma is a pure-Python CI dependency)."""

from __future__ import annotations

from pathlib import Path

import pytest

from silentwitness_mcp.detect.sigma_eval import (
    SigmaRuleset,
    UnsupportedRuleError,
    _compile_condition,
    default_ruleset,
    evaluate_event,
)


def _ruleset_from(tmp_path: Path, *rules: str) -> SigmaRuleset:
    for i, rule in enumerate(rules):
        (tmp_path / f"rule_{i}.yml").write_text(rule, encoding="utf-8")
    return SigmaRuleset(tmp_path)


_RDP = """
title: RDP Logon
id: 00000000-0000-0000-0000-000000000010
level: medium
logsource: {product: windows, service: security}
detection:
    selection: {EventID: 4624}
    logon_type: {LogonType: [10, 7]}
    condition: selection and logon_type
tags: [attack.t1021.001]
"""

_PS = """
title: Suspicious PowerShell
id: 00000000-0000-0000-0000-000000000011
level: high
logsource: {product: windows, service: powershell}
detection:
    selection: {EventID: 4104}
    susp:
        ScriptBlockText|contains: ['Net.WebClient', 'IEX ']
    condition: selection and susp
tags: [attack.t1059.001]
"""


def test_curated_pack_loads_without_skips() -> None:
    rs = default_ruleset()
    assert rs.rule_count >= 6
    assert rs.skipped == []  # every shipped rule must compile


def test_numeric_and_and_or_condition(tmp_path: Path) -> None:
    rs = _ruleset_from(tmp_path, _RDP)
    assert [d.title for d in rs.match({"EventID": "4624", "LogonType": "10"})] == ["RDP Logon"]
    assert [d.title for d in rs.match({"EventID": "4624", "LogonType": "7"})] == ["RDP Logon"]
    assert rs.match({"EventID": "4624", "LogonType": "2"}) == []  # interactive, not RDP
    assert rs.match({"EventID": "4625", "LogonType": "10"}) == []  # wrong event id


def test_contains_modifier_case_insensitive(tmp_path: Path) -> None:
    rs = _ruleset_from(tmp_path, _PS)
    hit = rs.match({"EventID": "4104", "ScriptBlockText": "iex (new-object net.webclient)"})
    assert [d.title for d in hit] == ["Suspicious PowerShell"]
    assert rs.match({"EventID": "4104", "ScriptBlockText": "Get-ChildItem"}) == []


def test_detection_metadata_surfaced(tmp_path: Path) -> None:
    rs = _ruleset_from(tmp_path, _RDP)
    det = rs.match({"EventID": "4624", "LogonType": "10"})[0]
    assert det.level == "medium"
    assert det.rule_id == "00000000-0000-0000-0000-000000000010"
    assert "t1021.001" in det.tags


def test_endswith_wildcard_anchoring(tmp_path: Path) -> None:
    rule = """
title: mstsc exec
id: 00000000-0000-0000-0000-000000000012
level: medium
logsource: {product: windows, category: process_creation}
detection:
    sel: {Image|endswith: '\\mstsc.exe'}
    condition: sel
"""
    rs = _ruleset_from(tmp_path, rule)
    assert rs.match({"Image": "C:\\Windows\\System32\\mstsc.exe"})
    assert rs.match({"Image": "C:\\evil\\notmstsc.exe.txt"}) == []  # anchored, no substring


def test_unsupported_condition_node_raises() -> None:
    class _Weird:
        pass

    with pytest.raises(UnsupportedRuleError):
        _compile_condition(_Weird())


def test_evaluate_event_uses_default_ruleset() -> None:
    hits = evaluate_event({"EventID": "4625", "TargetUserName": "BACKUPADMIN"})
    assert any("Failed Logon" in d.title for d in hits)
