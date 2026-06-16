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
    # Memory (vol3 plugins)
    assert categorize("vol:pslist") == "memory"
    assert categorize("vol:netscan") == "memory"
    assert categorize("vol:cmdline") == "memory"
    assert categorize("vol:malfind") == "memory"
    assert categorize("vol:psscan") == "memory"
    # System log
    assert categorize("evtx:Security") == "system_log"
    assert categorize("evtx:System") == "system_log"
    assert categorize("evtx:Application") == "system_log"
    # PowerShell transcripts are emitted as `powershell:transcript` — the round-1
    # review caught this being silently miscategorised as `other` when the map
    # keyed `pstranscript` instead.
    assert categorize("powershell:transcript") == "system_log"
    # Registry (incl. Amcache subkey)
    assert categorize("regipy:NTUSER") == "registry"
    assert categorize("regipy:Amcache_associations") == "registry"
    # Filesystem
    assert categorize("mft") == "filesystem"
    assert categorize("usnjrnl") == "filesystem"
    # User activity (SRUM lives here too — net+app-usage telemetry)
    assert categorize("prefetch") == "user_activity"
    assert categorize("lnk") == "user_activity"
    assert categorize("jumplist:auto") == "user_activity"
    assert categorize("srum:network_usage") == "user_activity"
    # Network evidence
    assert categorize("zeek:conn") == "network"
    assert categorize("zeek:dns") == "network"
    assert categorize("zeek:http") == "network"
    # Detection (Sigma — any severity bucket)
    assert categorize("sigma:critical") == "detection"
    assert categorize("sigma:high") == "detection"
    assert categorize("sigma:medium") == "detection"
    # Timeline breadth
    assert categorize("plaso") == "timeline_breadth"
    assert categorize("plaso:winreg") == "timeline_breadth"


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


# ---------------------------------------------------------------------------
# Drift gate — couples the category map to actual feeder emissions
# ---------------------------------------------------------------------------


def test_every_feeder_source_tool_prefix_is_mapped() -> None:
    """Walk every ``feeders_*.py`` + ``ingest.py`` for ``source_tool=`` literals.
    Every prefix MUST resolve to a real category (not ``other``).

    Round-1 review caught ``powershell:transcript`` silently classifying as
    ``other`` because the map keyed ``pstranscript`` instead. This test exists
    so the next feeder rename / addition fails LOUDLY here instead of silently
    downgrading findings in production."""
    import re
    from pathlib import Path

    index_dir = Path(__file__).resolve().parents[2] / "src" / "silentwitness_mcp" / "index"
    # Match `source_tool="…"` and `source_tool=f"…"` — string-literal RHS only.
    # Skips variable pass-throughs like ``source_tool=source_tool``.
    pattern = re.compile(r'source_tool\s*=\s*f?"(?P<value>[^"]+)"')
    found_prefixes: set[str] = set()
    for py in [*sorted(index_dir.glob("feeders_*.py")), index_dir / "ingest.py"]:
        for match in pattern.finditer(py.read_text(encoding="utf-8")):
            raw = match.group("value")
            # Strip f-string placeholders ({channel}, {plugin}, …) so we get the
            # static family prefix.
            family = raw.split(":")[0].split("{")[0]
            if family and family.isidentifier():
                found_prefixes.add(family)

    misrouted = {p for p in found_prefixes if categorize(p) == "other"}
    assert not misrouted, (
        f"Source_tool prefixes {sorted(misrouted)} fall through to 'other'. "
        f"Add them to _SOURCE_CATEGORY in findings/corroboration.py — "
        f"a silently-'other' prefix can falsely upgrade a finding to CONFIRMED."
    )
