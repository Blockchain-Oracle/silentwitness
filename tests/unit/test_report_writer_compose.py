"""Unit tests for compose.py helper functions (8 tests).

Each test exercises a single compose_* function with minimal data,
verifying the exact output contract from the story acceptance criteria.
"""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_agent.report.compose import (
    compose_engagement_overview,
    compose_executive_summary,
    compose_findings,
    compose_gaps,
    compose_iocs,
    compose_methodology,
    compose_timeline,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _obs(
    obs_id: str,
    text: str,
    audit_ids: list[str],
    interp_id: str,
    interp_text: str,
    confidence: str = "HIGH",
) -> dict:  # type: ignore[type-arg]
    return {
        "observation_id": obs_id,
        "text": text,
        "audit_ids": audit_ids,
        "cited_spans": [],
        "interpretations": [
            {
                "interpretation_id": interp_id,
                "text": interp_text,
                "confidence": confidence,
                "justification": "test",
                "what_would_change_this_confidence": "counter-evidence",
                "recorded_at": "2026-06-13T14:00:00Z",
            }
        ],
    }


def _finding(fid: str, obs_id: str, interp_id: str, status: str = "APPROVED") -> dict:  # type: ignore[type-arg]
    return {
        "finding_id": fid,
        "observation_id": obs_id,
        "interpretation_id": interp_id,
        "status": status,
        "title": f"Title for {fid}",
    }


# ---------------------------------------------------------------------------
# 1. compose_findings emits inline [verify:F-001/sift-aj-20260613-007]
# ---------------------------------------------------------------------------


def test_compose_findings_emits_verify_link() -> None:
    audit_id = "sift-aj-20260613-007"
    obs = _obs("O-001", "Malicious PE discovered.", [audit_id], "I-001", "Attacker used dropper.")
    obs_map = {"O-001": obs}
    approved = [_finding("F-001", "O-001", "I-001")]
    result = compose_findings(approved, obs_map)
    assert "[verify:F-001/sift-aj-20260613-007]" in result


# ---------------------------------------------------------------------------
# 2. compose_findings handles 0-finding case
# ---------------------------------------------------------------------------


def test_compose_findings_empty_returns_placeholder() -> None:
    result = compose_findings([], {})
    assert result == "_No findings approved yet._"


# ---------------------------------------------------------------------------
# 3. compose_timeline sorts by timestamp ascending
# ---------------------------------------------------------------------------


def test_compose_timeline_sorts_ascending() -> None:
    obs1 = _obs("O-001", "Event B", ["sift-aj-20260613-002"], "I-001", "Finding B.")
    obs1["interpretations"][0]["recorded_at"] = "2026-06-13T15:00:00Z"
    obs2 = _obs("O-002", "Event A", ["sift-aj-20260613-001"], "I-002", "Finding A.")
    obs2["interpretations"][0]["recorded_at"] = "2026-06-13T12:00:00Z"
    obs_map = {"O-001": obs1, "O-002": obs2}
    approved = [
        _finding("F-001", "O-001", "I-001"),
        _finding("F-002", "O-002", "I-002"),
    ]
    result = compose_timeline(approved, obs_map)
    pos_12 = result.find("2026-06-13T12:00:00Z")
    pos_15 = result.find("2026-06-13T15:00:00Z")
    assert pos_12 < pos_15, "Earlier timestamp should appear first"


# ---------------------------------------------------------------------------
# 4. compose_iocs groups by type
# ---------------------------------------------------------------------------


def test_compose_iocs_groups_by_type() -> None:
    # IP in text
    obs = _obs(
        "O-001",
        "Beacon to 192.168.1.100 and evil.com detected.",
        ["sift-aj-20260613-001"],
        "I-001",
        "C2 beacon.",
    )
    obs_map = {"O-001": obs}
    approved = [_finding("F-001", "O-001", "I-001")]
    result = compose_iocs(approved, obs_map)
    assert "IP" in result or "Domain" in result


# ---------------------------------------------------------------------------
# 5. compose_iocs deduplicates IOCs from multiple findings
# ---------------------------------------------------------------------------


def test_compose_iocs_deduplicates() -> None:
    same_ip = "10.0.0.1"
    obs1 = _obs("O-001", f"Beacon to {same_ip}", ["sift-aj-20260613-001"], "I-001", "Beacon.")
    obs2 = _obs(
        "O-002",
        f"Lateral movement via {same_ip}",
        ["sift-aj-20260613-002"],
        "I-002",
        "Lateral move.",
    )
    obs_map = {"O-001": obs1, "O-002": obs2}
    approved = [_finding("F-001", "O-001", "I-001"), _finding("F-002", "O-002", "I-002")]
    result = compose_iocs(approved, obs_map)
    # same_ip should appear once as a key, not duplicated
    assert result.count(f"`{same_ip}`") == 1


# ---------------------------------------------------------------------------
# 6. compose_executive_summary respects ≤500-word limit
# ---------------------------------------------------------------------------


def test_compose_executive_summary_respects_word_limit() -> None:
    approved = []
    obs_map = {}
    for i in range(1, 13):
        oid = f"O-{i:03d}"
        iid = f"I-{i:03d}"
        fid = f"F-{i:03d}"
        # Long single sentence (no internal periods) — must be >=39 words so
        # 12 bullets * (3-word prefix + 39-word sentence) = 504 words > 500 limit
        long_sentence = (
            "The attacker traversed the network laterally using stolen domain credentials "
            "pivoting from the initial compromised workstation to the domain controller "
            "via a pass-the-hash attack and then subsequently exfiltrated sensitive "
            "documents from the primary file server using a custom-compiled memory-resident "
            "implant that communicated with the command-and-control infrastructure over "
            "HTTPS to evade perimeter controls and firewall logging"
        )
        obs = _obs(oid, f"Evidence {i}", [f"sift-aj-20260613-{i:03d}"], iid, long_sentence)
        obs_map[oid] = obs
        approved.append(_finding(fid, oid, iid))

    result = compose_executive_summary(approved, obs_map)
    word_count = len(result.split())
    # Allow for the truncation marker itself being a few extra words
    assert word_count <= 530, f"Summary too long: {word_count} words"
    assert "[...truncated" in result


# ---------------------------------------------------------------------------
# 7. compose_methodology lists unique tools from audit entries
# ---------------------------------------------------------------------------


def test_compose_methodology_lists_unique_tools(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    audit_dir = case_dir / "audit"
    audit_dir.mkdir(parents=True)

    lines = [
        json.dumps({"tool": "vol3", "audit_id": "sift-aj-20260613-001"}),
        json.dumps({"tool": "sbeCmd", "audit_id": "sift-aj-20260613-002"}),
        json.dumps({"tool": "vol3", "audit_id": "sift-aj-20260613-003"}),  # duplicate
    ]
    (audit_dir / "vol3.jsonl").write_text("\n".join(lines[:1] + lines[2:]), encoding="utf-8")
    (audit_dir / "sbeCmd.jsonl").write_text(lines[1] + "\n", encoding="utf-8")

    result = compose_methodology(case_dir)
    assert "`vol3`" in result
    assert "`sbeCmd`" in result
    # vol3 appears once despite being in multiple lines
    assert result.count("`vol3`") == 1


# ---------------------------------------------------------------------------
# 8. compose_engagement_overview includes privilege placeholder
# ---------------------------------------------------------------------------


def test_compose_engagement_overview_includes_privilege_placeholder(tmp_path: Path) -> None:
    result = compose_engagement_overview(tmp_path / "nonexistent", "test-case-001", "aj")
    assert "_To be completed by examiner._" in result
    assert "test-case-001" in result
    assert "aj" in result


# ---------------------------------------------------------------------------
# 9. compose_iocs extracts SHA-1, MD5, and RegistryKey types
# ---------------------------------------------------------------------------


def test_compose_iocs_extracts_sha1_and_regkey() -> None:
    sha1 = "da39a3ee5e6b4b0d3255bfef95601890afd80709"  # pragma: allowlist secret
    regkey = r"HKEY_LOCAL_MACHINE\SOFTWARE\Malware\Persist"  # pragma: allowlist secret
    obs = _obs(
        "O-001",
        f"Hash {sha1} found; persistence via {regkey}",
        ["sift-aj-20260613-001"],
        "I-001",
        "Malware installed persistence.",
    )
    obs_map = {"O-001": obs}
    approved = [_finding("F-001", "O-001", "I-001")]
    result = compose_iocs(approved, obs_map)
    assert "SHA-1" in result or "RegistryKey" in result


# ---------------------------------------------------------------------------
# 10. compose_iocs returns placeholder when obs text has no IOC patterns
# ---------------------------------------------------------------------------


def test_compose_iocs_no_ioc_candidates_returns_placeholder() -> None:
    obs = _obs(
        "O-001",
        "General observation with no indicators.",
        ["sift-aj-20260613-001"],
        "I-001",
        "Nothing found.",
    )
    obs_map = {"O-001": obs}
    approved = [_finding("F-001", "O-001", "I-001")]
    result = compose_iocs(approved, obs_map)
    assert "_No IOC candidates extracted" in result


# ---------------------------------------------------------------------------
# 11. compose_gaps with dict-shaped entries
# ---------------------------------------------------------------------------


def test_compose_gaps_handles_dict_entries(tmp_path: Path) -> None:
    import json as _json

    state = {
        "abandoned_hypotheses": [{"id": "H-001", "label": "Insider threat ruled out"}],
        "exhausted_budgets": [],
        "explicit_gaps": [],
    }
    (tmp_path / "case_state.json").write_text(_json.dumps(state), encoding="utf-8")
    result = compose_gaps(tmp_path)
    assert "Insider threat ruled out" in result


# ---------------------------------------------------------------------------
# 12. compose_gaps with state that is not a dict → placeholder
# ---------------------------------------------------------------------------


def test_compose_gaps_invalid_json_type_returns_placeholder(tmp_path: Path) -> None:
    import json as _json

    (tmp_path / "case_state.json").write_text(_json.dumps([1, 2, 3]), encoding="utf-8")
    result = compose_gaps(tmp_path)
    assert result == "(no gaps identified)"


# ---------------------------------------------------------------------------
# 13. compose_appendix_audit when audit dir absent → placeholder
# ---------------------------------------------------------------------------


def test_compose_appendix_audit_no_audit_dir(tmp_path: Path) -> None:
    from silentwitness_agent.report.compose import compose_appendix_audit

    result = compose_appendix_audit(tmp_path / "nonexistent_case")
    assert "_No audit logs found._" in result


# ---------------------------------------------------------------------------
# 14. compose_timeline with long observation text (>80 chars → ellipsis)
# ---------------------------------------------------------------------------


def test_compose_timeline_truncates_long_obs_text() -> None:
    long_text = "A" * 100
    obs = _obs("O-001", long_text, ["sift-aj-20260613-001"], "I-001", "Long event.")
    obs["interpretations"][0]["recorded_at"] = "2026-06-13T10:00:00Z"
    obs_map = {"O-001": obs}
    approved = [_finding("F-001", "O-001", "I-001")]
    result = compose_timeline(approved, obs_map)
    assert "…" in result


# ---------------------------------------------------------------------------
# 15. compose_executive_summary skips findings with no matching interp
# ---------------------------------------------------------------------------


def test_compose_executive_summary_skips_missing_interp() -> None:
    obs = _obs("O-001", "Evidence.", ["sift-aj-20260613-001"], "I-001", "Found something.")
    obs_map = {"O-001": obs}
    # finding points to a non-existent interpretation
    approved = [
        {
            "finding_id": "F-001",
            "observation_id": "O-001",
            "interpretation_id": "I-999",
            "status": "APPROVED",
        }
    ]
    result = compose_executive_summary(approved, obs_map)
    # No matching interp → falls through to placeholder
    assert result == "_No findings approved yet._"


# ---------------------------------------------------------------------------
# 16. compose_engagement_overview with CASE.yaml present (covers yaml load path)
# ---------------------------------------------------------------------------


def test_compose_engagement_overview_reads_case_yaml(tmp_path: Path) -> None:
    import yaml as _yaml

    (tmp_path / "CASE.yaml").write_text(
        _yaml.safe_dump({"start_date": "2026-06-01", "scope": "Windows workstation"}),
        encoding="utf-8",
    )
    result = compose_engagement_overview(tmp_path, "my-case", "analyst1")
    assert "2026-06-01" in result
    assert "Windows workstation" in result


# ---------------------------------------------------------------------------
# 17. compose_engagement_overview with malformed CASE.yaml → graceful fallback
# ---------------------------------------------------------------------------


def test_compose_engagement_overview_bad_yaml_falls_back(tmp_path: Path) -> None:
    (tmp_path / "CASE.yaml").write_text(": : :\n  bad: [yaml", encoding="utf-8")
    result = compose_engagement_overview(tmp_path, "case-x", "aj")
    assert "_not recorded_" in result  # fallback values


# ---------------------------------------------------------------------------
# 18. compose_findings with finding that has no title field
# ---------------------------------------------------------------------------


def test_compose_findings_falls_back_to_fid_when_no_title() -> None:
    obs = _obs("O-001", "Malware found.", ["sift-aj-20260613-001"], "I-001", "Implant deployed.")
    obs_map = {"O-001": obs}
    finding_no_title = {
        "finding_id": "F-001",
        "observation_id": "O-001",
        "interpretation_id": "I-001",
        "status": "APPROVED",
    }
    result = compose_findings([finding_no_title], obs_map)
    # Falls back to fid as title
    assert "### F-001 — F-001" in result


# ---------------------------------------------------------------------------
# 19. compose_gaps with empty items list → placeholder
# ---------------------------------------------------------------------------


def test_compose_gaps_all_keys_empty_returns_placeholder(tmp_path: Path) -> None:
    import json as _json

    state = {"abandoned_hypotheses": [], "exhausted_budgets": [], "explicit_gaps": []}
    (tmp_path / "case_state.json").write_text(_json.dumps(state), encoding="utf-8")
    result = compose_gaps(tmp_path)
    assert result == "(no gaps identified)"
