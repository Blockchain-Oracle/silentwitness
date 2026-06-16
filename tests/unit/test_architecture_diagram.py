"""Tests for the tracked diagram assets used by judge-facing docs."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_DIAGRAMS = _REPO / "docs" / "diagrams"
_EXPECTED = [
    "architecture.svg",
    "hypothesis-state.svg",
    "investigation-flow.svg",
    "approval-flow.svg",
    "critic-flow.svg",
    "citation-rejection.svg",
]


def test_expected_svg_pack_exists() -> None:
    names = sorted(p.name for p in _DIAGRAMS.glob("*.svg"))
    assert names == sorted(_EXPECTED)


def test_no_legacy_diagram_source_or_png_fallback_remains() -> None:
    assert not (_DIAGRAMS / "architecture.mmd").exists()
    assert not (_DIAGRAMS / "architecture.png").exists()


def test_svgs_are_utf8_and_have_titles() -> None:
    for name in _EXPECTED:
        text = (_DIAGRAMS / name).read_text(encoding="utf-8")
        assert text.startswith("<svg")
        assert "<title" in text
        assert "<desc" in text


def test_svgs_stay_small_enough_for_repo_docs() -> None:
    for name in _EXPECTED:
        size = (_DIAGRAMS / name).stat().st_size
        assert 512 < size <= 256_000, f"{name} size {size} outside [512B, 256KiB]"


def test_readme_references_architecture_png() -> None:
    text = (_REPO / "README.md").read_text(encoding="utf-8")
    assert "assets/brand/diagram-A-architecture.png" in text


def test_setup_guide_references_architecture_png() -> None:
    text = (_REPO / "docs" / "SETUP_GUIDE.md").read_text(encoding="utf-8")
    assert "../assets/brand/diagram-A-architecture.png" in text


def test_architecture_doc_references_public_diagram_pack() -> None:
    text = (_REPO / "docs" / "architecture.md").read_text(encoding="utf-8")
    for rel in (
        "../assets/brand/diagram-A-architecture.png",
        "diagrams/hypothesis-state.svg",
        "diagrams/investigation-flow.svg",
        "diagrams/approval-flow.svg",
        "diagrams/critic-flow.svg",
        "diagrams/citation-rejection.svg",
    ):
        assert rel in text
