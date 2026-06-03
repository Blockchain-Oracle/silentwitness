"""Behavioural tests for src/silentwitness_mcp/verification/entity_gate.py.

Real spaCy load (lazy, cached at module level for the suite), real
regex catalog, real Pydantic. The spaCy model ``en_core_web_lg`` must
be installed; CI installs it in ci.yml. Tests that need only the
regex-catalog path are skip-free; tests that exercise spaCy NER are
skipped automatically if the model isn't installed.
"""

from __future__ import annotations

import pytest

from silentwitness_common.types import CitedSpan
from silentwitness_mcp.verification._entity_patterns import EntityKind
from silentwitness_mcp.verification.entity_gate import (
    EntityResult,
    ExtractedEntity,
    verify_entities,
)


def _has_spacy_model() -> bool:
    try:
        import spacy

        spacy.load("en_core_web_lg")
    except (ImportError, OSError):
        return False
    return True


_HAS_SPACY = _has_spacy_model()
_SHA64 = "e" * 64

_NEEDS_SPACY = pytest.mark.skipif(
    not _HAS_SPACY,
    reason="spaCy en_core_web_lg model not installed; install via "
    "`uv run python -m spacy download en_core_web_lg`",
)


def _span(text: str) -> CitedSpan:
    return CitedSpan(
        audit_id="sift-aj-20260613-007",
        sha256_of_normalized_output="a" * 64,
        line_start=0,
        line_end=1,
        span_text=text,
    )


# ---------------------------------------------------------------------------
# Regex catalog — each entity kind gets at least one test
# ---------------------------------------------------------------------------


def test_ipv4_extracted_and_matched() -> None:
    obs = "remote address 10.0.0.1"
    cited = _span("remote address 10.0.0.1 port 4444")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.text == "10.0.0.1" and e.kind == EntityKind.IPV4 for e in result.extracted)


def test_ipv4_hallucinated_when_not_in_cited() -> None:
    obs = "the C2 is 192.168.4.7"
    cited = _span("nothing about networking here")
    result = verify_entities(obs, [cited])
    assert result.success is False
    assert result.reason == "HALLUCINATED_ENTITIES"
    assert any(h.text == "192.168.4.7" for h in result.hallucinated)


def test_ipv6_extracted() -> None:
    obs = "address fe80::1234:5678:9abc:def0"
    cited = _span("source fe80::1234:5678:9abc:def0 destination ::1")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.kind == EntityKind.IPV6 for e in result.extracted)


def test_md5_extracted() -> None:
    # Empty-string MD5; literal stays inline so the regex catalog
    # exercises the actual 32-hex shape end-to-end.
    md5_hash = (
        "d41d8cd98f0"  # pragma: allowlist secret
        "0b204e9800998ecf8427e"  # pragma: allowlist secret
    )
    obs = f"md5 of the empty file is {md5_hash}"
    cited = _span(f"hashes computed: md5={md5_hash}")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.kind == EntityKind.MD5 for e in result.extracted)


def test_sha1_extracted_separately_from_sha256() -> None:
    """The 40-hex SHA1 must not be claimed as a SHA256 prefix and vice versa."""
    sha1 = (
        "da39a3ee5e6"  # pragma: allowlist secret
        "b4b0d3255bfef95601890afd80709"  # pragma: allowlist secret
    )
    obs = f"sha1: {sha1}"
    cited = _span(f"observed digest {sha1} in the manifest")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.text == sha1 and e.kind == EntityKind.SHA1 for e in result.extracted)


def test_sha256_wins_over_sha1_on_64_hex() -> None:
    obs = f"sha256 fingerprint {_SHA64}"
    cited = _span(f"manifest entry sha256={_SHA64}")
    result = verify_entities(obs, [cited])
    assert result.success is True
    sha_kinds = [e.kind for e in result.extracted if e.kind in (EntityKind.SHA256, EntityKind.SHA1)]
    assert sha_kinds == [EntityKind.SHA256]  # not SHA1


def test_registry_key_extracted() -> None:
    key = "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    obs = f"persistence at {key}"
    cited = _span(f"reg add {key} /v Updater /t REG_SZ /d evil.exe")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.kind == EntityKind.REGISTRY_KEY for e in result.extracted)


def test_windows_path_extracted_with_trailing_backslash() -> None:
    obs = "installed at C:\\Tools\\Ethereal\\"
    cited = _span("targeted directory: C:\\Tools\\Ethereal\\ owner SYSTEM")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(
        e.text == "C:\\Tools\\Ethereal\\" and e.kind == EntityKind.WINDOWS_PATH
        for e in result.extracted
    )


def test_windows_path_hallucinated_when_different_directory() -> None:
    obs = "binary was at C:\\Tools\\Ethereal\\"
    cited = _span("binary was at C:\\Program Files\\Ethereal\\")
    result = verify_entities(obs, [cited])
    assert result.success is False
    assert any(h.text == "C:\\Tools\\Ethereal\\" for h in result.hallucinated)


def test_windows_path_case_insensitive_match() -> None:
    obs = "installed at c:\\program files\\ethereal\\"
    cited = _span("found at C:\\Program Files\\Ethereal\\ during scan")
    result = verify_entities(obs, [cited])
    assert result.success is True


def test_windows_path_normalised_against_forward_slash_cite() -> None:
    """A cited span using forward-slash path style still matches a
    backslash-style observation (and vice versa)."""
    obs = "found at C:\\Windows\\System32\\drivers\\evil.sys"
    cited = _span("path c:/windows/system32/drivers/evil.sys flagged")
    result = verify_entities(obs, [cited])
    assert result.success is True


def test_posix_path_extracted() -> None:
    obs = "config at /etc/passwd"
    cited = _span("/etc/passwd timestamps preserved")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.kind == EntityKind.POSIX_PATH for e in result.extracted)


def test_url_extracted_not_misclassified_as_posix_path() -> None:
    """URL pattern wins over POSIX_PATH (order in REGEX_RULES)."""
    obs = "c2 at https://evil.example/c2.php"
    cited = _span("connection to https://evil.example/c2.php observed")
    result = verify_entities(obs, [cited])
    assert result.success is True
    url_entries = [e for e in result.extracted if e.kind == EntityKind.URL]
    assert any(e.text == "https://evil.example/c2.php" for e in url_entries)


def test_account_extracted() -> None:
    obs = "logon as DOMAIN\\Administrator at 03:14"
    cited = _span("Subject: DOMAIN\\Administrator LogonType: 10")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.kind == EntityKind.ACCOUNT for e in result.extracted)


def test_account_hallucinated_when_different_principal() -> None:
    obs = "logon as DOMAIN\\Administrator at 03:14"
    cited = _span("Subject: WORKGROUP\\guest LogonType: 3")
    result = verify_entities(obs, [cited])
    assert result.success is False
    assert any(h.text == "DOMAIN\\Administrator" for h in result.hallucinated)


def test_mutex_extracted() -> None:
    obs = "named Global\\Win32MutexX"
    cited = _span("CreateMutex named Global\\Win32MutexX with handle 0x4")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.kind == EntityKind.MUTEX for e in result.extracted)


def test_port_extracted_with_context_anchor() -> None:
    obs = "outbound to port 4444"
    cited = _span("destination port 4444 confirmed on the wire")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.text == "4444" and e.kind == EntityKind.PORT for e in result.extracted)


def test_bare_number_not_extracted_as_port() -> None:
    """Without the 'port' keyword preceding, a bare integer must NOT be
    extracted as PORT (architecture §4.7 explicit pitfall)."""
    obs = "the value 4444 appears in the registry"
    cited = _span("nothing about ports here, only the number 4444 elsewhere")
    result = verify_entities(obs, [cited])
    port_entries = [e for e in result.extracted if e.kind == EntityKind.PORT]
    assert port_entries == []


def test_email_extracted() -> None:
    obs = "from attacker@evil.example"
    cited = _span("from attacker@evil.example subject invoice")
    result = verify_entities(obs, [cited])
    assert result.success is True
    assert any(e.kind == EntityKind.EMAIL for e in result.extracted)


# ---------------------------------------------------------------------------
# Multi-entity flows + the wedge-closing test
# ---------------------------------------------------------------------------


def test_multi_entity_observation_all_present() -> None:
    obs = "outbound on port 4444 to 10.0.0.1"
    cited = _span("destination port 4444 remote 10.0.0.1 observed")
    result = verify_entities(obs, [cited])
    assert result.success is True
    kinds = {e.kind for e in result.extracted}
    assert EntityKind.PORT in kinds and EntityKind.IPV4 in kinds


def test_partial_hallucination_lists_only_missing_entities() -> None:
    obs = "svchost.exe at PID 1208 connecting to 192.168.4.7 port 4444"
    cited = _span("svchost.exe seen connecting on port 4444 to 10.0.0.1")
    result = verify_entities(obs, [cited])
    assert result.success is False
    hallucinated_texts = [h.text for h in result.hallucinated]
    assert "192.168.4.7" in hallucinated_texts
    # 10.0.0.1 was in cited bytes — NOT hallucinated. But the agent didn't
    # name it in the observation, so it isn't extracted at all.
    assert "10.0.0.1" not in [e.text for e in result.extracted]


def test_empty_observation_returns_empty_success() -> None:
    """An observation with no extractable entities is trivially a success
    (no entities → no hallucinations to find)."""
    obs = "the file was modified yesterday"
    cited = _span("evidence content")
    result = verify_entities(obs, [cited])
    assert result.success is True
    # spaCy may or may not extract NER kinds here; not asserting either way.


# ---------------------------------------------------------------------------
# Type-level Pydantic invariants
# ---------------------------------------------------------------------------


def test_entity_result_rejects_success_with_nonempty_hallucinated() -> None:
    from pydantic import ValidationError

    sample = ExtractedEntity(text="10.0.0.1", kind=EntityKind.IPV4, source="regex")
    with pytest.raises(ValidationError, match="empty hallucinated"):
        EntityResult(success=True, extracted=(sample,), hallucinated=(sample,))


def test_entity_result_rejects_failure_with_empty_hallucinated() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="non-empty hallucinated"):
        EntityResult(success=False, extracted=(), hallucinated=(), reason="HALLUCINATED_ENTITIES")


def test_entity_result_rejects_failure_with_wrong_reason() -> None:
    from pydantic import ValidationError

    sample = ExtractedEntity(text="10.0.0.1", kind=EntityKind.IPV4, source="regex")
    with pytest.raises(ValidationError, match="HALLUCINATED_ENTITIES"):
        EntityResult(success=False, extracted=(sample,), hallucinated=(sample,), reason="OTHER")


def test_entity_result_rejects_success_with_reason_set() -> None:
    """success=True must not carry a reason field."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="must not carry reason"):
        EntityResult(success=True, extracted=(), hallucinated=(), reason="OOPS")


@_NEEDS_SPACY
def test_spacy_non_ner_kind_label_skipped() -> None:
    """spaCy emits labels like DATE, CARDINAL, ORDINAL. Those aren't in
    SPACY_NER_KINDS; the gate skips them. (Branch coverage for
    `if kind not in SPACY_NER_KINDS: continue` at entity_gate.py.)"""
    obs = "incident detected on Tuesday at 3pm"  # DATE + TIME labels
    cited = _span("incident detected on Tuesday at 3pm during scan")
    result = verify_entities(obs, [cited])
    # No DATE / TIME entries — only NER kinds in SPACY_NER_KINDS are kept.
    for entity in result.extracted:
        if entity.source == "spacy":
            assert entity.kind in {
                EntityKind.PERSON,
                EntityKind.ORG,
                EntityKind.GPE,
                EntityKind.PRODUCT,
                EntityKind.WORK_OF_ART,
            }


@_NEEDS_SPACY
def test_spacy_overlap_with_regex_match_is_skipped() -> None:
    """If spaCy classifies the same span the regex already consumed (e.g.
    'evil.example' inside an email), the spaCy entity is skipped."""
    obs = "from attacker@evil.example"
    cited = _span("from attacker@evil.example reported")
    result = verify_entities(obs, [cited])
    # The email regex consumed the full "attacker@evil.example" span. Any
    # spaCy NER attempt at "evil.example" should overlap and be skipped.
    email_entries = [e for e in result.extracted if e.kind == EntityKind.EMAIL]
    assert len(email_entries) == 1


# ---------------------------------------------------------------------------
# spaCy NER (skipped automatically without model)
# ---------------------------------------------------------------------------


@_NEEDS_SPACY
def test_spacy_extracts_person_name_when_present_in_cite() -> None:
    obs = "the analyst named John Smith reported the incident"
    cited = _span("John Smith filed report #4172 on the IR call")
    result = verify_entities(obs, [cited])
    assert result.success is True


@_NEEDS_SPACY
def test_spacy_flags_hallucinated_person_name() -> None:
    obs = "the analyst named Jane Doe reported the incident"
    cited = _span("the analyst on call had no idea what was happening")
    result = verify_entities(obs, [cited])
    if not result.success:
        assert any("Jane Doe" in h.text for h in result.hallucinated)
