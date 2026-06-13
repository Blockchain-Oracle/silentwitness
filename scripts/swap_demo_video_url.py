#!/usr/bin/env python3
"""Swap the demo-video placeholder for the real YouTube URL at submission time.

Validates a YouTube Unlisted URL form, then atomic-renames in-place across
README.md + docs/TRY_IT_OUT.md. Refuses if either marker is missing
(probably already swapped — refuse-by-default rather than overwrite).
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TARGETS = (_REPO / "README.md", _REPO / "docs" / "TRY_IT_OUT.md")
_PLACEHOLDER_MARKER = "<!-- DEMO_VIDEO_URL -->"
_PLACEHOLDER_URL = "https://youtu.be/PLACEHOLDER"
_YT_PATTERNS = (
    re.compile(r"^https://youtu\.be/[A-Za-z0-9_-]{11}$"),
    re.compile(r"^https://(www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]{11}(&.*)?$"),
)


def _is_valid_youtube_url(url: str) -> bool:
    return any(p.match(url) for p in _YT_PATTERNS)


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        Path(tmp).replace(path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def swap(url: str, targets: tuple[Path, ...] = _TARGETS) -> int:
    if not _is_valid_youtube_url(url):
        print(
            f"ERROR: {url!r} is not a valid YouTube URL "
            "(expected https://youtu.be/<11-char-id> or "
            "https://www.youtube.com/watch?v=<11-char-id>)",
            file=sys.stderr,
        )
        return 1
    changed: list[Path] = []
    for target in targets:
        if not target.exists():
            print(f"ERROR: {target} does not exist", file=sys.stderr)
            return 1
        text = target.read_text(encoding="utf-8")
        if _PLACEHOLDER_URL not in text and _PLACEHOLDER_MARKER not in text:
            print(
                f"ERROR: {target}: neither placeholder marker "
                f"{_PLACEHOLDER_MARKER!r} nor placeholder URL "
                f"{_PLACEHOLDER_URL!r} present — refusing to overwrite "
                "(probably already swapped)",
                file=sys.stderr,
            )
            return 1
        new_text = text.replace(_PLACEHOLDER_URL, url)
        new_text = new_text.replace(_PLACEHOLDER_MARKER, f"<!-- demo-video: {url} -->")
        if new_text != text:
            _atomic_write(target, new_text)
            changed.append(target)
    print(f"Swapped demo video URL to {url} in {len(changed)} file(s):")
    for p in changed:
        try:
            display = p.relative_to(_REPO)
        except ValueError:
            display = p
        print(f"  ✓ {display}")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Swap demo-video placeholder for real URL.")
    parser.add_argument("url", help="YouTube URL (youtu.be/<id> or youtube.com/watch?v=<id>)")
    args = parser.parse_args(argv)
    return swap(args.url)


if __name__ == "__main__":
    sys.exit(main())
