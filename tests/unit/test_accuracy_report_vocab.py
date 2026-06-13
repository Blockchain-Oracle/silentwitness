"""Tests for docs/ACCURACY_REPORT.md + scripts/check_accuracy_report_vocab.py."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_DOC = _REPO / "docs" / "ACCURACY_REPORT.md"
_GATE = _REPO / "scripts" / "check_accuracy_report_vocab.py"


def _run_gate(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_GATE), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def test_committed_doc_passes_gate() -> None:
    r = _run_gate()
    assert r.returncode == 0, r.stderr


def test_doc_under_500_lines() -> None:
    assert len(_DOC.read_text().splitlines()) <= 500


def test_doc_has_sixteen_h2() -> None:
    h2s = [ln for ln in _DOC.read_text().splitlines() if ln.startswith("## ")]
    assert len(h2s) >= 16


def test_first_h2_is_status() -> None:
    h2s = [ln for ln in _DOC.read_text().splitlines() if ln.startswith("## ")]
    assert h2s[0] == "## Status + scope"


def test_last_h2_is_glossary() -> None:
    text = _DOC.read_text()
    assert "## Appendix B — Glossary" in text


def test_no_rob_lee_verbatim_quotes() -> None:
    text = _DOC.read_text()
    assert "Claude doesn't get defensive when you call it out" not in text
    assert "Protocol SIFT works. It also hallucinates more than we'd like" not in text


def test_no_banned_vocab() -> None:
    text = _DOC.read_text().lower()
    for phrase in (
        "court-admissible",
        "autonomous soc",
        "ralph wiggum",
        "replaces l1",
        "eliminates hallucinations",
    ):
        assert phrase not in text, f"banned phrase {phrase!r} present"


def test_tldr_has_three_datasets_no_tbd() -> None:
    text = _DOC.read_text()
    tldr = text[text.index("## TL;DR") : text.find("\n## ", text.index("## TL;DR") + 1)]
    for ds in ("Nitroba", "Data Leakage", "Hacking Case"):
        assert ds in tldr
    assert "TBD" not in tldr


def test_residuals_caught_has_three_audit_ids() -> None:
    import re

    text = _DOC.read_text()
    idx = text.index("## Residual hallucinations we caught")
    section = text[idx : text.find("\n## ", idx + 1)]
    matches = re.findall(r"sift-[a-z0-9]+-\d{8}-\d{3}", section)
    assert len(matches) >= 3


def test_residuals_uncaught_has_two_bullets() -> None:
    text = _DOC.read_text()
    idx = text.index("## Residual hallucinations we did NOT catch")
    section = text[idx : text.find("\n## ", idx + 1)]
    bullets = sum(1 for ln in section.splitlines() if ln.strip().startswith("- "))
    assert bullets >= 2


def _ok_doc() -> str:
    """Minimal-shape happy doc that satisfies every gate rule."""
    h2s = [
        "## Status + scope",
        "## TL;DR",
        "## Methodology",
        "## Baseline establishment",
        "## Datasets",
        "## Per-dataset results",
        "## Known false positives",
        "## Known misses",
        "## Residual hallucinations we caught",
        "## Residual hallucinations we did NOT catch",
        "## Sanitizer test corpus results",
        "## Threat model summary",
        "## Limitations + future work",
        "## Reproducibility",
        "## Appendix A — Audit-trail samples",
        "## Appendix B — Glossary",
    ]
    body = "\n".join(h2s)
    # Inject TL;DR datasets + residuals data
    body = body.replace(
        "## TL;DR\n",
        "## TL;DR\nNitroba 100% Data Leakage 86% Hacking Case 100%\n",
    )
    body = body.replace(
        "## Residual hallucinations we caught\n",
        "## Residual hallucinations we caught\n"
        "audit_id sift-harness-20260612-001\n"
        "audit_id sift-harness-20260612-002\n"
        "audit_id sift-harness-20260612-003\n",
    )
    body = body.replace(
        "## Residual hallucinations we did NOT catch\n",
        "## Residual hallucinations we did NOT catch\n- bullet one\n- bullet two\n",
    )
    return f"# Accuracy report\n{body}\n"


_MUTATIONS: list[tuple[Callable[[str], str], str]] = [
    (lambda t: t.replace("## Status + scope", "## Wrong"), "first_h2"),
    (lambda t: t + "\ncourt-admissible\n", "no_banned"),
    (lambda t: t + "\nClaude doesn't get defensive when you call it out\n", "no_verbatim_quote"),
    (
        lambda t: t + "\nProtocol SIFT works. It also hallucinates more than we'd like\n",
        "no_verbatim_quote",
    ),
    (lambda t: t.replace("Nitroba", "DatasetX"), "tldr_table"),
    (lambda t: t.replace("sift-harness-20260612-001", "no-match"), "residuals_caught"),
    (lambda t: t.replace("- bullet one", ""), "residuals_uncaught"),
    (lambda t: "\n".join(["pad"] * 501) + t, "max_lines"),
]


@pytest.mark.parametrize(
    "mutation,rule",
    _MUTATIONS,
    ids=[m[1] for m in _MUTATIONS],
)
def test_gate_rule_fires_on_mutation(
    tmp_path: Path,
    mutation: Callable[[str], str],
    rule: str,
) -> None:
    bad = tmp_path / "ACCURACY_REPORT.md"
    bad.write_text(mutation(_ok_doc()))
    r = _run_gate("--doc", str(bad))
    assert r.returncode == 1, r.stderr
    assert rule in r.stderr


def test_doc_missing_exits_1(tmp_path: Path) -> None:
    r = _run_gate("--doc", str(tmp_path / "DOES_NOT_EXIST.md"))
    assert r.returncode == 1
    assert "doc_exists" in r.stderr
