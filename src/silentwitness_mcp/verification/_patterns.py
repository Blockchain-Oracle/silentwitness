"""Per-tool regex catalog for the output normalizer (architecture §4.6).

Patterns are pre-compiled at import time so the hot path's per-line
matching costs nothing beyond the regex engine's match step. The
:data:`TOOL_PATTERNS` registry maps a snake_case tool name to a
:class:`ToolPatternSet` of three explicit pattern roles:

* ``banner`` — matches lines that must be dropped wholesale.
* ``metadata_timestamp_lines`` — matches lines on which the TRAILING
  wall-clock timestamp is non-evidence. The normalizer tokenizes ONLY
  the last timestamp on a matched line so any earlier timestamp (which
  may be embedded evidence like a source-file path) survives.
* ``diagnostic_lines`` — matches tool-emitted *non-evidence-bearing*
  diagnostic chatter (Vol3's plugin-stacking / dependency-graph
  construction lines). Lines that quote evidence paths (``Reading
  from C:\\...``, ``Loading symbol C:\\...``) are NOT in the set per
  PR-106 silent-failure review — those phrases ARE evidence carriers.

Patterns use ``[0-9]`` not ``\\d`` so digit matching is ASCII-only;
``\\d`` is Unicode-aware and matches ``Nd``-category code points
(Arabic-Indic digits, fullwidth digits, etc.). Cross-Python-version
drift on Unicode-digit category membership would otherwise produce
different hashes for byte-identical evidence on different builds.

Tools NOT in the registry raise :class:`UnknownToolError` (loud-fail per
PR-106 silent-failure H1). The explicit ``"_universal_only"`` key maps
to :data:`EMPTY_PATTERNS` for callers that want only the universal rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern


@dataclass(frozen=True, slots=True)
class ToolPatternSet:
    """Three pattern roles a tool may opt into; any may be ``None`` (no-op).

    Frozen + slots so :data:`EMPTY_PATTERNS` can safely be a module-level
    shared singleton.
    """

    banner: Pattern[str] | None = None
    metadata_timestamp_lines: Pattern[str] | None = None
    diagnostic_lines: Pattern[str] | None = None


# ISO-8601 wall-clock timestamps. ``[0-9]`` not ``\d`` per module docstring.
ISO_TIMESTAMP: Pattern[str] = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[T ]"
    r"[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?"
    r"(?:Z|[+-][0-9]{2}:?[0-9]{2})?"
)


# Broadened ANSI escape grammar (PR-106 silent-failure C4). Covers:
#   * CSI: ESC [ <param-bytes 0-?> <intermediate 0x20-0x2F>* <final 0x40-0x7E>
#     — catches cursor moves (\x1B[2A), hide-cursor (\x1B[?25l), erase
#     (\x1B[2J), and SGR (\x1B[31m).
#   * OSC: ESC ] <text> (BEL | ST=ESC\) — covers window-title (\x1B]0;...\x07).
#   * Two-byte ESC C1 controls (\x1B@ through \x1B_).
ANSI_SEQUENCE: Pattern[str] = re.compile(
    r"\x1B(?:"
    r"\[[0-?]*[ -/]*[@-~]"
    r"|\][^\x07\x1B]*(?:\x07|\x1B\\)"
    r"|[@-Z\\-_]"
    r")"
)

# Trailing-whitespace strip set (PR-106 silent-failure H4). ASCII space + tab
# + form-feed + vertical-tab + NBSP (U+00A0) + zero-width space (U+200B) +
# narrow-no-break (U+202F) + BOM (U+FEFF). Newline is intentionally NOT
# included — line endings are rule 6.
TRAILING_WHITESPACE_CHARS = " \t\v\f\u00a0\u200b\u202f\ufeff"


EMPTY_PATTERNS = ToolPatternSet()


# Vol3 banner + narrowed diagnostic. ``Reading`` / ``Loading`` / ``Scanning``
# REMOVED in PR-106 round-2 — Vol3 plugins emit ``Reading from C:\\...`` and
# ``Loading symbol C:\\...`` where the path IS evidence; backslash conversion
# on those lines would silently mutate evidence.
_VOL3_BANNER: Pattern[str] = re.compile(r"^Volatility 3 Framework\b")
_VOL3_DIAGNOSTIC: Pattern[str] = re.compile(r"^(?:Stacking|Constructing|Progress:)")

# EvtxECmd's start / completion stamp lines. ``Command line:`` REMOVED in
# PR-106 round-2 — the CLI argv often embeds evidence file paths containing
# ISO-8601 timestamps (``--source pull_2026-06-02T03:14:00Z.evtx``) and
# cannot be safely tokenized.
_EVTX_METADATA: Pattern[str] = re.compile(
    r"^(?:EvtxECmd|Total events processed|Processing started|Processing completed)"
)

_VOL3 = ToolPatternSet(banner=_VOL3_BANNER, diagnostic_lines=_VOL3_DIAGNOSTIC)
_EVTX = ToolPatternSet(metadata_timestamp_lines=_EVTX_METADATA)

TOOL_PATTERNS: dict[str, ToolPatternSet] = {
    "vol_pslist": _VOL3,
    "vol_pstree": _VOL3,
    "vol_psscan": _VOL3,
    "vol_malfind": _VOL3,
    "vol_netscan": _VOL3,
    "vol_cmdline": _VOL3,
    "vol_dlllist": _VOL3,
    "vol_handles": _VOL3,
    "vol_filescan": _VOL3,
    "vol_lsadump": _VOL3,
    # EZ-Tools CSV outputs are byte-stable — MFTECmd does NOT emit a
    # banner into the CSV (the version banner goes to stdout, never
    # to the CSV). Universal-rules-only suffices.
    "parse_mft": EMPTY_PATTERNS,
    "parse_amcache": EMPTY_PATTERNS,
    "parse_shimcache": EMPTY_PATTERNS,
    "parse_prefetch": EMPTY_PATTERNS,
    "parse_shellbags": EMPTY_PATTERNS,
    "regripper_run": EMPTY_PATTERNS,
    "parse_evtx": _EVTX,
    "chainsaw_hunt": EMPTY_PATTERNS,
    "hayabusa_csv_timeline": EMPTY_PATTERNS,
    "zeek_run": EMPTY_PATTERNS,
    # Explicit "universal rules only" sentinel — callers that don't need
    # per-tool transforms use this rather than a typo'd tool name silently
    # producing wrong output.
    "_universal_only": EMPTY_PATTERNS,
}


__all__ = [
    "ANSI_SEQUENCE",
    "EMPTY_PATTERNS",
    "ISO_TIMESTAMP",
    "TOOL_PATTERNS",
    "TRAILING_WHITESPACE_CHARS",
    "ToolPatternSet",
]
