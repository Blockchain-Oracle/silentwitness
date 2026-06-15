"""Unit tests for findings/corroboration.py — the pure tier classifier."""

from __future__ import annotations

from silentwitness_mcp.findings.corroboration import (
    CorroborationTier,
    categorize,
    classify,
)
from silentwitness_mcp.index.store import IndexRecord


def _rec(source_tool: str, text: str = "x") -> IndexRecord:
    return IndexRecord(
        text=text,
        source_tool=source_tool,
        artifact_path="m.raw",
        host="H",
        ts="",
        audit_id="A",
        sha256="s",
    )


# ---------------------------------------------------------------------------
# categorize() — the prefix lookup
# ---------------------------------------------------------------------------


def test_categorize_known_prefixes() -> None:
    assert categorize("vol:pslist") == "memory"
    assert categorize("vol:netscan") == "memory"
    assert categorize("evtx:Security") == "system_log"
    assert categorize("regipy:NTUSER") == "registry"
    assert categorize("mft") == "filesystem"
    assert categorize("usnjrnl") == "filesystem"
    assert categorize("prefetch") == "user_activity"
    assert categorize("sigma:critical") == "detection"
    assert categorize("plaso") == "timeline_breadth"


def test_categorize_unknown_falls_to_other() -> None:
    assert categorize("brand_new_feeder") == "other"
    assert categorize("totally:unknown") == "other"
    assert categorize("") == "other"


def test_exact_match_beats_prefix() -> None:
    """``mft`` matches as a plain key; a hypothetical ``mft:xyz`` would also
    take the ``mft`` family. Different category-key shapes coexist."""
    assert categorize("mft") == "filesystem"


# ---------------------------------------------------------------------------
# classify() — the tier rule
# ---------------------------------------------------------------------------


def test_two_distinct_categories_yields_confirmed() -> None:
    """Disk row (registry) + memory row (vol:netscan) → CONFIRMED. This is the
    headline use-case the memory ingest enables."""
    records = [_rec("regipy:NTUSER"), _rec("vol:netscan")]
    tier, categories = classify(records)
    assert tier is CorroborationTier.CONFIRMED
    assert categories == frozenset({"registry", "memory"})


def test_three_distinct_categories_still_confirmed() -> None:
    records = [_rec("regipy:NTUSER"), _rec("vol:pslist"), _rec("evtx:Security")]
    tier, categories = classify(records)
    assert tier is CorroborationTier.CONFIRMED
    assert categories == frozenset({"registry", "memory", "system_log"})


def test_two_same_category_records_yields_inferred() -> None:
    """Two vol:* rows are the same lens (memory) — they multiply touchpoints but
    don't triangulate. INFERRED."""
    records = [_rec("vol:pslist"), _rec("vol:netscan")]
    tier, categories = classify(records)
    assert tier is CorroborationTier.INFERRED
    assert categories == frozenset({"memory"})


def test_two_evtx_rows_yields_inferred() -> None:
    """Same rationale: two evtx rows from different channels are still both
    system_log under our category model."""
    records = [_rec("evtx:Security"), _rec("evtx:System")]
    tier, _ = classify(records)
    assert tier is CorroborationTier.INFERRED


def test_single_record_yields_unverified() -> None:
    records = [_rec("sigma:critical")]
    tier, categories = classify(records)
    assert tier is CorroborationTier.UNVERIFIED
    assert categories == frozenset({"detection"})


def test_empty_records_yields_unverified() -> None:
    """A finding with zero resolvable cited records is, by definition, unverified.
    Categories is empty — no signal to render in the badge."""
    tier, categories = classify([])
    assert tier is CorroborationTier.UNVERIFIED
    assert categories == frozenset()


def test_unknown_source_tools_clustered_as_one_category() -> None:
    """Multiple unmapped source_tools all land in ``other`` — they shouldn't be
    treated as independent. Two unknown rows is INFERRED, not CONFIRMED."""
    records = [_rec("foo"), _rec("bar")]
    tier, categories = classify(records)
    assert tier is CorroborationTier.INFERRED
    assert categories == frozenset({"other"})


def test_one_known_plus_one_unknown_is_confirmed() -> None:
    """A known category + ``other`` is still two distinct categories → CONFIRMED.
    Deliberate — once we have a mapped-family row, the unmapped one independently
    triangulates regardless of its name."""
    records = [_rec("vol:pslist"), _rec("brand_new_feeder")]
    tier, categories = classify(records)
    assert tier is CorroborationTier.CONFIRMED
    assert categories == frozenset({"memory", "other"})
