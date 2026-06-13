#!/usr/bin/env python3
"""Gate: docs/TRY_IT_OUT.md — judge-facing walkthrough invariants.

11 rules — each routes through _fail() with a grep-able slug:

  doc_exists / doc_unreadable / max_lines / h1 / sift_install / docker_up /
  docker_exec / model_strings / nitroba_command / troubleshooting_entries /
  banned_vocab

Exit 0 on pass; 1 with rule slug on stderr.
"""

from __future__ import annotations

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
    idx = text.find(heading)
    if idx < 0:
        return ""
    next_h2 = text.find("\n## ", idx + 1)
    return text[idx : next_h2 if next_h2 > 0 else len(text)]


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
    # All 4 provider model strings must be referenced in the Model selection section
    model_section = _section_slice(text, "## Model selection")
    if not model_section:
        return _fail("model_strings", "`## Model selection` section missing")
    for prefix in _REQUIRED_MODELS:
        if prefix not in model_section:
            return _fail("model_strings", f"missing provider prefix {prefix!r}")
    if "nitroba-smoke-001" not in text:
        return _fail("nitroba_command", "no `nitroba-smoke-001` command present")
    troubleshooting = _section_slice(text, "## Troubleshooting")
    # Count Q&A entries — each is a top-level bullet line `- "...`
    qa_count = sum(
        1 for ln in troubleshooting.splitlines() if ln.startswith('- "') or ln.startswith("- **")
    )
    if qa_count < 6:
        return _fail(
            "troubleshooting_entries",
            f"need >=6 Q&A bullets; found {qa_count}",
        )
    for phrase in _BANNED:
        if phrase.lower() in text.lower():
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
