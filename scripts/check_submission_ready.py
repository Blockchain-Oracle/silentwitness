#!/usr/bin/env python3
"""Pre-submission gate: confirm all 8 deliverables + license + vocab + URL.

CLI: ``--mode {all,deliverables,vocab,license,placeholder-swap,video-url}``
(default ``all``). Each rule prints ✓/✗ to stderr; exit 0 if all pass.

Carve-out: meta-docs that document the banned-vocab list (this script, the
checklist, and the per-doc gate scripts) are excluded from the vocab scan.
The authoritative carve-out lists are ``_VOCAB_EXCLUDE_FILES`` and
``_VOCAB_EXCLUDE_PREFIXES`` below.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_BANNED = (
    "court-admissible",
    "autonomous SOC",
    "Ralph Wiggum",
    "replaces L1",
    "eliminates hallucinations",
)
_BANNED_RE = re.compile(r"(?i)(" + "|".join(re.escape(b) for b in _BANNED) + r")")
_VOCAB_EXCLUDE_FILES = {
    "scripts/check_submission_ready.py",
    "scripts/check_readme_gate.py",
    "scripts/check_datasets_doc.py",
    "scripts/check_accuracy_report_vocab.py",
    "scripts/check_try_it_out.py",
    "scripts/_notices_catalog.py",
    "docs/devpost-submission-checklist.md",
    "docs/architecture.md",
}
# Directories that document the banned vocab as part of their content are
# excluded from the scan; the gate covers committed src/, scripts/, and the
# judge-facing docs/*.md leaves.
_VOCAB_EXCLUDE_PREFIXES = (
    "archive/",
    "docs/EXAMPLE_EXECUTION_LOGS/",
)
_YT_URL_PATTERN = (
    r"https://(?:youtu\.be/[A-Za-z0-9_-]{11}"
    r"|(?:www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]{11})"
)
# Anchored at both ends — used by --video-url for strict validation. The 11-char
# ID upper bound (no trailing junk) matches swap_demo_video_url._YT_PATTERNS so
# the two scripts agree on what counts as a valid YouTube URL.
_YT_RE_STRICT = re.compile(rf"^{_YT_URL_PATTERN}$")
# Search variant: used to detect a YouTube URL anywhere in README.md prose. The
# trailing word-boundary stops the ID match from accepting `abcdefghijkEXTRA`.
_YT_RE_SEARCH = re.compile(rf"{_YT_URL_PATTERN}(?=\b|$)")


class Check:
    def __init__(self, name: str) -> None:
        self.name = name
        self.passed = True
        self.detail = ""

    def fail(self, detail: str) -> None:
        self.passed = False
        self.detail = detail

    def emit(self) -> None:
        mark = "✓" if self.passed else "✗"
        line = f"  {mark} {self.name}"
        if self.detail:
            line += f" — {self.detail}"
        print(line, file=sys.stderr)


def _check_license(root: Path) -> Check:
    chk = Check("LICENSE is MIT")
    lic = root / "LICENSE"
    if not lic.exists():
        chk.fail("LICENSE file missing")
    elif not lic.read_text(encoding="utf-8").lstrip().startswith("MIT License"):
        chk.fail("LICENSE does not start with `MIT License`")
    return chk


def _check_deliverables(root: Path) -> list[Check]:
    checks: list[Check] = []

    # Deliverable 1: GitHub repo + LICENSE
    checks.append(_check_license(root))

    # Deliverable 2: Demo video URL in README (not placeholder)
    readme = root / "README.md"
    chk = Check("Deliverable 2: Demo video URL present + swapped")
    if not readme.exists():
        chk.fail("README.md missing")
    else:
        full = readme.read_text(encoding="utf-8")
        head = "\n".join(full.splitlines()[:100])
        if "youtu.be/PLACEHOLDER" in full or "<!-- DEMO_VIDEO_URL -->" in full:
            chk.fail("README still contains demo-video placeholder marker")
        elif not _YT_RE_SEARCH.search(head):
            chk.fail("no YouTube URL in first 100 lines")
    checks.append(chk)

    # Deliverable 3: Architecture diagram asset + README reference
    chk = Check("Deliverable 3: Architecture diagram asset + README reference")
    arch_md = root / "docs" / "architecture.md"
    arch_svg = root / "docs" / "diagrams" / "architecture.svg"
    if not arch_md.exists():
        chk.fail("docs/architecture.md missing")
    elif not arch_svg.exists():
        chk.fail("docs/diagrams/architecture.svg missing")
    elif "docs/diagrams/architecture.svg" not in readme.read_text(encoding="utf-8"):
        chk.fail("README does not reference docs/diagrams/architecture.svg")
    checks.append(chk)

    # Deliverable 4: Devpost write-up
    chk = Check("Deliverable 4: docs/DEVPOST.md present + ≤400 lines")
    devpost = root / "docs" / "DEVPOST.md"
    if not devpost.exists():
        chk.fail("docs/DEVPOST.md missing")
    else:
        text = devpost.read_text(encoding="utf-8")
        if len(text.splitlines()) > 400:
            chk.fail(f"{len(text.splitlines())} > 400 lines")
        elif "## Built with" not in text:
            chk.fail("missing `## Built with` heading")
    checks.append(chk)

    # Deliverable 5: Dataset documentation
    chk = Check("Deliverable 5: docs/DATASETS.md + >=3 manifests")
    if not (root / "docs" / "DATASETS.md").exists():
        chk.fail("docs/DATASETS.md missing")
    else:
        manifests = list((root / "harness" / "datasets").glob("*.manifest.json"))
        if len(manifests) < 3:
            chk.fail(f"only {len(manifests)} manifests; require >=3")
    checks.append(chk)

    # Deliverable 6: Accuracy report
    chk = Check("Deliverable 6: docs/ACCURACY_REPORT.md present")
    if not (root / "docs" / "ACCURACY_REPORT.md").exists():
        chk.fail("docs/ACCURACY_REPORT.md missing")
    checks.append(chk)

    # Deliverable 7: Try-It-Out
    chk = Check("Deliverable 7: docs/TRY_IT_OUT.md present + curl + docker")
    try_doc = root / "docs" / "TRY_IT_OUT.md"
    if not try_doc.exists():
        chk.fail("docs/TRY_IT_OUT.md missing")
    else:
        text = try_doc.read_text(encoding="utf-8")
        if "curl --proto" not in text:
            chk.fail("missing `curl --proto` install one-liner")
        elif "docker compose up" not in text:
            chk.fail("missing `docker compose up`")
    checks.append(chk)

    # Deliverable 8: Agent execution logs
    chk = Check("Deliverable 8: docs/EXAMPLE_EXECUTION_LOGS/")
    case_dir = root / "docs" / "EXAMPLE_EXECUTION_LOGS" / "case-example-001_EXAMPLE"
    if not case_dir.exists():
        chk.fail("case-example-001_EXAMPLE/ missing")
    else:
        report = case_dir / "report.md"
        if not report.exists():
            chk.fail("report.md missing")
        else:
            text = report.read_text(encoding="utf-8")
            if "## Gaps" not in text or "## Appendix-Audit" not in text:
                chk.fail("report.md missing ## Gaps or ## Appendix-Audit")
    checks.append(chk)

    return checks


def _check_vocab(root: Path) -> Check:
    chk = Check("banned vocab absent from committed src/docs")
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if not (rel.startswith("src/") or rel.startswith("docs/") or rel.startswith("scripts/")):
            continue
        if rel in _VOCAB_EXCLUDE_FILES:
            continue
        if any(rel.startswith(p) for p in _VOCAB_EXCLUDE_PREFIXES):
            continue
        if path.suffix not in (".py", ".md", ".sh", ".yaml", ".yml", ".toml"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"WARN: vocab-scan failed to read {rel}: {exc}", file=sys.stderr)
            hits.append(rel)
            continue
        if _BANNED_RE.search(text):
            hits.append(rel)
    if hits:
        chk.fail(f"{len(hits)} file(s) hit: {hits[:3]}{'...' if len(hits) > 3 else ''}")
    return chk


def _check_placeholder_swap(root: Path) -> Check:
    chk = Check("README + TRY_IT_OUT: demo-video placeholder swapped")
    offenders: list[str] = []
    for target in (root / "README.md", root / "docs" / "TRY_IT_OUT.md"):
        if not target.exists():
            chk.fail(f"{target.relative_to(root)} missing")
            return chk
        text = target.read_text(encoding="utf-8")
        # Each marker is checked independently — a half-swap (one marker remains)
        # must still fail the gate, otherwise stale placeholders ship to judges.
        if "youtu.be/PLACEHOLDER" in text or "<!-- DEMO_VIDEO_URL -->" in text:
            offenders.append(target.relative_to(root).as_posix())
    if offenders:
        chk.fail(f"placeholder remains in: {offenders}")
    return chk


def _check_video_url(url: str) -> Check:
    chk = Check(f"Video URL well-formed: {url}")
    if not _YT_RE_STRICT.fullmatch(url):
        chk.fail("not a recognized youtu.be/ or youtube.com/watch URL")
    return chk


def check(
    mode: str = "all",
    *,
    video_url: str | None = None,
    root: Path = _REPO,
) -> int:
    checks: list[Check] = []
    if mode in ("all", "license"):
        checks.append(_check_license(root))
    if mode in ("all", "deliverables"):
        checks.extend(_check_deliverables(root))
    if mode in ("all", "vocab"):
        checks.append(_check_vocab(root))
    if mode in ("all", "placeholder-swap"):
        checks.append(_check_placeholder_swap(root))
    if mode == "video-url":
        if video_url is None:
            print("ERROR: --video-url requires <url> arg", file=sys.stderr)
            return 1
        checks.append(_check_video_url(video_url))
    for c in checks:
        c.emit()
    return 0 if all(c.passed for c in checks) else 1


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Pre-submission gate.")
    parser.add_argument(
        "--mode",
        choices=("all", "deliverables", "vocab", "license", "placeholder-swap", "video-url"),
        default="all",
    )
    parser.add_argument("--video-url", default=None)
    parser.add_argument("--root", type=Path, default=_REPO)
    args = parser.parse_args(argv)
    return check(args.mode, video_url=args.video_url, root=args.root)


if __name__ == "__main__":
    sys.exit(main())
