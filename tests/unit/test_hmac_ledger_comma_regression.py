"""Regression coverage for comma handling in HMAC ledger composition."""

from __future__ import annotations

from silentwitness_common.types import Confidence
from silentwitness_mcp.audit.ledger import InterpretationParts, LedgerComposer, ObservationParts


def test_compose_observation_allows_commas_in_text() -> None:
    parts = ObservationParts(text="evil.exe ran, then exited", audit_ids=("a",))
    assert LedgerComposer.observation(parts) == b"evil.exe ran, then exited|a"


def test_compose_interpretation_allows_commas_in_text() -> None:
    parts = InterpretationParts(
        observation_id="O-042",
        text="malware detonated, then persisted",
        confidence=Confidence.HIGH,
    )
    assert LedgerComposer.interpretation(parts) == b"O-042|malware detonated, then persisted|HIGH"
