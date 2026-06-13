#!/usr/bin/env python3
"""Gate: docs/TRY_IT_OUT.md — judge-facing walkthrough invariants.

12 rule slugs (13 fail sites — model_strings fires from two distinct sites):

  doc_exists / doc_unreadable / max_lines / h1 / sift_install / docker_up /
  docker_exec / model_strings / nitroba_command / troubleshooting_section_missing /
  troubleshooting_entries / banned_vocab

Each routes through _fail() so the CI log carries a grep-able slug.
Exit 0 on pass; 1 with rule slug on stderr.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_DOC = _REPO / "docs" / "TRY_IT_OUT.md"
_MAX = 400
_REQUIRED_MODELS = ("anthropic:", "openai:", "google-gla:", "ollama:")
_BANNED = (
    "court-admissible",
    "autonomous SOC",
    "Ralph Wiggum",
    "replaces L1",
    "eliminates hallucinations",
)


def _fail(rule: str, detail: str = "") -> int:
    print(f"TRY_IT_OUT gate FAIL: {rule}" + (f" — {detail}" if detail else ""), file=sys.stderr)
    return 1


def _section_slice(text: str, heading: str) -> str:
    """Return the text from `heading` (line-anchored) up to the next ## or EOF."""
    pattern = f"\n{heading}"
    idx = text.find(pattern)
    if idx < 0 and text.startswith(heading):
        idx = 0
    elif idx >= 0:
        idx += 1  # skip the leading newline
    else:
        return ""
    next_h2 = text.find("\n## ", idx + 1)
    return text[idx : next_h2 if next_h2 > 0 else len(text)]


def _strip_code_fences(text: str) -> str:
    """Strip ```...``` fenced blocks so banned-vocab discussions in code don't false-fire."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def _contains_provider_prefix(section: str, prefix: str) -> bool:
    """Word-bounded check so `openai:` doesn't false-pass on `openai-chat:`."""
    # The prefix ends in `:`; require the char before is not a word char or hyphen
    # (so `openai-chat:` does NOT match `openai:`).
    pattern = rf"(?<![\w-]){re.escape(prefix)}"
    return re.search(pattern, section) is not None


def check(doc_path: Path = _DOC) -> int:
    if not doc_path.exists():
        return _fail("doc_exists", str(doc_path))
    try:
        text = doc_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _fail("doc_unreadable", str(exc))
    lines = text.splitlines()
    if len(lines) > _MAX:
        return _fail("max_lines", f"{len(lines)} > {_MAX}")
    if not any(line.startswith("# Try SilentWitness") for line in lines[:5]):
        return _fail("h1", "expected `# Try SilentWitness` within first 5 lines")
    if "curl --proto '=https' --tlsv1.2 -sSf" not in text or "install.sh | bash" not in text:
        return _fail("sift_install", "Path A install one-liner missing")
    if "docker compose up -d" not in text:
        return _fail("docker_up", "Path B `docker compose up -d` missing")
    if "docker compose exec silentwitness" not in text:
        return _fail("docker_exec", "Path B `docker compose exec silentwitness` missing")
    model_section = _section_slice(text, "## Model selection")
    if not model_section:
        return _fail("model_strings", "`## Model selection` section missing")
    for prefix in _REQUIRED_MODELS:
        if not _contains_provider_prefix(model_section, prefix):
            return _fail("model_strings", f"missing word-bounded provider prefix {prefix!r}")
    if "nitroba-smoke-001" not in text:
        return _fail("nitroba_command", "no `nitroba-smoke-001` command present")
    troubleshooting = _section_slice(text, "## Troubleshooting")
    if not troubleshooting:
        return _fail(
            "troubleshooting_section_missing", "`## Troubleshooting` section missing entirely"
        )
    qa_count = sum(
        1 for ln in troubleshooting.splitlines() if ln.startswith('- "') or ln.startswith("- **")
    )
    if qa_count < 6:
        return _fail("troubleshooting_entries", f"need >=6 Q&A bullets; found {qa_count}")
    # Banned vocab — strip fenced code blocks first so legitimate meta-discussion
    # in a Q&A or code example doesn't trip the gate.
    prose_text = _strip_code_fences(text)
    for phrase in _BANNED:
        if phrase.lower() in prose_text.lower():
            return _fail("banned_vocab", f"{phrase!r}")
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Check docs/TRY_IT_OUT.md against story gate.",
    )
    parser.add_argument("--doc", type=Path, default=_DOC)
    args = parser.parse_args(argv)
    return check(args.doc)


if __name__ == "__main__":
    sys.exit(main())
