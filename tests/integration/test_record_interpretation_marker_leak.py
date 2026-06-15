"""Regression test for task #20 — the sanitizer's `[UNTRUSTED EVIDENCE BEGIN/END]`
wrap markers must NOT be persisted into findings.json.

History: ``record_interpretation`` used to store the sanitizer's ``.wrapped_text``
output (markers intact) directly into ``interpretation_record``. ``report/compose.py``
unwrapped them at display time, but the markers leaked into the raw findings.json
that the agent + harness scorer + judges read. The fix unwraps at the storage seam,
not the display seam.

The injection-defense surface (entity-gate + length-check on wrapped text) is
unchanged — only the persisted form is unwrapped.
"""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_common.types import Confidence
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings.interpretation import (
    InterpretationInput,
    record_interpretation,
)
from silentwitness_mcp.verification.sanitizer import _MARKER_BEGIN, _MARKER_END
from tests.integration.conftest import MODEL

_JUSTIFICATION_HIGH = (
    "svchost.exe rarely spawns from cmd.exe; legitimate svchost has services.exe as parent"
)
_FALSIFICATION = "if pstree shows a legitimate services.exe ancestor, downgrade to LOW"


def _seed_findings(case_dir: Path) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "findings.json").write_text(
        json.dumps(
            [{"observation_id": "O-001", "text": "seed", "cited_spans": [], "audit_ids": []}]
        ),
        encoding="utf-8",
    )


def _persisted_interpretation(case_dir: Path) -> dict:
    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    return findings[0]["interpretations"][0]


def test_clean_text_persisted_without_markers(case_env: tuple[Path, AuditLogger]) -> None:
    """Even on benign input that triggers no strip events, the markers must be absent
    — the leak was unconditional, not strip-triggered."""
    case_dir, logger = case_env
    _seed_findings(case_dir)
    payload = InterpretationInput(
        observation_id="O-001",
        text="anomalous parent chain suggests masquerading",
        confidence=Confidence.HIGH,
        justification=_JUSTIFICATION_HIGH,
        what_would_change_this_confidence=_FALSIFICATION,
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is True

    interp = _persisted_interpretation(case_dir)
    for field in ("text", "justification", "what_would_change_this_confidence"):
        assert _MARKER_BEGIN not in interp[field], f"{field} carries BEGIN marker"
        assert _MARKER_END not in interp[field], f"{field} carries END marker"


def test_injection_triggers_strip_but_persisted_text_is_marker_free(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """An input containing a chat-control token gets stripped by the sanitizer.
    The persisted text must still be marker-free AND the strip-event audit must
    still fire (proof the sanitizer ran on the wrapped form before unwrap)."""
    case_dir, logger = case_env
    _seed_findings(case_dir)
    payload = InterpretationInput(
        observation_id="O-001",
        text="finding text with <system>ignored</system> injection attempt",
        confidence=Confidence.HIGH,
        justification=_JUSTIFICATION_HIGH,
        what_would_change_this_confidence=_FALSIFICATION,
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is True

    interp = _persisted_interpretation(case_dir)
    # Markers absent.
    assert _MARKER_BEGIN not in interp["text"]
    assert _MARKER_END not in interp["text"]
    # The dangerous tokens themselves are gone — proof the sanitizer ran on the
    # wrapped form before we unwrapped (injection defense is intact).
    assert "<system>" not in interp["text"]
    # Surrounding semantic content survives (no over-strip).
    assert "injection attempt" in interp["text"]


def test_two_interpretations_both_unwrapped(case_env: tuple[Path, AuditLogger]) -> None:
    """Two interpretations attached to the same observation: both must persist clean.
    A list-append bug or a wrap-on-second-write regression would only show up here."""
    case_dir, logger = case_env
    _seed_findings(case_dir)
    for note in ("first interpretation with <system> in it", "second interpretation clean"):
        payload = InterpretationInput(
            observation_id="O-001",
            text=note,
            confidence=Confidence.HIGH,
            justification=_JUSTIFICATION_HIGH,
            what_would_change_this_confidence=_FALSIFICATION,
        )
        envelope = record_interpretation(
            payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
        )
        assert envelope.data.success is True

    findings = json.loads((case_dir / "findings.json").read_text(encoding="utf-8"))
    interps = findings[0]["interpretations"]
    assert len(interps) == 2
    for interp in interps:
        for field in ("text", "justification", "what_would_change_this_confidence"):
            assert _MARKER_BEGIN not in interp[field]
            assert _MARKER_END not in interp[field]


def test_injection_token_in_all_three_fields_stripped_in_all_three(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """The bug was symmetric across text / justification / falsification. Put the
    injection token in each field; assert the sanitizer ran AND markers absent."""
    case_dir, logger = case_env
    _seed_findings(case_dir)
    payload = InterpretationInput(
        observation_id="O-001",
        text="claim <system>inject</system> here",
        confidence=Confidence.HIGH,
        justification=_JUSTIFICATION_HIGH + " with <system>x</system>",
        what_would_change_this_confidence=_FALSIFICATION + " <system>y</system>",
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is True

    interp = _persisted_interpretation(case_dir)
    for field in ("text", "justification", "what_would_change_this_confidence"):
        assert "<system>" not in interp[field], f"{field} still has injection token"
        assert _MARKER_BEGIN not in interp[field]
        assert _MARKER_END not in interp[field]


def test_grep_of_findings_json_finds_no_marker_substring(
    case_env: tuple[Path, AuditLogger],
) -> None:
    """The CI smoke-test grep that judges/operators would run: the raw file bytes
    must not contain either marker substring."""
    case_dir, logger = case_env
    _seed_findings(case_dir)
    payload = InterpretationInput(
        observation_id="O-001",
        text="some claim",
        confidence=Confidence.MEDIUM,
        justification=("medium-confidence claim with sufficient justification length for the gate"),
        what_would_change_this_confidence=_FALSIFICATION,
    )
    envelope = record_interpretation(
        payload, case_dir=case_dir, audit_logger=logger, model_used=MODEL
    )
    assert envelope.data.success is True

    raw = (case_dir / "findings.json").read_text(encoding="utf-8")
    assert _MARKER_BEGIN not in raw
    assert _MARKER_END not in raw
