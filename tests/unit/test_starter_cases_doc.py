"""Tests for docs/STARTER_CASES.md + scripts/check_starter_cases_doc.py."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_DOC = _REPO / "docs" / "STARTER_CASES.md"
_GATE = _REPO / "scripts" / "check_starter_cases_doc.py"
_MANIFEST_DIR = _REPO / "harness" / "datasets"

_NITROBA_SHA = (
    "2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb"  # pragma: allowlist secret
)


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


def test_doc_under_400_lines() -> None:
    assert len(_DOC.read_text().splitlines()) <= 400


def test_doc_has_h1() -> None:
    assert _DOC.read_text().startswith("# Starter cases")


@pytest.mark.parametrize(
    "section",
    [
        "## At a glance",
        "## Reproducibility recipe",
        "## Nitroba University Harassment",
        "## NIST CFReDS Data Leakage Case",
        "## NIST CFReDS Hacking Case",
        "## case-trapdoor",
        "## Gitignored evidence binaries",
        "## Verification",
        "## Sources + licenses",
    ],
)
def test_doc_has_required_section(section: str) -> None:
    assert section in _DOC.read_text(), f"missing {section!r}"


def test_doc_has_at_least_nine_h2_sections() -> None:
    """BDD: >=9 ## sections per story acceptance criteria."""
    h2_count = sum(1 for ln in _DOC.read_text().splitlines() if ln.startswith("## "))
    assert h2_count >= 9, f"only {h2_count} H2 sections; story requires >=9"


def test_nitroba_sha256_matches_manifest() -> None:
    manifest = json.loads((_MANIFEST_DIR / "nitroba.manifest.json").read_text())
    assert manifest["sha256"] in _DOC.read_text()


def test_memorization_risk_sentence_verbatim_in_hacking_section() -> None:
    text = _DOC.read_text()
    hack_idx = text.index("## NIST CFReDS Hacking Case")
    next_idx = text.find("\n## ", hack_idx + 1)
    section = text[hack_idx : next_idx if next_idx > 0 else len(text)]
    assert "Greg Schardt / Mr. Evil canonical answers (MAC, IP, hostname, email)" in section
    assert "appear in hundreds of indexed writeups" in section


def test_reproducibility_recipe_has_verify_step() -> None:
    """Tighter assertion: both verify_manifest.py AND --strict must appear (AND, not OR)."""
    text = _DOC.read_text()
    assert "verify_manifest.py" in text
    assert "--strict" in text
    assert "uv run python -m harness" in text


def test_results_links_for_every_active_case() -> None:
    text = _DOC.read_text()
    for slug in ("nitroba", "nist-data-leakage", "nist-hacking-case"):
        assert f"harness/results/{slug}/" in text


def test_justfile_carries_harness_recipe() -> None:
    """Doc references `just harness DATASET=...`; verify the recipe exists."""
    justfile = (_REPO / "justfile").read_text()
    assert "harness DATASET" in justfile, "justfile missing `harness DATASET:` recipe"
    assert "verify_manifest.py" in justfile
    assert "harness.scorer" in justfile


def test_section_order_matches_spec() -> None:
    text = _DOC.read_text()
    order = [
        "## At a glance",
        "## Reproducibility recipe",
        "## Nitroba University Harassment",
        "## NIST CFReDS Data Leakage Case",
        "## NIST CFReDS Hacking Case",
        "## case-trapdoor",
        "## Gitignored evidence binaries",
        "## Verification",
        "## Sources + licenses",
    ]
    positions = [text.index(h) for h in order]
    assert positions == sorted(positions)


def _ok_doc() -> str:
    """Minimal happy-path doc that satisfies every gate rule."""
    return (
        "# Starter cases — test\n"
        "## At a glance\n## Reproducibility recipe\n"
        "uv run python -m harness.baseline\n"
        "verify_manifest.py --strict\n"
        "harness/results/nitroba/ harness/results/nist-data-leakage/ "
        "harness/results/nist-hacking-case/\n"
        "## Nitroba University Harassment\n"
        f"{_NITROBA_SHA}\n"
        "## NIST CFReDS Data Leakage Case\n"
        "## NIST CFReDS Hacking Case\n"
        "Greg Schardt / Mr. Evil canonical answers (MAC, IP, hostname, email) "
        "appear in hundreds of indexed writeups.\n"
        "## case-trapdoor\n"
        "## Gitignored evidence binaries\n"
        "## Verification\n"
        "## Sources + licenses\n"
    )


_MUTATIONS: list[tuple[Callable[[str], str], str]] = [
    # (mutation_fn, expected_rule_slug_in_stderr)
    (lambda t: t.replace("# Starter cases", "# Wrong"), "h1"),
    (lambda t: t.replace("## At a glance", "## Glance"), "required_section"),
    (lambda t: t.replace(_NITROBA_SHA, "0" * 64), "nitroba_sha_xref"),
    (lambda t: t.replace("verify_manifest.py --strict", "REMOVED"), "repro_recipe"),
    (lambda t: t.replace("uv run python -m harness.baseline", "x"), "repro_recipe"),
    (lambda t: t.replace("harness/results/nitroba/", "x/"), "results_link"),
    (lambda t: t + "court-admissible content here\n", "banned_vocab"),
    (
        lambda t: t.replace("hundreds of indexed writeups", "REMOVED"),
        "memorization_risk_disclosure",
    ),
    (lambda t: "\n".join(["padding"] * 401) + "\n" + t, "max_lines"),
    (
        # swap two sections to break ordering
        lambda t: (
            t.replace("## At a glance", "TMP1")
            .replace("## Reproducibility recipe", "## At a glance")
            .replace("TMP1", "## Reproducibility recipe")
        ),
        "section_order",
    ),
]


@pytest.mark.parametrize(
    "mutation,expected_rule",
    _MUTATIONS,
    ids=[m[1] for m in _MUTATIONS],
)
def test_gate_rule_fires_on_mutation(
    tmp_path: Path,
    mutation: Callable[[str], str],
    expected_rule: str,
) -> None:
    """Every gate rule has a corresponding failure-mode test."""
    bad = tmp_path / "STARTER_CASES.md"
    bad.write_text(mutation(_ok_doc()))
    # Inject the real manifest dir so the gate can still cross-reference
    r = _run_gate("--doc", str(bad), "--manifest-dir", str(_MANIFEST_DIR))
    assert r.returncode == 1, r.stderr
    assert expected_rule in r.stderr, (
        f"expected rule slug {expected_rule!r} in stderr; got: {r.stderr}"
    )


class TestManifestIoFailures:
    """Manifest IO errors must route through _fail() with a rule slug, not crash."""

    def test_missing_manifest_dir_yields_manifest_missing(self, tmp_path: Path) -> None:
        doc = tmp_path / "STARTER_CASES.md"
        doc.write_text(_ok_doc())
        fake_manifest_dir = tmp_path / "no-manifests"
        r = _run_gate("--doc", str(doc), "--manifest-dir", str(fake_manifest_dir))
        assert r.returncode == 1
        assert "manifest_missing" in r.stderr

    def test_corrupt_manifest_yields_manifest_corrupt(self, tmp_path: Path) -> None:
        doc = tmp_path / "STARTER_CASES.md"
        doc.write_text(_ok_doc())
        bad_manifest_dir = tmp_path / "manifests"
        bad_manifest_dir.mkdir()
        (bad_manifest_dir / "nitroba.manifest.json").write_text("{not-json")
        r = _run_gate("--doc", str(doc), "--manifest-dir", str(bad_manifest_dir))
        assert r.returncode == 1
        assert "manifest_corrupt" in r.stderr

    def test_doc_missing_yields_doc_exists(self, tmp_path: Path) -> None:
        r = _run_gate("--doc", str(tmp_path / "DOES_NOT_EXIST.md"))
        assert r.returncode == 1
        assert "doc_exists" in r.stderr
