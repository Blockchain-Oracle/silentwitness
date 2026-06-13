"""Tests for docs/DATASETS.md + scripts/check_datasets_doc.py (story-dataset-doc)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_DOC = _REPO / "docs" / "DATASETS.md"
_GATE = _REPO / "scripts" / "check_datasets_doc.py"
_MANIFEST_DIR = _REPO / "harness" / "datasets"


def _run_gate(doc_override: Path | None = None) -> subprocess.CompletedProcess[str]:
    args = [sys.executable, str(_GATE)]
    env = None
    if doc_override is not None:
        # Temporarily symlink: this fn only matters for negative tests we write below
        # via direct invocation.
        pass
    return subprocess.run(args, capture_output=True, text=True, check=False, env=env)


def test_committed_doc_passes_gate() -> None:
    r = _run_gate()
    assert r.returncode == 0, r.stderr


def test_doc_under_400_lines() -> None:
    assert len(_DOC.read_text().splitlines()) <= 400


def test_doc_has_h1() -> None:
    assert _DOC.read_text().startswith("# Datasets")


@pytest.mark.parametrize(
    "section",
    [
        "## At a glance",
        "## Reproducibility recipe",
        "## Nitroba University Harassment",
        "## NIST CFReDS Data Leakage Case",
        "## NIST CFReDS Hacking Case",
        "## case-trapdoor",
    ],
)
def test_doc_has_required_section(section: str) -> None:
    assert section in _DOC.read_text(), f"missing {section!r}"


def test_nitroba_sha256_matches_manifest() -> None:
    manifest = json.loads((_MANIFEST_DIR / "nitroba.manifest.json").read_text())
    assert manifest["sha256"] in _DOC.read_text()


def test_memorization_risk_paragraph_verbatim_in_hacking_section() -> None:
    text = _DOC.read_text()
    hack_idx = text.index("## NIST CFReDS Hacking Case")
    next_idx = text.find("\n## ", hack_idx + 1)
    section = text[hack_idx : next_idx if next_idx > 0 else len(text)]
    assert "Greg Schardt / Mr. Evil canonical answers (MAC, IP, hostname, email)" in section
    assert "appear in hundreds of indexed writeups" in section


def test_reproducibility_recipe_has_verify_step() -> None:
    text = _DOC.read_text()
    assert "verify_manifest.py" in text
    assert "--strict" in text or "uv run python" in text


def test_results_links_for_every_active_dataset() -> None:
    text = _DOC.read_text()
    for slug in ("nitroba", "nist-data-leakage", "nist-hacking-case"):
        assert f"harness/results/{slug}/" in text


def test_section_order_matches_spec() -> None:
    """Sections must appear in story-spec order, not arbitrary order."""
    text = _DOC.read_text()
    order = [
        "## At a glance",
        "## Reproducibility recipe",
        "## Nitroba University Harassment",
        "## NIST CFReDS Data Leakage Case",
        "## NIST CFReDS Hacking Case",
        "## case-trapdoor",
    ]
    positions = [text.index(h) for h in order]
    assert positions == sorted(positions)


class TestGateFailureModes:
    """Direct-call tests of the gate's negative paths via stub files."""

    def test_missing_h1_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Simulate by patching _DOC
        bad = tmp_path / "DATASETS.md"
        bad.write_text("Not a heading\n## At a glance\n")
        import importlib.util

        spec = importlib.util.spec_from_file_location("gate", _GATE)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        monkeypatch.setattr(mod, "_DOC", bad)
        assert mod.check() == 1

    def test_missing_memo_risk_fails(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # H1 + all sections, but no memorization-risk paragraph
        bad_text = (
            "# Datasets — test\n## At a glance\n## Reproducibility recipe\n"
            "verify_manifest.py --strict\nharness/results/nitroba/\n"
            "harness/results/nist-data-leakage/\nharness/results/nist-hacking-case/\n"
            "## Nitroba University Harassment\n"
            "2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb\n"
            "## NIST CFReDS Data Leakage Case\n"
            "## NIST CFReDS Hacking Case\n"
            "## case-trapdoor\n"
        )
        bad = tmp_path / "DATASETS.md"
        bad.write_text(bad_text)
        import importlib.util

        spec = importlib.util.spec_from_file_location("gate", _GATE)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        monkeypatch.setattr(mod, "_DOC", bad)
        rc = mod.check()
        assert rc == 1
