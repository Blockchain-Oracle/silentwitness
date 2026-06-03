"""Per-tool regex catalog for the output normalizer (architecture §4.6).

Patterns are pre-compiled at import time so the hot path's per-line
matching costs nothing beyond the regex engine's match step. The
:data:`TOOL_PATTERNS` registry maps a snake_case tool name to a
:class:`ToolPatternSet` of three explicit pattern roles:

* ``banner`` — matches lines that must be dropped wholesale (the tool's
  own version stamp, "Framework X.Y" lines).
* ``metadata_timestamp_lines`` — matches lines on which wall-clock
  timestamps are non-evidence (e.g., "EvtxECmd version 1.x" header,
  "Total events processed at ...") and should be tokenized to ``<TS>``.
* ``diagnostic_lines`` — matches tool-emitted diagnostic chatter (e.g.,
  Vol3's ``Stacking`` / ``Progress:`` / ``Scanning`` lines) where the
  agent's reading of paths is incidental and Windows-style backslashes
  should be normalised to forward slashes for byte-stability.

Tools NOT in the registry get the :data:`EMPTY_PATTERNS` (no per-tool
rules); the universal rules (ANSI strip, line endings, trailing
whitespace collapse) still apply.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern


@dataclass(frozen=True, slots=True)
class ToolPatternSet:
    """Three pattern roles a tool may opt into; any may be ``None`` (no-op)."""

    banner: Pattern[str] | None = None
    metadata_timestamp_lines: Pattern[str] | None = None
    diagnostic_lines: Pattern[str] | None = None


# ISO-8601 wall-clock timestamps — both space-separated and T-separated forms,
# with or without fractional seconds, with or without a Z suffix or numeric
# timezone offset. Matched ONLY inside metadata lines (per
# :class:`ToolPatternSet.metadata_timestamp_lines`); evidence content (EVTX
# event timestamps in CSV rows) is left verbatim.
ISO_TIMESTAMP: Pattern[str] = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"
)

# ANSI CSI escape sequences (colour, cursor, erase). Stripped universally
# regardless of tool — every modern terminal-aware tool may emit them when
# stdout is incorrectly detected as a TTY.
ANSI_SEQUENCE: Pattern[str] = re.compile(r"\x1B\[[0-9;]*[mK]")

EMPTY_PATTERNS = ToolPatternSet()


# Volatility 3's version banner and progress chatter. The plugin name suffix
# (``vol_pslist`` / ``vol_pstree`` / ``vol_psscan`` / ``vol_malfind`` / etc.)
# all emit the same banner shape and the same diagnostic lines, so the entries
# share the same pattern set.
_VOL3_BANNER: Pattern[str] = re.compile(r"^Volatility 3 Framework\b")
_VOL3_DIAGNOSTIC: Pattern[str] = re.compile(
    r"^(?:Stacking|Constructing|Progress:|Scanning|Reading|Loading|Volatility)"
)

# EvtxECmd writes a header with wall-clock timestamps on its own start /
# completion / progress lines. The CSV event rows themselves contain real
# evidence timestamps and MUST be preserved — we discriminate by line shape.
_EVTX_METADATA: Pattern[str] = re.compile(
    r"^(?:EvtxECmd|Total events processed|Processing started|Processing completed|Command line:)"
)

TOOL_PATTERNS: dict[str, ToolPatternSet] = {
    "vol_pslist": ToolPatternSet(banner=_VOL3_BANNER, diagnostic_lines=_VOL3_DIAGNOSTIC),
    "vol_pstree": ToolPatternSet(banner=_VOL3_BANNER, diagnostic_lines=_VOL3_DIAGNOSTIC),
    "vol_psscan": ToolPatternSet(banner=_VOL3_BANNER, diagnostic_lines=_VOL3_DIAGNOSTIC),
    "vol_malfind": ToolPatternSet(banner=_VOL3_BANNER, diagnostic_lines=_VOL3_DIAGNOSTIC),
    "vol_netscan": ToolPatternSet(banner=_VOL3_BANNER, diagnostic_lines=_VOL3_DIAGNOSTIC),
    "vol_filescan": ToolPatternSet(banner=_VOL3_BANNER, diagnostic_lines=_VOL3_DIAGNOSTIC),
    "vol_lsadump": ToolPatternSet(banner=_VOL3_BANNER, diagnostic_lines=_VOL3_DIAGNOSTIC),
    "parse_evtx": ToolPatternSet(metadata_timestamp_lines=_EVTX_METADATA),
}


__all__ = [
    "ANSI_SEQUENCE",
    "EMPTY_PATTERNS",
    "ISO_TIMESTAMP",
    "TOOL_PATTERNS",
    "ToolPatternSet",
]
