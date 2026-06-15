"""Phase 6a — corroboration tier badge rendering in compose_findings.

Split off from test_report_writer_compose.py to stay under the 400-LOC gate."""

from __future__ import annotations

from silentwitness_agent.report.compose import compose_findings
from tests.unit._compose_fixtures import _finding, _obs


def test_compose_findings_renders_corroboration_badge() -> None:
    obs = _obs("O-001", "Malicious PE discovered.", ["aid-1"], "I-001", "Attacker dropper.")
    finding = _finding("F-001", "O-001", "I-001")
    finding["corroboration_tier"] = "CONFIRMED"
    finding["corroboration_categories"] = ["memory", "registry"]
    result = compose_findings([finding], {"O-001": obs})
    assert "**Corroboration:** `CONFIRMED`" in result
    assert "memory + registry" in result


def test_compose_findings_no_badge_when_tier_field_absent() -> None:
    """Legacy findings (materialised before Phase 6a) carry no tier — the section
    renders unchanged so old reports don't break."""
    obs = _obs("O-001", "text", ["aid-1"], "I-001", "interp")
    finding = _finding("F-001", "O-001", "I-001")  # no tier field
    result = compose_findings([finding], {"O-001": obs})
    assert "Corroboration:" not in result


def test_compose_findings_unverified_tier_renders_without_categories() -> None:
    """An UNVERIFIED finding has an empty categories list — the badge still
    renders the tier label so the signal is visible."""
    obs = _obs("O-001", "text", ["aid-1"], "I-001", "interp")
    finding = _finding("F-001", "O-001", "I-001")
    finding["corroboration_tier"] = "UNVERIFIED"
    finding["corroboration_categories"] = []
    result = compose_findings([finding], {"O-001": obs})
    assert "**Corroboration:** `UNVERIFIED`" in result


def test_badge_renders_between_confidence_and_affected_systems() -> None:
    """Structural placement check — the badge must appear between the Confidence
    line and the Affected systems line, not at the section footer. A regression
    that moves it to the end would otherwise pass the substring tests."""
    import re

    obs = _obs("O-001", "text", ["aid-1"], "I-001", "interp")
    finding = _finding("F-001", "O-001", "I-001")
    finding["corroboration_tier"] = "CONFIRMED"
    finding["corroboration_categories"] = ["memory", "registry"]
    result = compose_findings([finding], {"O-001": obs})
    assert re.search(
        r"\*\*Confidence:\*\*.*\n\*\*Corroboration:\*\*.*\n\*\*Affected systems:\*\*",
        result,
        re.S,
    ), result


def test_badge_handles_malformed_categories_field() -> None:
    """Defense in depth — a finding with `corroboration_tier` set but
    `corroboration_categories` as something other than a list still renders
    the tier label (no suffix). Catches a future schema regression."""
    obs = _obs("O-001", "text", ["aid-1"], "I-001", "interp")
    finding = _finding("F-001", "O-001", "I-001")
    finding["corroboration_tier"] = "INFERRED"
    finding["corroboration_categories"] = "not-a-list"  # type: ignore[assignment]
    result = compose_findings([finding], {"O-001": obs})
    assert "**Corroboration:** `INFERRED`" in result
