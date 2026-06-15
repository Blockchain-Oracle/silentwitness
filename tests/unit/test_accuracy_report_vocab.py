"""Gate tests for docs/ACCURACY_REPORT.md (validates substance, not a frozen template).

The gate (scripts/check_accuracy_report_vocab.py) enforces: no banned marketing vocab, no
verbatim organizer quotes, the rubric-required substance (recall, hallucination controls,
evidence integrity, known issues/limitations, self-correction), no placeholders, and a
readable length. These tests run the real gate as a subprocess (no mocks).
"""

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
        [sys.executable, str(_GATE), *extra], capture_output=True, text=True, check=False
    )


# --- the committed doc ------------------------------------------------------


def test_committed_doc_passes_gate() -> None:
    r = _run_gate()
    assert r.returncode == 0, r.stderr


def test_doc_under_500_lines() -> None:
    assert len(_DOC.read_text().splitlines()) <= 500


def test_committed_doc_has_required_substance() -> None:
    lower = _DOC.read_text().lower()
    assert "recall" in lower
    assert "evidence integrity" in lower
    assert "self-correction" in lower or "critic" in lower
    assert any(s in lower for s in ("citation gate", "entity gate", "hallucination"))


def test_no_banned_vocab() -> None:
    lower = _DOC.read_text().lower()
    for phrase in ("court-admissible", "autonomous soc", "eliminates hallucinations"):
        assert phrase not in lower, f"banned phrase {phrase!r} present"


# --- the gate fires on each rule (mutate a known-good doc) ------------------


def _ok_doc() -> str:
    return (
        "# Accuracy Report\n\n"
        "## 1. Method\nHow findings were measured.\n\n"
        "## 2. Recall\nThe honest progression of results.\n\n"
        "## 3. Hallucination controls\nThe citation gate and entity gate catch fabrication.\n\n"
        "## 4. Self-correction\nThe live critic challenged findings.\n\n"
        "## 5. Evidence integrity\nRead-only evidence; no write surface.\n\n"
        "## 6. Known issues\nFalse negatives and limitations we are not hiding.\n"
    )


_MUTATIONS: list[tuple[Callable[[str], str], str]] = [
    (lambda t: t + "\ncourt-admissible\n", "banned"),
    (lambda t: t + "\nClaude doesn't get defensive when you call it out\n", "verbatim_quote"),
    (lambda t: t + "\nTBD\n", "placeholder"),
    (
        lambda t: t.replace("## 2. Recall\nThe honest progression of results.", "## 2. x\ny"),
        "section_missing",
    ),
    (
        lambda t: t.replace(
            "## 5. Evidence integrity\nRead-only evidence; no write surface.", "## 5. x\ny"
        ),
        "section_missing",
    ),
    (lambda t: "\n".join(["pad"] * 501) + t, "too_long"),
]


def test_ok_doc_self_passes_gate(tmp_path: Path) -> None:
    good = tmp_path / "ACCURACY_REPORT.md"
    good.write_text(_ok_doc())
    r = _run_gate("--doc", str(good))
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("mutation,rule", _MUTATIONS, ids=[m[1] for m in _MUTATIONS])
def test_gate_rule_fires_on_mutation(
    tmp_path: Path, mutation: Callable[[str], str], rule: str
) -> None:
    bad = tmp_path / "ACCURACY_REPORT.md"
    bad.write_text(mutation(_ok_doc()))
    r = _run_gate("--doc", str(bad))
    assert r.returncode == 1, r.stderr
    assert rule in r.stderr


def test_doc_missing_exits_1(tmp_path: Path) -> None:
    r = _run_gate("--doc", str(tmp_path / "DOES_NOT_EXIST.md"))
    assert r.returncode == 1
