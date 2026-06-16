#!/usr/bin/env python3
"""README gate: verify README shape + banned-vocab invariants.

Exit 0 on pass; exit 1 with the failing rule name on stderr.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# README is capped at 400 lines to stay scannable on one Devpost screen.
_MAX_LINES = 400
# First-screen checks (demo, image, architecture asset) scope to the first 100 lines.
_HEAD_LINES = 100
_DEMO_RE = re.compile(r"youtu\.be/|youtube\.com/watch|vimeo\.com/\d+|<!--\s*DEMO_VIDEO_URL\s*-->")
_ARCHITECTURE_RE = re.compile(
    r"docs/diagrams/architecture\.svg|assets/brand/diagram-A-architecture\.png"
)
_MIT_RE = re.compile(r"\bMIT\b")
_H1_RE = re.compile(r"^# SilentWitness\b")
_BANNED = (
    "court-admissible",
    "autonomous SOC",
    "Ralph Wiggum",
    "replaces L1",
    "eliminates hallucinations",
)
# "Find Evil!" (with trailing `!`) — the literal hackathon name — is allowed anywhere.
# The marketing phrase "find evil" without `!` is banned by vocab discipline.
# Implementation: first strip the markdown link form `[Find Evil!](url)` in check()
# (line 96), then this regex catches bare "find evil" without `!`.
_FIND_EVIL_MARKETING = re.compile(r"\bfind evil(?!!)", re.IGNORECASE)


def _fail(rule: str, detail: str = "") -> int:
    msg = f"README gate FAIL: {rule}"
    if detail:
        msg += f" — {detail}"
    print(msg, file=sys.stderr)
    return 1


def check(readme_path: Path) -> int:
    try:
        # Normalize CRLF → LF so the head-scoped regex checks behave the same on
        # Windows-saved files and Unix-saved files.
        text = readme_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except OSError as exc:
        return _fail("readable", f"cannot read {readme_path}: {exc}")
    lines = text.splitlines()

    # Rule 1: H1 SilentWitness within first 5 lines (word-bounded — reject SilentWitnessXYZ)
    if not any(_H1_RE.match(line) for line in lines[:5]):
        return _fail("h1", "expected `# SilentWitness` within first 5 lines")

    # Rule 9: total line count
    if len(lines) > _MAX_LINES:
        return _fail("max_lines", f"{len(lines)} > {_MAX_LINES}")

    head = "\n".join(lines[:_HEAD_LINES])

    # Rule 2: demo video link or placeholder marker
    if not _DEMO_RE.search(head):
        return _fail(
            "demo_video",
            "no YouTube/Vimeo link or DEMO_VIDEO_URL marker in first 100 lines",
        )

    # Rule 3: image embed alt-text
    if "![" not in head:
        return _fail("image_embed", "no `![alt](path)` image embed in first 100 lines")

    # Rule 4: SIFT native install — either curl-pipe-bash one-liner OR the
    # git-clone-then-./install.sh pattern (PR #238 changed the recommended
    # path to "clone then run" so the user sees the script they're about to
    # execute; curl-pipe-bash is still accepted as an alternative).
    has_curl_bash = re.search(r"curl[^\n]*install\.sh[^\n]*\|\s*bash", text) is not None
    has_clone_run = (
        re.search(r"git clone[^\n]*silentwitness[\s\S]*?\./install\.sh", text) is not None
    )
    if not (has_curl_bash or has_clone_run):
        return _fail(
            "sift_install",
            "missing both `curl ... install.sh | bash` and `git clone ... && ./install.sh`",
        )

    # Rule 5: Docker Compose path
    if "docker compose up" not in text:
        return _fail("docker_compose", "missing `docker compose up` shell line")

    # Rule 6: tracked architecture diagram reference
    if not _ARCHITECTURE_RE.search(text):
        return _fail(
            "architecture_diagram",
            "missing README reference to a tracked architecture diagram",
        )

    # Rule 8: literal `MIT` (word-bounded — must not match `transMIT`, `commit`, etc.)
    if not _MIT_RE.search(text):
        return _fail("mit_license", "missing literal `MIT` license reference")

    # Rule 10: banned vocab list (CI grep gate)
    for phrase in _BANNED:
        if phrase.lower() in text.lower():
            return _fail("banned_vocab", f"phrase {phrase!r} present")
    # "find evil" as marketing (not the hackathon link form)
    # Strip the hackathon link `[Find Evil!](https://...)` then scan
    text_no_link = re.sub(r"\[\s*find\s*evil\s*!?\s*\]\([^)]+\)", "", text, flags=re.IGNORECASE)
    if _FIND_EVIL_MARKETING.search(text_no_link):
        return _fail(
            "find_evil_marketing",
            "`find evil` used as marketing copy outside hackathon link",
        )

    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check README.md against story-readme-polish gate.",
    )
    parser.add_argument(
        "readme",
        nargs="?",
        default="README.md",
        type=Path,
        help="Path to README.md (default: ./README.md)",
    )
    args = parser.parse_args(argv)
    return check(args.readme)


if __name__ == "__main__":
    sys.exit(main())
