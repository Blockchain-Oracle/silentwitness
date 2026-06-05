"""End-to-end conjunction property for the verification wedge.

Individually-passing gates (citation, entity) are necessary but not
sufficient for ``record_observation`` — the architecture §4.5 / §4.7
contract is that BOTH gates accept the same observation in
conjunction. This module pins exactly that invariant under random
input. If Hypothesis finds an input where one gate accepts and the
other does not, a gate has drifted from the contract.

Lives in its own file (separate from ``test_gates.py``) because the
file-size guard treats this as a load-bearing property worth its own
module boundary, and so that the conjunction property's failure
output isn't buried among the per-gate test verdicts.
"""

from __future__ import annotations

from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.strategies import DataObject
from pytest import TempPathFactory

from silentwitness_mcp.verification.citation_gate import verify_citation
from silentwitness_mcp.verification.entity_gate import verify_entities
from tests.property.strategies import (
    audit_entry_strategy,
    cited_span_strategy,
    dfir_entity_strategy,
)


@given(data=st.data(), entity=dfir_entity_strategy())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow],
    deadline=None,
)
def test_both_gates_accept_valid_observation(
    tmp_path_factory: TempPathFactory, data: DataObject, entity: str
) -> None:
    """The wedge's load-bearing property: for a randomly constructed
    observation whose cited span contains a DFIR entity, BOTH the
    citation gate AND the entity gate accept."""
    from silentwitness_common.types import CitedSpan

    tmpdir = tmp_path_factory.mktemp("conjunction", numbered=True)
    entry, payload = data.draw(audit_entry_strategy(tmpdir))
    span = data.draw(cited_span_strategy(entry, payload))
    assume(span is not None)
    assert span is not None
    # Plant the entity into observation_text AND into a cited span
    # whose audit_id is in the index. Citation gate accepts the
    # byte-level span; entity gate accepts because the entity is
    # present in both the observation and a cited span.
    entity_cited = CitedSpan(
        audit_id=entry.audit_id,
        sha256_of_normalized_output=span.sha256_of_normalized_output,
        line_start=span.line_start,
        line_end=span.line_end,
        span_text=f"{span.span_text} {entity}",
    )
    obs_text = f"observed {entity} per span"
    citation_result = verify_citation(span, audit_index={entry.audit_id: entry})
    entity_result = verify_entities(obs_text, [entity_cited])
    assert citation_result.success is True, (
        f"citation gate rejected; reason={citation_result.reason} context={citation_result.context}"
    )
    assert entity_result.success is True, (
        f"entity gate rejected; hallucinated="
        f"{[(h.text, h.kind.value) for h in entity_result.hallucinated]}"
    )
