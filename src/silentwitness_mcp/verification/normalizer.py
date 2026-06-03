"""Deterministic output normalizer — citation-gate SHA-256 surface (architecture §4.6).

Every tool wrapper passes its raw stdout through :func:`normalize_output`
before the citation gate hashes the result. Two successive runs of the
same tool against the same evidence MUST produce byte-identical normalised
output so the recorded ``content_sha256`` stays comparable. Drift between
"what the model saw" and "what the gate later verifies" would break the
wedge silently.

The six rules (architecture §4.6) applied in execution order:

* **(6) Line-ending normalization** — ``\\r\\n`` and standalone ``\\r``
  collapse to ``\\n`` first so every subsequent line-based rule can
  ``str.split("\\n")`` without surprises. Spec lists this as rule 6; we
  apply it first because the rest of the pipeline is line-aware. The
  visible effect is identical to applying it last (idempotent).
* **(5) ANSI escape strip** — CSI sequences (``\\x1B[...m`` /
  ``\\x1B[...K``) erased regardless of tool. Modern Vol3 / EvtxECmd may
  emit them when stdout's TTY-detection is wrong.
* **(1) Banner strip** — per-tool pattern matched against each line; the
  line is dropped if it matches.
* **(2) Metadata-timestamp tokenize** — per-tool pattern matches lines
  where wall-clock timestamps are non-evidence; matched lines have their
  ISO-8601 timestamps replaced with the literal token ``<TS>``. Evidence
  content (EVTX event rows) is left verbatim — the discriminator is the
  per-tool ``metadata_timestamp_lines`` regex.
* **(4) Diagnostic path-separator normalize** — per-tool pattern matches
  tool-internal diagnostic lines (Vol3 progress chatter); on those lines
  backslashes become forward slashes. Evidence-content paths (e.g.
  ``C:\\Program Files\\Ethereal\\``) are preserved verbatim because they
  do not match the diagnostic pattern.
* **(3) Whitespace collapse** — trailing spaces / tabs on every line
  rstripped. Applied last so any whitespace exposed by the preceding
  ANSI / banner / metadata transforms is cleaned in the same pass.

Idempotency: ``normalize_output(normalize_output(x, t), t) ==
normalize_output(x, t)`` for any byte payload ``x`` and tool name ``t``.
Determinism: no time / random / locale dependencies — same input always
maps to same output.

The original (pre-normalised) output is NOT retained per the architecture
§4.6 commitment "what the model saw is what the gate verifies."
"""

from __future__ import annotations

from silentwitness_mcp.verification._patterns import (
    ANSI_SEQUENCE,
    EMPTY_PATTERNS,
    ISO_TIMESTAMP,
    TOOL_PATTERNS,
    ToolPatternSet,
)

_TIMESTAMP_PLACEHOLDER = "<TS>"


def normalize_output(raw: bytes, tool: str) -> bytes:
    """Return the byte-stable canonical form of ``raw`` for ``tool``.

    ``raw`` is decoded UTF-8 with ``errors="replace"`` so a tool that emits
    invalid UTF-8 (rare, but possible from Vol3's plugin output when a
    process memory string is dumped raw) still produces a deterministic
    canonical form — the U+FFFD replacement character is itself stable.

    Output is bytes (not str) so the caller can ``hashlib.sha256(...)``
    directly without re-encoding (which would introduce a normalisation
    choice the caller could get wrong).
    """
    patterns: ToolPatternSet = TOOL_PATTERNS.get(tool, EMPTY_PATTERNS)
    text = raw.decode("utf-8", errors="replace")
    text = _normalize_line_endings(text)
    text = _strip_ansi(text)
    lines = text.split("\n")
    lines = _strip_banner_lines(lines, patterns)
    lines = _tokenize_metadata_timestamps(lines, patterns)
    lines = _normalize_diagnostic_paths(lines, patterns)
    lines = _rstrip_trailing_whitespace(lines)
    return "\n".join(lines).encode("utf-8")


# ---------------------------------------------------------------------------
# Per-rule helpers (pure functions, each one rule, each one idempotent)
# ---------------------------------------------------------------------------


def _normalize_line_endings(text: str) -> str:
    """``\\r\\n`` → ``\\n`` first so a lone ``\\r`` isn't doubled into ``\\n\\n``.

    Order matters: replacing ``\\r`` before ``\\r\\n`` would turn
    ``"a\\r\\nb"`` into ``"a\\n\\nb"`` — an extra blank line that would
    appear/disappear depending on input line-ending style. CRLF first
    keeps the rule idempotent and platform-stable.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _strip_ansi(text: str) -> str:
    return ANSI_SEQUENCE.sub("", text)


def _strip_banner_lines(lines: list[str], patterns: ToolPatternSet) -> list[str]:
    if patterns.banner is None:
        return lines
    banner = patterns.banner
    return [line for line in lines if not banner.match(line)]


def _tokenize_metadata_timestamps(lines: list[str], patterns: ToolPatternSet) -> list[str]:
    """Replace ISO-8601 timestamps with ``<TS>`` on metadata-only lines.

    The per-tool ``metadata_timestamp_lines`` regex is the discriminator:
    lines that match are header/footer/progress lines whose timestamps
    are wall-clock noise. Lines that do NOT match (typically CSV event
    rows from EvtxECmd) keep their timestamps as evidence content.
    """
    pattern = patterns.metadata_timestamp_lines
    if pattern is None:
        return lines
    return [
        ISO_TIMESTAMP.sub(_TIMESTAMP_PLACEHOLDER, line) if pattern.match(line) else line
        for line in lines
    ]


def _normalize_diagnostic_paths(lines: list[str], patterns: ToolPatternSet) -> list[str]:
    """Backslash → forward slash on tool-diagnostic lines only.

    Vol3's ``Stacking`` / ``Progress:`` chatter includes module paths the
    agent doesn't reason about; normalising those decouples the citation
    gate's hash from a path-separator preference that varies by Vol3
    version. Evidence-content lines (process command lines containing
    ``C:\\Program Files\\...``) do NOT match the diagnostic pattern and
    are preserved verbatim.
    """
    pattern = patterns.diagnostic_lines
    if pattern is None:
        return lines
    return [line.replace("\\", "/") if pattern.match(line) else line for line in lines]


def _rstrip_trailing_whitespace(lines: list[str]) -> list[str]:
    """``rstrip(" \\t")`` per line — preserves the line itself but trims
    trailing spaces/tabs. Run last so any whitespace exposed by the
    preceding banner / ANSI / metadata transforms is cleaned in one pass.
    """
    return [line.rstrip(" \t") for line in lines]


__all__ = ["normalize_output"]
