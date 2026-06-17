"""Tests for the tracked diagram assets used by judge-facing docs."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_BRAND = _REPO / "assets" / "brand"
_SITE_BRAND = _REPO / "apps" / "site" / "public" / "brand"
_EXPECTED = [
    "banner.png",
    "diagram-A-architecture.png",
    "diagram-B-firewall.png",
    "diagram-C-ingest.png",
    "diagram-D-investigation-loop.png",
    "diagram-E-recall.png",
    "diagram-F-trace.png",
    "social-card.png",
]


def test_expected_brand_png_pack_exists() -> None:
    for name in _EXPECTED:
        assert (_BRAND / name).exists(), name
        assert (_SITE_BRAND / name).exists(), name


def test_site_brand_png_pack_matches_repo_assets() -> None:
    for name in _EXPECTED:
        assert (_SITE_BRAND / name).read_bytes() == (_BRAND / name).read_bytes(), name


def test_retired_svg_diagram_pack_is_not_referenced() -> None:
    diagrams_dir = _REPO / "docs" / "diagrams"
    assert not any(diagrams_dir.glob("*.svg"))
    retired_source_suffix = "." + "mmd"
    assert not any(path.suffix == retired_source_suffix for path in diagrams_dir.glob("*"))
    assert not any(diagrams_dir.glob("*.png"))


def test_pngs_are_large_enough_to_be_real_assets() -> None:
    for name in _EXPECTED:
        size = (_BRAND / name).stat().st_size
        assert size > 100_000, f"{name} size {size} too small for generated diagram asset"


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
        "../assets/brand/diagram-B-firewall.png",
        "../assets/brand/diagram-C-ingest.png",
        "../assets/brand/diagram-D-investigation-loop.png",
        "../assets/brand/diagram-E-recall.png",
        "../assets/brand/diagram-F-trace.png",
    ):
        assert rel in text
