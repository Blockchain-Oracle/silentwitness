"""Round-2 review-fix tests for entity gate (split from main file for the
400-LOC file-size guard). Covers regex tightening for trailing prose
(Windows path / POSIX path / Registry key), IPv6 ::1 loopback, FQDN
account principals, and _get_nlp failure-sentinel caching.
"""

from __future__ import annotations

import pytest

from silentwitness_common.types import CitedSpan
from silentwitness_mcp.verification._entity_patterns import EntityKind
from silentwitness_mcp.verification.entity_gate import verify_entities


def _span(text: str) -> CitedSpan:
    return CitedSpan(record_id=1, span_text=text)


# ---------------------------------------------------------------------------
# PR-112 round-2 review fixes — regex tightening for trailing prose / IPv6 ::1
# ---------------------------------------------------------------------------


def test_windows_path_does_not_swallow_trailing_prose() -> None:
    """Code-reviewer C1: previous pattern consumed everything after the path
    up to the next backslash. With the whitespace+punctuation guard added,
    only the path-shaped prefix extracts."""
    obs = "the binary at C:\\Tools\\evil.exe was suspicious"
    cited = _span("scan flagged C:\\Tools\\evil.exe last Tuesday")
    result = verify_entities(obs, [cited])
    assert result.success is True
    windows_paths = [e.text for e in result.extracted if e.kind == EntityKind.WINDOWS_PATH]
    assert "C:\\Tools\\evil.exe" in windows_paths
    # Confirm the prose isn't part of the extracted entity.
    assert all("suspicious" not in e for e in windows_paths)


def test_posix_path_strips_trailing_punctuation() -> None:
    """Code-reviewer C2: docstring promised the prose-punctuation guard
    but the pattern didn't enforce it. Now ``the file /etc/passwd.``
    extracts ``/etc/passwd`` without the dot."""
    obs = "the file /etc/passwd. was modified"
    cited = _span("/etc/passwd timestamp changed during the incident")
    result = verify_entities(obs, [cited])
    assert result.success is True
    paths = [e.text for e in result.extracted if e.kind == EntityKind.POSIX_PATH]
    assert "/etc/passwd" in paths
    assert not any(p.endswith(".") for p in paths)


def test_registry_key_strips_trailing_comma() -> None:
    obs = "persistence at HKLM\\Software\\Run, then exec"
    cited = _span("reg add HKLM\\Software\\Run /v Updater")
    result = verify_entities(obs, [cited])
    assert result.success is True
    keys = [e.text for e in result.extracted if e.kind == EntityKind.REGISTRY_KEY]
    assert not any(k.endswith(",") for k in keys)


def test_ipv6_loopback_double_colon_one_extracted() -> None:
    """Code-reviewer #3: previous \\b anchor missed ``::1`` because ``:``
    isn't a word boundary. New boundary set covers the leading-``::`` shape."""
    obs = "loopback at ::1"
    cited = _span("loopback at ::1 confirmed")
    result = verify_entities(obs, [cited])
    assert result.success is True
    ipv6s = [e.text for e in result.extracted if e.kind == EntityKind.IPV6]
    assert "::1" in ipv6s


def test_account_extracts_fqdn_domain() -> None:
    """Code-reviewer #4: domain segment now allows ``.`` so dotted FQDNs
    like CORP.LOCAL\\Administrator extract intact rather than truncated."""
    obs = "CORP.LOCAL\\Administrator"
    cited = _span("CORP.LOCAL\\Administrator CORP.LOCAL\\Administrator")
    result = verify_entities(obs, [cited])
    assert result.success is True
    accounts = [e.text for e in result.extracted if e.kind == EntityKind.ACCOUNT]
    assert "CORP.LOCAL\\Administrator" in accounts


def test_word_boundary_prevents_substring_overmatch() -> None:
    """PR-112 silent-failure CRITICAL-3: previous ``in`` substring check
    accepted ``10.0.0.1`` in observation as 'present' when cited bytes
    contained the LONGER ``10.0.0.10``. Word-boundary anchor closes this
    false-acceptance surface."""
    # Cited contains "10.0.0.10" — a longer IP whose prefix matches "10.0.0.1"
    obs = "remote 10.0.0.1"
    cited = _span("remote 10.0.0.10 confirmed")
    result = verify_entities(obs, [cited])
    assert result.success is False
    assert any(h.text == "10.0.0.1" for h in result.hallucinated)


def test_ipv4_octet_bounds_reject_impossible_address() -> None:
    """PR-112 silent-failure HIGH-8: 999.999.999.999 must NOT extract as
    IPV4 — only octets 0-255 qualify."""
    from silentwitness_mcp.verification.entity_gate import _extract_all_entities

    entities = _extract_all_entities("the address 999.999.999.999 is impossible")
    ipv4 = [e for e in entities if e.kind == EntityKind.IPV4]
    assert ipv4 == []


def test_registry_key_lowercase_extracted() -> None:
    """PR-112 silent-failure HIGH-7: ``hklm\\...`` (lowercase) now
    extracts via re.IGNORECASE on the registry-key pattern."""
    from silentwitness_mcp.verification.entity_gate import _extract_all_entities

    entities = _extract_all_entities("persistence at hklm\\software\\run")
    reg = [e for e in entities if e.kind == EntityKind.REGISTRY_KEY]
    assert any(e.text.lower() == "hklm\\software\\run" for e in reg)


def test_entity_gate_model_error_message_is_actionable() -> None:
    """PR-112 silent-failure HIGH-9: missing-model error must name the
    install command so operators see context, not a raw spaCy traceback."""
    import pytest as _pytest

    from silentwitness_mcp.verification import entity_gate as gate_mod

    gate_mod._nlp_cache = None
    import spacy as _spacy

    saved_load = _spacy.load

    def fake_load(_name: str) -> None:
        raise OSError("[E050] Can't find model 'en_core_web_lg'")

    _spacy.load = fake_load  # type: ignore[assignment]
    try:
        with _pytest.raises(gate_mod.EntityGateModelError) as excinfo:
            gate_mod._get_nlp()
        msg = str(excinfo.value)
        assert "uv pip install --python" in msg
        assert "en_core_web_lg-3.8.0-py3-none-any.whl" in msg
    finally:
        _spacy.load = saved_load  # type: ignore[assignment]
        gate_mod._nlp_cache = None


def test_get_nlp_caches_failure_sentinel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Code-reviewer #5: once spacy.load fails, subsequent calls raise
    immediately rather than retrying the expensive load. Restores the
    cache in the finally block so sibling tests aren't poisoned."""
    from silentwitness_mcp.verification import entity_gate as gate_mod

    monkeypatch.setattr(gate_mod, "_nlp_cache", None)
    call_count = {"n": 0}

    def fake_load(_name: str) -> None:
        call_count["n"] += 1
        raise OSError("simulated missing model")

    import spacy as _spacy

    monkeypatch.setattr(_spacy, "load", fake_load)
    try:
        with pytest.raises(gate_mod.EntityGateModelError):
            gate_mod._get_nlp()
        with pytest.raises(gate_mod.EntityGateModelError, match="unavailable"):
            gate_mod._get_nlp()
        assert call_count["n"] == 1
    finally:
        gate_mod._nlp_cache = None
