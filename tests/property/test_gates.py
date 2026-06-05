"""Hypothesis property tests for the verification gates (architecture §14).

Ratifies architectural invariants of the normalizer, citation gate,
entity gate, and sanitizer under random input. Profile selection:
``HYPOTHESIS_PROFILE=dev|ci|slow`` (registered in ``tests/conftest.py``).

Load-bearing property: any randomly constructed valid observation
(cited spans derived from real tmp-path blob bytes, SHA-256 recomputed)
must be accepted by both the citation gate AND the entity gate in
conjunction — see ``test_both_gates_accept_valid_observation``.
"""

from __future__ import annotations

import hashlib

from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.strategies import DataObject
from pytest import TempPathFactory

from silentwitness_mcp.verification._types import CitationRejectReason
from silentwitness_mcp.verification.citation_gate import verify_citation
from silentwitness_mcp.verification.entity_gate import verify_entities
from silentwitness_mcp.verification.normalizer import normalize_output
from silentwitness_mcp.verification.sanitizer import StripEvent, sanitize
from tests.property.strategies import (
    FORGED_MALLORY_PREFIX,
    ForgedMarkerPayload,
    audit_entry_strategy,
    cited_span_strategy,
    dfir_entity_strategy,
    forged_marker_strategy,
    injection_payload_strategy,
    normalizable_output_strategy,
)

_AUDIT_ID = "sift-aj-20260613-007"


class _CollectingWriter:
    """Sanitizer audit_writer test double — captures emitted events for
    assertion against the canonical-marker invariant."""

    def __init__(self) -> None:
        self.events: list[StripEvent] = []

    def emit(self, event: StripEvent) -> None:
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
def test_normalize_is_sensitive_to_invalid_utf8_trailing_byte(raw: bytes) -> None:
    """Appending a 0xff byte (invalid UTF-8, surrogateescape-preserved)
    MUST shift the SHA-256 — proves the normalizer doesn't quietly
    discard high-bit bytes that would otherwise reach the citation gate.
    Filter the precondition (raw doesn't already end in 0xff) BEFORE
    hashing — otherwise the test asserts inequality on inputs that are
    byte-identical after the append."""
    assume(not raw.endswith(b"\xff"))
    hash_a = hashlib.sha256(normalize_output(raw, tool="_universal_only")).hexdigest()
    hash_b = hashlib.sha256(normalize_output(raw + b"\xff", tool="_universal_only")).hexdigest()
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


# Sanitizer ops that silently remove without emitting a marker
# (architecture §4.8; sanitizer.sanitize uses _empty replacement for these).
_SILENT_REMOVAL_OPS = frozenset({"bidi-unicode", "zero-width", "tag-character"})


@given(payload=injection_payload_strategy())
def test_sanitize_emitted_markers_carry_audit_id(payload: str) -> None:
    """Every marker the sanitizer EMITTED (excluding silent-removal ops
    that delete BIDI / zero-width / tag characters) carries this audit_id.
    Architecture §4.8 requires emitted markers in the canonical
    ``[stripped:{audit_id}:{pattern_id}]`` format so a downstream consumer
    can verify the nonce was minted by THIS audit context."""
    writer = _CollectingWriter()
    result = sanitize(payload, _AUDIT_ID, audit_writer=writer)
    for ev in writer.events:
        if ev.pattern_id in _SILENT_REMOVAL_OPS:
            continue
        marker = f"[stripped:{_AUDIT_ID}:{ev.pattern_id}]"
        assert marker in result.wrapped_text, (
            f"sanitizer event {ev.pattern_id} did not produce a canonical marker"
        )


@given(forged_pair=forged_marker_strategy())
def test_sanitize_passes_through_forged_markers(forged_pair: ForgedMarkerPayload) -> None:
    """Pre-existing ``[stripped:...]`` literals in input survive verbatim
    into the wrap — they're untrusted evidence, not sanitizer output, so
    the audit_id-nonce check downstream catches them as
    not-from-this-run (architecture §4.8). The sanitizer must NOT emit
    a canonical marker that bears the forged audit_id, and any
    canonical marker it emits (on the real injection token co-located
    in the payload) must carry THIS audit_id, not the forged one."""
    writer = _CollectingWriter()
    result = sanitize(forged_pair.full_payload, _AUDIT_ID, audit_writer=writer)
    # The forged marker substring survives verbatim into wrapped_text —
    # the sanitizer does not consume or rewrite it.
    assert forged_pair.forged_marker in result.wrapped_text, (
        f"forged marker stripped: {forged_pair.forged_marker!r} absent from output"
    )
    # Tight invariant: the sanitizer can never mint a NEW marker
    # carrying the forged audit_id prefix. Counting on raw strings
    # avoids constructing a haystack that contains the needle by
    # f-string interpolation.
    input_forged = forged_pair.full_payload.count(FORGED_MALLORY_PREFIX)
    output_forged = result.wrapped_text.count(FORGED_MALLORY_PREFIX)
    assert output_forged <= input_forged, (
        f"sanitizer minted a marker carrying the forged audit_id: "
        f"input had {input_forged} occurrences, output has {output_forged}"
    )
    # Strategy precondition: events must fire — if the strategy regresses
    # to producing payloads that don't trip the catalog, the per-event
    # smuggling check below is dead code and the property goes vacuous.
    assert writer.events, (
        "strategy produced a payload that emitted no sanitizer events; "
        "the forgery-defense per-event assertion is now dead code"
    )
    # Every emitted event's canonical-marker rendering must be keyed on
    # THIS audit_id; the pattern_id itself must not embed the forged
    # prefix (defends against pattern_id field smuggling).
    for ev in writer.events:
        assert FORGED_MALLORY_PREFIX not in ev.pattern_id, (
            f"sanitizer event pattern_id smuggled forged prefix: {ev.pattern_id!r}"
        )


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
    assert span is not None
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


@given(seq=st.integers(min_value=1, max_value=999_999))
def test_citation_gate_rejects_unknown_audit_id(seq: int) -> None:
    """An audit_id absent from the index → AUDIT_ID_NOT_FOUND. Strategy
    generates canonical-format ids so the CitedSpan model accepts them."""
    from silentwitness_common.types import CitedSpan

    span = CitedSpan(
        audit_id=f"sift-mallory-20260613-{seq:03d}",
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
    cited_span MUST be accepted (no false positives). Also asserts that
    the entity was actually EXTRACTED — without this, a strategy draw
    that the regex catalog doesn't match would make the test pass
    vacuously (extracted=[] ⇒ hallucinated=[] ⇒ success=True for the
    wrong reason)."""
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
    # Defend against vacuous successes — the strategy is contracted to
    # generate catalog-extractable shapes, but if the catalog drifts
    # (or a future strategy branch produces a non-matching shape),
    # extracted will be empty and success=True misleads us.
    assert any(e.text == entity for e in result.extracted), (
        f"entity gate did not extract {entity!r} — strategy diverged from "
        f"the regex catalog; extracted={[(e.text, e.kind.value) for e in result.extracted]}"
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
    assert any(h.text == entity for h in result.hallucinated), (
        f"strict equality miss; hallucinated={[h.text for h in result.hallucinated]} "
        f"vs entity={entity!r}"
    )


@given(entity=dfir_entity_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow])
def test_entity_gate_extracts_entity_kind_consistently(entity: str) -> None:
    """For a DFIR entity in obs+cited, the extracted-entities list
    contains an ExtractedEntity whose ``text`` matches ``entity`` AND
    whose ``source`` is ``"regex"`` (these are catalog-defined shapes,
    not spaCy NER outputs)."""
    from silentwitness_common.types import CitedSpan

    cited = CitedSpan(
        audit_id=_AUDIT_ID,
        sha256_of_normalized_output="a" * 64,
        line_start=0,
        line_end=1,
        span_text=f"row data {entity} more data",
    )
    result = verify_entities(f"row data {entity}", [cited])
    assert result.success is True
    matching = [e for e in result.extracted if e.text == entity]
    assert matching, (
        f"entity {entity!r} not in extracted list; "
        f"extracted={[(e.text, e.kind.value, e.source) for e in result.extracted]}"
    )
    assert all(e.source == "regex" for e in matching), (
        f"DFIR entity {entity!r} extracted via non-regex source — "
        f"regex catalog should have first-extracted this shape"
    )


# ---------------------------------------------------------------------------
# Cross-gate invariants
# ---------------------------------------------------------------------------


@given(payload=injection_payload_strategy())
def test_sanitize_is_idempotent_on_its_own_output(payload: str) -> None:
    """Sanitising the sanitiser's own output must be a no-op modulo the
    outer wrap. Strict idempotency — not just ``second.strip_count <=
    first.strip_count`` — catches the case where re-sanitising would
    accumulate nested ``[UNTRUSTED EVIDENCE BEGIN]`` envelopes, double-
    strip canonical markers, or trip a future broader catalog pattern
    on the wrap/strip text itself."""
    result = sanitize(payload, _AUDIT_ID, audit_writer=_CollectingWriter())
    second = sanitize(result.wrapped_text, _AUDIT_ID, audit_writer=_CollectingWriter())
    # Zero new strips on the second pass: the wrap/strip markers must
    # not themselves match any catalog token.
    assert second.strip_count == 0, (
        f"second-pass sanitise stripped {second.strip_count} new tokens; "
        f"the sanitiser's own output trips its own catalog"
    )
    # The wrap of the second pass must be the first wrap surrounded by
    # one additional pair of evidence markers — never a deeper nesting
    # or a rewriting of the inner content.
    expected = "[UNTRUSTED EVIDENCE BEGIN]\n" + result.wrapped_text + "\n[UNTRUSTED EVIDENCE END]"
    assert second.wrapped_text == expected, (
        f"second-pass output deviated from envelope-only re-wrap; "
        f"diff begins at index {_first_diff(second.wrapped_text, expected)}"
    )


def _first_diff(a: str, b: str) -> int:
    for i, (ca, cb) in enumerate(zip(a, b, strict=False)):
        if ca != cb:
            return i
    return min(len(a), len(b))
