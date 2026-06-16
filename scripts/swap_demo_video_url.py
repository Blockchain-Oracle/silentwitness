#!/usr/bin/env python3
"""Swap the demo-video placeholder for the real hosted demo URL at submission time.

Validates a YouTube or Vimeo URL form, then writes each target via tempfile +
atomic ``Path.replace`` (per-file atomic, no cross-file rollback — submission
is a single-operator one-shot, the gate catches half-swapped state on re-run).
Refuses on a target that contains neither the marker comment nor the
placeholder URL (refuse-by-default rather than overwrite).
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
_VIDEO_PATTERNS = (
    re.compile(r"^https://youtu\.be/[A-Za-z0-9_-]{11}$"),
    re.compile(r"^https://(www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]{11}(&.*)?$"),
    re.compile(r"^https://vimeo\.com/\d+$"),
)


def _is_valid_video_url(url: str) -> bool:
    return any(p.match(url) for p in _VIDEO_PATTERNS)


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        Path(tmp).replace(path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError as cleanup_exc:
            print(
                f"WARN: failed to clean up tmp file {tmp}: {cleanup_exc}",
                file=sys.stderr,
            )
        raise


def swap(url: str, targets: tuple[Path, ...] = _TARGETS) -> int:
    if not _is_valid_video_url(url):
        print(
            f"ERROR: {url!r} is not a valid YouTube or Vimeo URL "
            "(expected https://youtu.be/<11-char-id> or "
            "https://www.youtube.com/watch?v=<11-char-id> or "
            "https://vimeo.com/<numeric-id>)",
            file=sys.stderr,
        )
        return 1
    # Two-pass: validate every target has a placeholder before mutating any
    # file. Avoids the half-swapped state where target[0] writes succeed and
    # target[1] is missing the marker — observed as a confusing partial-swap.
    pending: list[tuple[Path, str, str]] = []
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
        pending.append((target, text, new_text))
    changed: list[Path] = []
    for target, text, new_text in pending:
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
    parser.add_argument("url", help="YouTube or Vimeo URL")
    args = parser.parse_args(argv)
    return swap(args.url)


if __name__ == "__main__":
    sys.exit(main())
