"""Tests for scripts/check_submission_ready.py + scripts/swap_demo_video_url.py."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_GATE = _REPO / "scripts" / "check_submission_ready.py"
_SWAP = _REPO / "scripts" / "swap_demo_video_url.py"


def _run_gate(*extra: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_GATE), *extra],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )


def _make_minimal_fixture(tmp_path: Path) -> Path:
    """Build a minimal pass-the-gate fixture tree."""
    root = tmp_path / "repo"
    root.mkdir()
    (root / "LICENSE").write_text("MIT License\n\nCopyright (c) 2026\n")
    # README with real YouTube URL, mermaid block, no placeholder
    (root / "README.md").write_text(
        "# SilentWitness\n\n"
        "Demo: https://youtu.be/abcdefghijk\n\n"
        "```mermaid\nflowchart TB\nA --> B\n```\n"
    )
    docs = root / "docs"
    docs.mkdir()
    (docs / "architecture.md").write_text("# Architecture\n```mermaid\nflowchart\n```\n")
    (docs / "diagrams").mkdir()
    (docs / "diagrams" / "architecture.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (docs / "DEVPOST.md").write_text(
        "# SilentWitness\n## One-line pitch\n## What it does\n## Built with\npython\n"
    )
    (docs / "DATASETS.md").write_text("# Datasets\n")
    (docs / "ACCURACY_REPORT.md").write_text("# Accuracy report\n")
    (docs / "TRY_IT_OUT.md").write_text(
        "# Try SilentWitness\ncurl --proto '=https' x install.sh | bash\ndocker compose up -d\n"
    )
    logs = docs / "EXAMPLE_EXECUTION_LOGS" / "case-example-001_EXAMPLE"
    logs.mkdir(parents=True)
    (logs / "report.md").write_text("# Report\n## Gaps\n- gap\n## Appendix-Audit\n| t | r |\n")
    harness = root / "harness" / "datasets"
    harness.mkdir(parents=True)
    for name in ("nitroba", "nist-data-leakage", "nist-hacking-case"):
        (harness / f"{name}.manifest.json").write_text("{}")
    return root


class TestDeliverables:
    def test_clean_fixture_passes_all(self, tmp_path: Path) -> None:
        root = _make_minimal_fixture(tmp_path)
        r = _run_gate("--mode", "deliverables", "--root", str(root))
        assert r.returncode == 0, r.stderr

    def test_missing_datasets_md_fails(self, tmp_path: Path) -> None:
        root = _make_minimal_fixture(tmp_path)
        (root / "docs" / "DATASETS.md").unlink()
        r = _run_gate("--mode", "deliverables", "--root", str(root))
        assert r.returncode == 1
        assert "DATASETS.md" in r.stderr

    def test_missing_license_fails(self, tmp_path: Path) -> None:
        root = _make_minimal_fixture(tmp_path)
        (root / "LICENSE").write_text("Apache License\n")
        r = _run_gate("--mode", "deliverables", "--root", str(root))
        assert r.returncode == 1


class TestVideoUrl:
    def test_valid_youtu_be_passes(self) -> None:
        r = _run_gate("--mode", "video-url", "--video-url", "https://youtu.be/aaaaaaaaaaa")
        assert r.returncode == 0, r.stderr

    def test_valid_youtube_com_watch_passes(self) -> None:
        r = _run_gate(
            "--mode", "video-url", "--video-url", "https://www.youtube.com/watch?v=aaaaaaaaaaa"
        )
        assert r.returncode == 0, r.stderr

    def test_non_youtube_url_fails(self) -> None:
        r = _run_gate("--mode", "video-url", "--video-url", "https://example.com/video.mp4")
        assert r.returncode == 1


class TestPlaceholderSwap:
    def test_readme_with_placeholder_fails(self, tmp_path: Path) -> None:
        root = _make_minimal_fixture(tmp_path)
        (root / "README.md").write_text(
            "# SilentWitness\n<!-- DEMO_VIDEO_URL --> https://youtu.be/PLACEHOLDER\n"
        )
        (root / "docs" / "TRY_IT_OUT.md").write_text("# Try\n")
        r = _run_gate("--mode", "placeholder-swap", "--root", str(root))
        assert r.returncode == 1
        assert "PLACEHOLDER" in r.stderr or "placeholder" in r.stderr


class TestVocab:
    def test_vocab_carve_out_for_meta_docs(self, tmp_path: Path) -> None:
        """The vocab scanner must exclude this script + the meta-docs it lives near."""
        root = _make_minimal_fixture(tmp_path)
        # No banned vocab in any committed file
        r = _run_gate("--mode", "vocab", "--root", str(root))
        assert r.returncode == 0, r.stderr

    def test_vocab_detects_banned_in_docs(self, tmp_path: Path) -> None:
        root = _make_minimal_fixture(tmp_path)
        (root / "docs" / "BAD.md").write_text("This is court-admissible content.\n")
        r = _run_gate("--mode", "vocab", "--root", str(root))
        assert r.returncode == 1


class TestSwapDemoVideoUrl:
    def test_valid_url_swaps_both_files(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        try_md = tmp_path / "docs" / "TRY_IT_OUT.md"
        try_md.parent.mkdir()
        readme.write_text("# X\n<!-- DEMO_VIDEO_URL --> https://youtu.be/PLACEHOLDER\n")
        try_md.write_text("# Y\n<!-- DEMO_VIDEO_URL --> https://youtu.be/PLACEHOLDER\n")
        # Invoke as a library function so we can pass custom targets
        import importlib.util

        spec = importlib.util.spec_from_file_location("swap", _SWAP)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rc = mod.swap("https://youtu.be/aaaaaaaaaaa", targets=(readme, try_md))
        assert rc == 0
        assert "PLACEHOLDER" not in readme.read_text()
        assert "aaaaaaaaaaa" in readme.read_text()
        assert "aaaaaaaaaaa" in try_md.read_text()

    def test_invalid_url_refused(self, tmp_path: Path) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("swap", _SWAP)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rc = mod.swap("https://example.com/video", targets=())
        assert rc == 1

    def test_already_swapped_refuses(self, tmp_path: Path) -> None:
        readme = tmp_path / "README.md"
        readme.write_text("# X\nDemo: https://youtu.be/aaaaaaaaaaa\n")
        import importlib.util

        spec = importlib.util.spec_from_file_location("swap", _SWAP)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        rc = mod.swap("https://youtu.be/bbbbbbbbbbb", targets=(readme,))
        assert rc == 1


class TestCommittedRepoState:
    def test_committed_devpost_md_under_400_lines(self) -> None:
        text = (_REPO / "docs" / "DEVPOST.md").read_text()
        assert len(text.splitlines()) <= 400

    def test_committed_devpost_has_required_h2s(self) -> None:
        text = (_REPO / "docs" / "DEVPOST.md").read_text()
        h2_count = sum(1 for ln in text.splitlines() if ln.startswith("## "))
        assert h2_count >= 9, f"only {h2_count} H2s; spec wants >=9"

    def test_committed_checklist_has_eight_checkboxes(self) -> None:
        text = (_REPO / "docs" / "devpost-submission-checklist.md").read_text()
        boxes = sum(1 for ln in text.splitlines() if ln.startswith("- [ ]"))
        assert boxes >= 8

    def test_committed_checklist_mentions_ci_green(self) -> None:
        text = (_REPO / "docs" / "devpost-submission-checklist.md").read_text()
        assert "CI green on `main`" in text or "CI green on main" in text


def test_swap_smoke_from_cli(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    try_md = tmp_path / "docs" / "TRY_IT_OUT.md"
    try_md.parent.mkdir()
    readme.write_text("<!-- DEMO_VIDEO_URL --> https://youtu.be/PLACEHOLDER\n")
    try_md.write_text("<!-- DEMO_VIDEO_URL --> https://youtu.be/PLACEHOLDER\n")
    # Make a fake _REPO root so the script targets these files
    fake_root = tmp_path
    repo_layout = tmp_path / "scripts"
    repo_layout.mkdir()
    shutil.copy(_SWAP, repo_layout / "swap_demo_video_url.py")
    r = subprocess.run(
        [
            sys.executable,
            str(repo_layout / "swap_demo_video_url.py"),
            "https://youtu.be/zzzzzzzzzzz",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=fake_root,
    )
    assert r.returncode == 0, r.stderr
    assert "zzzzzzzzzzz" in readme.read_text()
