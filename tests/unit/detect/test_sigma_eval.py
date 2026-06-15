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
    proc = {"EventID": "1"}  # process_creation logsource gate -> Sysmon/4688 event
    assert rs.match({**proc, "Image": "C:\\Windows\\System32\\mstsc.exe"})
    assert rs.match({**proc, "Image": "C:\\evil\\notmstsc.exe.txt"}) == []  # anchored
    # logsource gate: same Image on a non-process-creation event does NOT fire
    assert rs.match({"EventID": "4624", "Image": "C:\\Windows\\System32\\mstsc.exe"}) == []


def test_unsupported_condition_node_raises() -> None:
    class _Weird:
        pass

    with pytest.raises(UnsupportedRuleError):
        _compile_condition(_Weird())


def test_evaluate_event_uses_default_ruleset() -> None:
    hits = evaluate_event({"EventID": "4625", "TargetUserName": "BACKUPADMIN"})
    assert any("Failed Logon" in d.title for d in hits)


def test_condition_not_inverts(tmp_path: Path) -> None:
    rule = """
title: t
id: 00000000-0000-0000-0000-0000000000a0
level: low
logsource: {product: windows, service: security}
detection:
    sel: {EventID: 4624}
    filt: {TargetUserName: SYSTEM}
    condition: sel and not filt
"""
    rs = _ruleset_from(tmp_path, rule)
    assert rs.match({"EventID": "4624", "TargetUserName": "fredr"})  # not filtered
    assert rs.match({"EventID": "4624", "TargetUserName": "SYSTEM"}) == []  # filtered out


def test_keyword_value_only_matches_any_field(tmp_path: Path) -> None:
    rule = """
title: t
id: 00000000-0000-0000-0000-0000000000a1
level: high
logsource: {product: windows}
detection:
    keywords:
        - mimikatz
    condition: keywords
"""
    rs = _ruleset_from(tmp_path, rule)
    assert rs.match({"CommandLine": "x mimikatz y"})  # matches the value, not a field name
    assert rs.match({"Image": "clean.exe"}) == []


def test_multi_expression_condition_is_or_combined(tmp_path: Path) -> None:
    rule = """
title: t
id: 00000000-0000-0000-0000-0000000000a2
level: low
logsource: {product: windows, service: security}
detection:
    a: {EventID: 4624}
    b: {EventID: 4625}
    condition:
        - a
        - b
"""
    rs = _ruleset_from(tmp_path, rule)
    assert rs.match({"EventID": "4624"})
    assert rs.match({"EventID": "4625"})
    assert rs.match({"EventID": "4648"}) == []


def test_sigma_null_matches_absent_or_empty(tmp_path: Path) -> None:
    rule = """
title: t
id: 00000000-0000-0000-0000-0000000000a3
level: low
logsource: {product: windows}
detection:
    sel: {ParentImage: null}
    condition: sel
"""
    rs = _ruleset_from(tmp_path, rule)
    assert rs.match({"EventID": "1"})  # field absent
    assert rs.match({"ParentImage": ""})  # field empty
    assert rs.match({"ParentImage": "explorer.exe"}) == []


def test_regex_value_unanchored_case_insensitive(tmp_path: Path) -> None:
    rule = """
title: t
id: 00000000-0000-0000-0000-0000000000a4
level: low
logsource: {product: windows}
detection:
    sel: {CommandLine|re: 'pow.*shell'}
    condition: sel
"""
    rs = _ruleset_from(tmp_path, rule)
    assert rs.match({"CommandLine": "C:\\PowErShell.exe -nop"})  # substring + case-insensitive
    assert rs.match({"CommandLine": "cmd.exe"}) == []


def test_numeric_value_vs_nonnumeric_field(tmp_path: Path) -> None:
    rule = """
title: t
id: 00000000-0000-0000-0000-0000000000a5
level: low
logsource: {product: windows, service: security}
detection:
    sel: {EventID: 4624, LogonType: 10}
    condition: sel
"""
    rs = _ruleset_from(tmp_path, rule)
    assert rs.match({"EventID": "4624", "LogonType": "interactive"}) == []  # no throw, no match
    assert rs.match({"EventID": "4624"}) == []  # missing LogonType


def test_all_modifier_requires_every_value(tmp_path: Path) -> None:
    rule = """
title: t
id: 00000000-0000-0000-0000-0000000000a6
level: high
logsource: {product: windows}
detection:
    sel:
        CommandLine|contains|all:
            - DownloadString
            - IEX
    condition: sel
"""
    rs = _ruleset_from(tmp_path, rule)
    assert rs.match({"CommandLine": "IEX (x).DownloadString(y)"})  # both present
    assert rs.match({"CommandLine": "x.DownloadString(y)"}) == []  # only one


def test_empty_rules_dir_loads_to_zero_without_raising(tmp_path: Path) -> None:
    rs = SigmaRuleset(tmp_path)
    assert rs.rule_count == 0
    assert rs.match({"EventID": "4625"}) == []


def test_uncompilable_rule_is_skipped_not_fatal(tmp_path: Path) -> None:
    good = """
title: good
id: 00000000-0000-0000-0000-0000000000b0
level: low
logsource: {product: windows, service: security}
detection: {sel: {EventID: 4625}, condition: sel}
"""
    bad = """
title: bad regex
id: 00000000-0000-0000-0000-0000000000b1
level: low
logsource: {product: windows}
detection: {sel: {CommandLine|re: '(unclosed'}, condition: sel}
"""
    rs = _ruleset_from(tmp_path, good, bad)
    assert rs.rule_count == 1  # good rule survives
    assert len(rs.skipped) == 1  # bad rule skipped loudly, not crashed
    assert rs.match({"EventID": "4625"})
