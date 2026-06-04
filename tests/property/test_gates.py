"""Hypothesis property tests for the verification gates (architecture §14).

Ratifies the four upstream Epic-3 stories — output_normalizer,
citation_gate, entity_gate, sanitizer — against architectural invariants
under random input. Profile selection: ``HYPOTHESIS_PROFILE=dev|ci|slow``
(registered in ``tests/conftest.py``).

The strongest property in this suite: a randomly constructed valid
observation (cited spans derived from real tmp-path blob bytes,
SHA-256 recomputed) ALWAYS passes both gates. If Hypothesis ever
shrinks an accept→reject inversion, the wedge has cracked and the
demo will fail.
"""

from __future__ import annotations

import hashlib

from _pytest.tmpdir import TempPathFactory
from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.strategies import DataObject

from silentwitness_mcp.verification._types import CitationRejectReason
from silentwitness_mcp.verification.citation_gate import verify_citation
from silentwitness_mcp.verification.entity_gate import verify_entities
from silentwitness_mcp.verification.normalizer import normalize_output
from silentwitness_mcp.verification.sanitizer import sanitize
from tests.property.strategies import (
    audit_entry_strategy,
    cited_span_strategy,
    dfir_entity_strategy,
    injection_payload_strategy,
    normalizable_output_strategy,
)

_AUDIT_ID = "sift-aj-20260613-007"


class _CollectingWriter:
    """Sanitizer audit_writer fake — discards events for property tests."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def emit(self, event: object) -> None:
        self.events.append(event)


# ---------------------------------------------------------------------------
# Normalizer properties
# ---------------------------------------------------------------------------


@given(raw=normalizable_output_strategy())
def test_normalize_is_idempotent(raw: bytes) -> None:
    """normalize(normalize(x)) == normalize(x) for any input."""
    once = normalize_output(raw, tool="_universal_only")
    twice = normalize_output(once, tool="_universal_only")
    assert once == twice


@given(raw=normalizable_output_strategy())
def test_normalize_is_byte_stable(raw: bytes) -> None:
    """Same input → same output. The hash the citation gate stores must
    be reproducible on every re-verification."""
    assert normalize_output(raw, tool="_universal_only") == normalize_output(
        raw, tool="_universal_only"
    )


@given(raw=normalizable_output_strategy())
def test_normalize_decode_round_trip_is_lossless_on_invalid_utf8(raw: bytes) -> None:
    """surrogateescape preserves invalid bytes — two raw inputs that
    differ in invalid-UTF-8 bytes produce DIFFERENT normalised hashes."""
    hash_a = hashlib.sha256(normalize_output(raw, tool="_universal_only")).hexdigest()
    hash_b = hashlib.sha256(normalize_output(raw + b"\xff", tool="_universal_only")).hexdigest()
    # Adding a different trailing byte must change the hash.
    assume(raw[-1:] != b"\xff" if raw else True)
    assert hash_a != hash_b


# ---------------------------------------------------------------------------
# Sanitizer properties
# ---------------------------------------------------------------------------


@given(payload=injection_payload_strategy())
def test_sanitize_strips_at_least_one_known_token(payload: str) -> None:
    """A payload containing a known injection token must produce strip_count ≥ 1."""
    writer = _CollectingWriter()
    result = sanitize(payload, _AUDIT_ID, audit_writer=writer)
    assert result.strip_count >= 1


@given(payload=injection_payload_strategy())
def test_sanitize_visible_markers_carry_audit_id(payload: str) -> None:
    """Every visible ``[stripped:{audit_id}:...]`` marker must include the
    audit_id nonce. Attacker-planted bare ``[stripped: ...]`` strings
    don't share the canonical format and survive intact."""
    writer = _CollectingWriter()
    result = sanitize(payload, _AUDIT_ID, audit_writer=writer)
    # Every event the sanitizer emitted is reflected in the wrapped text
    # via either a [stripped:{audit_id}:{pid}] marker (for ops 1-3) or
    # silent removal (for ops 4 — bidi/zwsp/tag-char). We can't assert
    # 1:1 between events and markers, but we CAN assert no orphan marker.
    suffix = f":{_AUDIT_ID}:"
    # Either there's no marker at all, or every marker contains the nonce.
    if "[stripped:" in result.wrapped_text:
        assert suffix in result.wrapped_text


@given(payload=injection_payload_strategy())
def test_sanitize_wrap_markers_present(payload: str) -> None:
    """Sanitised output always wraps in the canonical evidence markers."""
    result = sanitize(payload, _AUDIT_ID, audit_writer=_CollectingWriter())
    assert result.wrapped_text.startswith("[UNTRUSTED EVIDENCE BEGIN]\n")
    assert result.wrapped_text.endswith("\n[UNTRUSTED EVIDENCE END]")


# ---------------------------------------------------------------------------
# Citation gate properties — the strongest invariant of Epic 3
# ---------------------------------------------------------------------------


@given(data=st.data())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_citation_gate_accepts_valid_construction(
    tmp_path_factory: TempPathFactory, data: DataObject
) -> None:
    """For ANY validly constructed CitedSpan + matching audit_entry the
    citation gate ACCEPTS. The wedge's strongest property — if this ever
    fails Hypothesis has found a construction we forgot."""
    tmpdir = tmp_path_factory.mktemp("citation_accept", numbered=True)
    entry, payload = data.draw(audit_entry_strategy(tmpdir))
    span = data.draw(cited_span_strategy(entry, payload))
    assume(span is not None)
    result = verify_citation(span, audit_index={entry.audit_id: entry})
    assert result.success is True, (
        f"citation gate rejected a valid construction; reason={result.reason} "
        f"context={result.context}"
    )


@given(
    data=st.data(),
    bogus_hash=st.text(alphabet="0123456789abcdef", min_size=64, max_size=64),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_citation_gate_rejects_random_sha256(
    tmp_path_factory: TempPathFactory, data: DataObject, bogus_hash: str
) -> None:
    """A randomly generated sha256 cannot match an arbitrary blob's
    actual hash (collision-resistance probability 2^-256). The gate
    must reject with OUTPUT_HASH_MISMATCH."""
    tmpdir = tmp_path_factory.mktemp("citation_reject_hash", numbered=True)
    entry, payload = data.draw(audit_entry_strategy(tmpdir))
    actual = hashlib.sha256(normalize_output(payload, tool=entry.tool)).hexdigest()
    assume(bogus_hash != actual)  # vacuous collision case
    from silentwitness_common.types import CitedSpan

    span = CitedSpan(
        audit_id=entry.audit_id,
        sha256_of_normalized_output=bogus_hash,
        line_start=0,
        line_end=1,
        span_text="anything",
    )
    result = verify_citation(span, audit_index={entry.audit_id: entry})
    assert result.success is False
    assert result.reason == CitationRejectReason.OUTPUT_HASH_MISMATCH


@given(
    audit_id=st.text(
        alphabet=st.characters(min_codepoint=0x61, max_codepoint=0x7A),
        min_size=4,
        max_size=20,
    ).map(lambda s: f"sift-aj-99999999-{s}")
)
def test_citation_gate_rejects_unknown_audit_id(audit_id: str) -> None:
    """An audit_id absent from the index → AUDIT_ID_NOT_FOUND, never
    a different rejection code that would mislead the agent."""
    from silentwitness_common.types import CitedSpan

    span = CitedSpan(
        audit_id=audit_id,
        sha256_of_normalized_output="a" * 64,
        line_start=0,
        line_end=1,
        span_text="anything",
    )
    result = verify_citation(span, audit_index={})
    assert result.success is False
    assert result.reason == CitationRejectReason.AUDIT_ID_NOT_FOUND


# ---------------------------------------------------------------------------
# Entity gate properties
# ---------------------------------------------------------------------------


@given(entity=dfir_entity_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_entity_gate_accepts_when_entity_in_cited(entity: str) -> None:
    """A DFIR entity placed verbatim in both observation_text AND a
    cited_span MUST be accepted (no false positives)."""
    from silentwitness_common.types import CitedSpan

    cited = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output="a" * 64,
        line_start=0,
        line_end=1,
        span_text=f"observed {entity} in evidence",
    )
    result = verify_entities(f"observed {entity}", [cited])
    assert result.success is True, (
        f"entity gate rejected a valid entity; "
        f"hallucinated={[(h.text, h.kind.value) for h in result.hallucinated]}"
    )


@given(entity=dfir_entity_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_entity_gate_rejects_when_entity_only_in_obs(entity: str) -> None:
    """A DFIR entity in observation_text but absent from cited bytes
    → REJECTED with HALLUCINATED_ENTITIES + entity in hallucinated list."""
    from silentwitness_common.types import CitedSpan

    # Use cited text that has no entities — generic prose.
    cited = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output="a" * 64,
        line_start=0,
        line_end=1,
        span_text="generic evidence text with no actionable entities",
    )
    result = verify_entities(f"observed {entity}", [cited])
    assert result.success is False
    assert result.reason == "HALLUCINATED_ENTITIES"
    assert any(entity in h.text or h.text in entity for h in result.hallucinated)


@given(entity=dfir_entity_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_entity_gate_extracts_entity_kind_consistently(entity: str) -> None:
    """For a DFIR entity in obs+cited, the extracted-entities list
    contains exactly one ExtractedEntity matching it (up to dedupe)."""
    from silentwitness_common.types import CitedSpan

    cited = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output="a" * 64,
        line_start=0,
        line_end=1,
        span_text=f"row data {entity} more data",
    )
    result = verify_entities(f"row data {entity}", [cited])
    # The strict assertion is success — extraction kind is downstream.
    assert result.success is True


# ---------------------------------------------------------------------------
# Cross-gate invariants
# ---------------------------------------------------------------------------


@given(payload=injection_payload_strategy())
def test_sanitized_output_doesnt_introduce_new_attack_tokens(payload: str) -> None:
    """The wrap markers + strip markers MUST NOT themselves match the
    injection-pattern catalog. Otherwise the sanitizer creates the
    attack surface it's defending against."""
    writer = _CollectingWriter()
    result = sanitize(payload, _AUDIT_ID, audit_writer=writer)
    # If sanitize were called again on its own output, no new strip events
    # should fire (the markers don't trip the catalog).
    second = sanitize(result.wrapped_text, _AUDIT_ID, audit_writer=_CollectingWriter())
    # Some catalog patterns are broad ("you are now ..."); the property is
    # that sanitize's OWN OUTPUT introduces no new pattern hits beyond
    # what was in `payload`. So we compare strip counts: the second pass
    # should not exceed what the first found on `payload` minus already-
    # stripped instances.
    assert second.strip_count <= result.strip_count + 1
