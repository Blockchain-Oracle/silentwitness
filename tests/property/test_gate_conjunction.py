"""End-to-end conjunction property for the verification gates.

Individually-passing gates (citation, entity) are necessary but not
sufficient for ``record_observation`` — the architecture §4.5 / §4.7
contract is that BOTH gates accept the same observation in
conjunction. This module pins exactly that invariant under random
input. If Hypothesis finds an input where one gate accepts and the
other does not, a gate has drifted from the contract.
"""

from __future__ import annotations

import dataclasses

from hypothesis import HealthCheck, given, settings

from silentwitness_common.types import CitedSpan
from silentwitness_mcp.index.store import IndexRecord
from silentwitness_mcp.verification.citation_gate import verify_citation
from silentwitness_mcp.verification.entity_gate import verify_entities
from tests.property.strategies import dfir_entity_strategy, index_record_strategy


@given(record=index_record_strategy(), entity=dfir_entity_strategy())
@settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
def test_both_gates_accept_valid_observation(record: IndexRecord, entity: str) -> None:
    """Load-bearing conjunction property (architecture §4.5 + §4.7):
    for an index record carrying a line with a DFIR entity, a cited_span
    quoting that line is accepted by BOTH the citation gate (verbatim
    substring of the record) AND the entity gate (entity present in the
    cited span)."""
    entity_line = f"connection to {entity} observed"
    rec = dataclasses.replace(record, text=record.text + "\n" + entity_line)  # type: ignore[type-var]
    assert rec.id is not None
    cited = CitedSpan(record_id=rec.id, span_text=entity_line)
    obs_text = f"observed {entity} per span"
    citation_result = verify_citation(cited, {rec.id: rec})
    entity_result = verify_entities(obs_text, [cited])
    assert citation_result.success is True, (
        f"citation gate rejected; reason={citation_result.reason} context={citation_result.context}"
    )
    assert entity_result.success is True, (
        f"entity gate rejected; hallucinated="
        f"{[(h.text, h.kind.value) for h in entity_result.hallucinated]}"
    )
