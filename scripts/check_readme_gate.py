#!/usr/bin/env python3
"""README gate (story-readme-polish): verify PRD §11 + §14 invariants.

Exit 0 on pass; exit 1 with the failing rule name on stderr.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_MAX_LINES = 400
_DEMO_RE = re.compile(r"youtu\.be/|youtube\.com/watch|<!--\s*DEMO_VIDEO_URL\s*-->")
_BANNED = (
    "court-admissible",
    "autonomous SOC",
    "Ralph Wiggum",
    "replaces L1",
    "eliminates hallucinations",
)
# "Find Evil!" (literal hackathon name) is allowed; the marketing phrase "find evil"
# (lowercase, no exclamation) without the hackathon link context is the banned form.
_FIND_EVIL_MARKETING = re.compile(r"\bfind evil\b(?!\s*!\s*\])", re.IGNORECASE)


def _fail(rule: str, detail: str = "") -> int:
    msg = f"README gate FAIL: {rule}"
    if detail:
        msg += f" — {detail}"
    print(msg, file=sys.stderr)
    return 1


def check(readme_path: Path) -> int:
    try:
        text = readme_path.read_text(encoding="utf-8")
    except OSError as exc:
        return _fail("readable", f"cannot read {readme_path}: {exc}")
    lines = text.splitlines()

    # Rule 1: H1 SilentWitness within first 5 lines
    if not any(line.startswith("# SilentWitness") for line in lines[:5]):
        return _fail("h1", "expected `# SilentWitness` within first 5 lines")

    # Rule 9: total line count
    if len(lines) > _MAX_LINES:
        return _fail("max_lines", f"{len(lines)} > {_MAX_LINES}")

    # Limit subsequent first-screen checks to first 100 lines
    head = "\n".join(lines[:100])

    # Rule 2: demo video link or placeholder marker
    if not _DEMO_RE.search(head):
        return _fail("demo_video", "no YouTube link or DEMO_VIDEO_URL marker in first 100 lines")

    # Rule 3: image embed alt-text
    if "![" not in head:
        return _fail("image_embed", "no `![alt](path)` image embed in first 100 lines")

    # Rule 4: SIFT native install one-liner
    if not re.search(r"curl[^\n]*install\.sh[^\n]*\|\s*bash", text):
        return _fail("sift_install", "missing curl ... install.sh | bash shell line")

    # Rule 5: Docker Compose path
    if "docker compose up" not in text:
        return _fail("docker_compose", "missing `docker compose up` shell line")

    # Rule 6: mermaid fence
    if "```mermaid" not in text:
        return _fail("mermaid_fence", "missing ```mermaid``` code fence")

    # Rule 7: mermaid block has (architectural) and (prompt-based markers
    mermaid_match = re.search(r"```mermaid\n(.*?)```", text, re.DOTALL)
    if mermaid_match is None:
        return _fail("mermaid_block", "mermaid fence opened but no closing fence")
    mermaid = mermaid_match.group(1)
    arch_count = mermaid.count("(architectural)")
    if arch_count < 6:
        return _fail(
            "mermaid_architectural",
            f"≥6 `(architectural)` labels required, found {arch_count}",
        )
    if "(prompt-based" not in mermaid:
        return _fail("mermaid_prompt_based", "missing `(prompt-based` label inside mermaid block")

    # Rule 8: literal MIT license reference
    if "MIT" not in text:
        return _fail("mit_license", "missing literal `MIT` license reference")

    # Rule 10: banned vocab list (CI grep gate, PRD §14)
    for phrase in _BANNED:
        if phrase.lower() in text.lower():
            return _fail("banned_vocab", f"phrase {phrase!r} present (PRD §14)")
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
