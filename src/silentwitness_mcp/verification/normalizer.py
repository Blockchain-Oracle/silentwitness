"""Deterministic output normalizer — citation-gate SHA-256 surface (architecture §4.6).

Every tool wrapper passes its raw stdout through :func:`normalize_output`
before the citation gate hashes the result. Two successive runs of the
same tool against the same evidence MUST produce byte-identical normalised
output so the recorded ``content_sha256`` stays comparable. Drift between
"what the model saw" and "what the gate later verifies" would break the
wedge silently.

The six rules (architecture §4.6) applied in execution order:

* **(6) Line endings** — ``\\r\\n`` / lone ``\\r`` → ``\\n`` first so every
  subsequent line-based rule can ``str.split("\\n")`` without splitting on
  platform-quirks. Spec lists this as rule 6; we apply it first because
  the rest of the pipeline is line-aware. Idempotent — second-pass on
  ``\\n``-only text is a no-op.
* **(5) ANSI escape strip** — Broad ECMA-48 CSI grammar (final byte
  ``[@-~]``) + OSC (terminated by BEL or ST) + 2-byte ESC controls.
  Catches cursor moves and hide-cursor sequences that progress bars emit
  when stdout's TTY-detection is wrong.
* **(1) Banner strip** — per-tool pattern matched against each line; the
  line is dropped if it matches.
* **(2) Metadata-timestamp tokenize** — on lines matching the per-tool
  ``metadata_timestamp_lines`` regex, ONLY the trailing timestamp is
  replaced with ``<TS>``. Earlier timestamps on the same line (which may
  be embedded evidence) survive. Evidence content (EVTX event rows, CSV)
  doesn't match the discriminator and is untouched.
* **(4) Diagnostic path-separator normalize** — per-tool pattern matches
  *non-evidence-bearing* diagnostic prefixes (Vol3's ``Stacking`` /
  ``Constructing`` / ``Progress:``). On matched lines, backslashes become
  forward slashes. Evidence-content lines (process command lines, paths
  on ``Reading`` / ``Loading`` chatter — PR-106 silent-failure C2) are
  preserved verbatim because they no longer match the diagnostic pattern.
* **(3) Trailing whitespace strip** — extended set (ASCII space + tab +
  form-feed + vertical-tab + NBSP + zero-width space) rstripped per line.
  Applied last so any invisible bytes exposed by the preceding ANSI /
  banner / metadata transforms are cleaned in one pass.

UTF-8 handling uses ``errors="surrogateescape"`` (bijective on
``bytes ↔ str``) so two raw inputs that differ ONLY in invalid bytes
produce DIFFERENT normalised outputs. ``errors="replace"`` would have
collapsed both to U+FFFD — a non-injective surface an attacker could
exploit to collide tampered evidence with a recorded hash (PR-106
silent-failure H5).

Idempotency: ``normalize_output(normalize_output(x, t), t) ==
normalize_output(x, t)`` for any byte payload ``x`` and any registered
tool ``t``. Property-tested with Hypothesis.

Determinism: pure function, no time / random / locale dependencies. ASCII
digits in regexes (``[0-9]`` not ``\\d``) so the rule set doesn't drift
across Python builds whose Unicode ``Nd`` category differs.

Unknown tool names raise :class:`UnknownToolError` rather than silently
falling back — a typo'd ``"vol_pslit"`` would otherwise produce a
different canonical form than the intended ``"vol_pslist"`` and break
citation comparison with zero diagnostic signal (PR-106 silent-failure
H1). Callers that genuinely want only universal rules pass the explicit
``"_universal_only"`` sentinel.
"""

from __future__ import annotations

from silentwitness_mcp.verification._patterns import (
    ANSI_SEQUENCE,
    ISO_TIMESTAMP,
    TOOL_PATTERNS,
    TRAILING_WHITESPACE_CHARS,
    ToolPatternSet,
)

_TIMESTAMP_PLACEHOLDER = "<TS>"


class UnknownToolError(ValueError):
    """Raised when ``normalize_output`` receives a tool string not in the registry.

    Listing the known keys in the message helps the caller spot typos
    immediately. The explicit ``"_universal_only"`` sentinel is the way
    to opt out of per-tool rules without registering a new entry.
    """


def normalize_output(raw: bytes, tool: str) -> bytes:
    """Return the byte-stable canonical form of ``raw`` for ``tool``.

    ``raw`` is decoded via ``utf-8`` with ``surrogateescape`` errors so
    invalid bytes round-trip losslessly through the pipeline — two raw
    inputs that differ only in invalid UTF-8 produce DIFFERENT normalised
    outputs, preserving the collision-resistance the citation gate depends
    on.

    Output is bytes (not str) so the caller can ``hashlib.sha256(...)``
    directly without re-encoding. Raises :class:`UnknownToolError` for any
    tool name not in :data:`silentwitness_mcp.verification._patterns.TOOL_PATTERNS`.
    """
    try:
        patterns: ToolPatternSet = TOOL_PATTERNS[tool]
    except KeyError as exc:
        known = ", ".join(sorted(TOOL_PATTERNS))
        raise UnknownToolError(
            f"tool {tool!r} not registered in TOOL_PATTERNS. Known: {known}. "
            "Use tool='_universal_only' for the explicit universal-rules-only path."
        ) from exc
    text = raw.decode("utf-8", errors="surrogateescape")
    text = _normalize_line_endings(text)
    text = _strip_ansi(text)
    lines = text.split("\n")
    lines = _strip_banner_lines(lines, patterns)
    lines = _tokenize_trailing_metadata_timestamps(lines, patterns)
    lines = _normalize_diagnostic_paths(lines, patterns)
    lines = _rstrip_trailing_whitespace(lines)
    return "\n".join(lines).encode("utf-8", errors="surrogateescape")


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


def _tokenize_trailing_metadata_timestamps(lines: list[str], patterns: ToolPatternSet) -> list[str]:
    """Replace the TRAILING timestamp on metadata-matched lines with ``<TS>``.

    Only the last timestamp on the line is replaced (PR-106 silent-failure
    C1): EvtxECmd metadata lines may embed an evidence source-file path
    that itself contains an ISO-8601 timestamp; only the wrapper
    start/completion timestamp at end-of-line is non-evidence. Lines that
    do not match the discriminator are unchanged.
    """
    pattern = patterns.metadata_timestamp_lines
    if pattern is None:
        return lines
    return [_replace_trailing_timestamp(line) if pattern.match(line) else line for line in lines]


def _replace_trailing_timestamp(line: str) -> str:
    """Replace only the LAST ``ISO_TIMESTAMP`` match on ``line`` with ``<TS>``."""
    matches = list(ISO_TIMESTAMP.finditer(line))
    if not matches:
        return line
    last = matches[-1]
    return line[: last.start()] + _TIMESTAMP_PLACEHOLDER + line[last.end() :]


def _normalize_diagnostic_paths(lines: list[str], patterns: ToolPatternSet) -> list[str]:
    """Backslash → forward slash on non-evidence-bearing diagnostic lines.

    The diagnostic pattern was narrowed in PR-106 round-2 to exclude
    ``Reading`` / ``Loading`` / ``Scanning`` — those phrases ARE evidence
    carriers in Vol3 plugin output (``Reading from C:\\evidence\\...``),
    so converting their backslashes would silently mutate evidence and
    fail citation comparison downstream.
    """
    pattern = patterns.diagnostic_lines
    if pattern is None:
        return lines
    return [line.replace("\\", "/") if pattern.match(line) else line for line in lines]


def _rstrip_trailing_whitespace(lines: list[str]) -> list[str]:
    """Extended rstrip — ASCII space/tab + form-feed/vertical-tab + NBSP +
    zero-width space. Newline is intentionally NOT in the set (line endings
    are rule 6). Invisible bytes that survived prior transforms get cleaned
    in this last pass."""
    return [line.rstrip(TRAILING_WHITESPACE_CHARS) for line in lines]


__all__ = ["UnknownToolError", "normalize_output"]
