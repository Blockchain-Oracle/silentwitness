"""Round-4 review-fix tests for record_observation.

Pins the round-3 fixes that the round-3 commit closed in code but
NOT in the test suite (round-3 pr-test-analyzer C1/C2/C3 + H1/H2):

* C1 — audit-write retry inside the outer finally
* C2 — except Exception catch-all (TypeError / ImportError / RuntimeError)
* C3 — scrub_line_terminators across all 8 forbidden chars
* H1 — ENTITY_GATE_UNAVAILABLE direct path
* H2 — FINDINGS_STORE_UNWRITABLE outer-OSError path

Also lands the canonical audit-row property invariant (round-3 pr-test
L1): every call appends exactly one row regardless of pipeline outcome.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.findings import observation as obs_mod
from silentwitness_mcp.findings.observation import (
    ObservationInput,
    ObservationRejectReason,
    record_observation,
)
from silentwitness_mcp.verification.entity_gate import EntityGateModelError
from tests.integration.conftest import (
    MODEL,
    cited_span_for,
    write_blob_and_entry,
)

CaseEnv = tuple[Path, Path, AuditLogger]

_CONTENT = b"PID 4 System idle process\n"
_SPAN_TEXT = "PID 4"


def _basic_payload(case_env: CaseEnv) -> tuple[ObservationInput, dict[str, object]]:
    _case_dir, blobs_dir, logger = case_env
    aid = logger.next_audit_id()
    entry = write_blob_and_entry(blobs_dir, audit_id=aid, content=_CONTENT)
    span = cited_span_for(_CONTENT, aid, span_text=_SPAN_TEXT)
    payload = ObservationInput(text="PID 4 System idle", cited_spans=(span,), audit_ids=(aid,))
    return payload, {aid: entry}


# ---------------------------------------------------------------------------
# C1 — audit-write retry path inside finally
# ---------------------------------------------------------------------------


def test_audit_write_failure_inside_finally_still_returns_envelope(
    case_env: CaseEnv,
) -> None:
    """If _write_audit_row raises (disk full / path occupied / permission),
    the inner try/except inside finally must rewrite the result to
    FINDINGS_STORE_UNWRITABLE and STILL return the envelope. Without
    this guard the original pipeline exception would mask everything
    and the audit row would silently vanish."""
    case_dir, _, _ = case_env
    audit_dir = case_dir / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    # Place a directory where the JSONL file should be → append fails.
    (audit_dir / "findings.jsonl").mkdir()
    payload, audit_index = _basic_payload(case_env)
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index=audit_index,
        audit_logger=case_env[2],
        model_used=MODEL,
    )
    # Envelope returns cleanly — that's the load-bearing promise.
    assert envelope.success is True
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.FINDINGS_STORE_UNWRITABLE
    assert envelope.data.context.get("audit_write_failed") is True
    assert envelope.data.context.get("stage") == "audit_write"


# ---------------------------------------------------------------------------
# C2 — except Exception catch-all (TypeError + ImportError)
# ---------------------------------------------------------------------------


def test_typeerror_mid_pipeline_caught_as_pipeline_internal_error(
    case_env: CaseEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A TypeError raised by an integration-layer bug (e.g. malformed
    audit_index) must NOT leak past the envelope. The broadened
    except Exception is the only thing that catches it."""

    def _boom(*_a: object, **_kw: object) -> None:
        raise TypeError("synthetic mid-pipeline TypeError")

    monkeypatch.setattr(obs_mod, "verify_citation", _boom)
    payload, audit_index = _basic_payload(case_env)
    case_dir, _, logger = case_env
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index=audit_index,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.success is True
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.PIPELINE_INTERNAL_ERROR
    assert envelope.data.context["error_type"] == "TypeError"
    assert (case_dir / "audit" / "findings.jsonl").exists()


def test_importerror_mid_pipeline_caught_as_pipeline_internal_error(
    case_env: CaseEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Locks the catch tuple's BREADTH — narrowing back to
    (OSError, ValueError, ...) would let ImportError through."""

    def _boom(*_a: object, **_kw: object) -> None:
        raise ImportError("synthetic mid-pipeline ImportError")

    monkeypatch.setattr(obs_mod, "verify_citation", _boom)
    payload, audit_index = _basic_payload(case_env)
    case_dir, _, logger = case_env
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index=audit_index,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.reason == ObservationRejectReason.PIPELINE_INTERNAL_ERROR
    assert envelope.data.context["error_type"] == "ImportError"


# ---------------------------------------------------------------------------
# C3 — scrub_line_terminators across all 8 forbidden chars
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "attack_char,codename",
    [
        ("\u2028", "LINE SEPARATOR"),
        ("\u2029", "PARAGRAPH SEPARATOR"),
        ("\x85", "NEL"),
        ("\x0b", "VT"),
        ("\x0c", "FF"),
        ("\x1c", "FS"),
        ("\x1d", "GS"),
        ("\x1e", "RS"),
    ],
)
def test_forbidden_line_terminators_scrubbed_from_audit_row(
    case_env: CaseEnv, attack_char: str, codename: str
) -> None:
    """Every char in _LINE_TERMINATOR_CHARS must round-trip cleanly
    through the audit-row write. A regression that drops one char would
    re-introduce the round-2 silent-failure C2 attack surface for that
    specific char."""
    case_dir, blobs_dir, logger = case_env
    aid = logger.next_audit_id()
    entry = write_blob_and_entry(blobs_dir, audit_id=aid, content=_CONTENT)
    span = cited_span_for(_CONTENT, aid, span_text=_SPAN_TEXT)
    payload = ObservationInput(
        text=f"PID 4 System{attack_char}injection-{codename}",
        cited_spans=(span,),
        audit_ids=(aid,),
    )
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index={aid: entry},
        audit_logger=logger,
        model_used=MODEL,
    )
    findings_log = case_dir / "audit" / "findings.jsonl"
    assert findings_log.exists(), f"audit row missing for {codename}"
    row = json.loads(findings_log.read_text().strip().split("\n")[0])
    assert attack_char not in row["params"]["text"]
    assert "\ufffd" in row["params"]["text"]
    # Envelope wrap stays clean across all 8.
    assert envelope.success is True


# ---------------------------------------------------------------------------
# H1 — ENTITY_GATE_UNAVAILABLE direct path
# ---------------------------------------------------------------------------


def test_entity_gate_unavailable_reject(case_env: CaseEnv, monkeypatch: pytest.MonkeyPatch) -> None:
    """spaCy model unavailable → ENTITY_GATE_UNAVAILABLE + audit row + envelope.
    Distinct from PIPELINE_INTERNAL_ERROR so the agent can decide between
    retry (cold-start) and escalate."""

    def _no_spacy(*_a: object, **_kw: object) -> None:
        raise EntityGateModelError("spaCy en_core_web_lg unavailable")

    monkeypatch.setattr(obs_mod, "verify_entities", _no_spacy)
    payload, audit_index = _basic_payload(case_env)
    case_dir, _, logger = case_env
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index=audit_index,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.ENTITY_GATE_UNAVAILABLE
    assert envelope.data.context["stage"] == "entity_gate"
    assert (case_dir / "audit" / "findings.jsonl").exists()


# ---------------------------------------------------------------------------
# H2 — FINDINGS_STORE_UNWRITABLE outer-OSError path
# ---------------------------------------------------------------------------


def test_findings_store_unwritable_outer_oserror(
    case_env: CaseEnv, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OSError during allocate_observation_id (write side) → outer
    except OSError → FINDINGS_STORE_UNWRITABLE."""

    def _boom(*_a: object, **_kw: object) -> str:
        raise PermissionError("synthetic findings.json EACCES")

    monkeypatch.setattr(obs_mod, "allocate_observation_id", _boom)
    payload, audit_index = _basic_payload(case_env)
    case_dir, _, logger = case_env
    envelope = record_observation(
        payload,
        case_dir=case_dir,
        audit_index=audit_index,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert envelope.data.success is False
    assert envelope.data.reason == ObservationRejectReason.FINDINGS_STORE_UNWRITABLE
    assert envelope.data.context["stage"] == "findings_write"
    assert envelope.data.context["error_type"] == "PermissionError"
    assert (case_dir / "audit" / "findings.jsonl").exists()


# ---------------------------------------------------------------------------
# Property — every call produces exactly one audit row (pr-test L1)
# ---------------------------------------------------------------------------


@given(failure_mode=st.sampled_from(["none", "type_error", "entity_unavailable", "oserror"]))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None)
def test_exactly_one_audit_row_per_call_regardless_of_outcome(
    case_env: CaseEnv,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
) -> None:
    """Architecture §4.4 canonical promise: every record_observation call
    appends exactly one row to audit/findings.jsonl regardless of accept,
    reject, or pipeline failure. This property is the load-bearing
    invariant the entire wedge depends on."""
    case_dir, _, logger = case_env
    findings_log = case_dir / "audit" / "findings.jsonl"
    rows_before = (
        len([ln for ln in findings_log.read_text().splitlines() if ln.strip()])
        if findings_log.exists()
        else 0
    )
    payload, audit_index = _basic_payload(case_env)

    if failure_mode == "type_error":

        def _boom(*_a: object, **_kw: object) -> None:
            raise TypeError("synthetic")

        monkeypatch.setattr(obs_mod, "verify_citation", _boom)
    elif failure_mode == "entity_unavailable":

        def _no_spacy(*_a: object, **_kw: object) -> None:
            raise EntityGateModelError("synthetic")

        monkeypatch.setattr(obs_mod, "verify_entities", _no_spacy)
    elif failure_mode == "oserror":

        def _boom(*_a: object, **_kw: object) -> str:
            raise PermissionError("synthetic")

        monkeypatch.setattr(obs_mod, "allocate_observation_id", _boom)

    record_observation(
        payload,
        case_dir=case_dir,
        audit_index=audit_index,
        audit_logger=logger,
        model_used=MODEL,
    )
    assert findings_log.exists()
    rows_after = len([ln for ln in findings_log.read_text().splitlines() if ln.strip()])
    assert rows_after == rows_before + 1, (
        f"expected +1 audit row, got delta={rows_after - rows_before} (failure_mode={failure_mode})"
    )
