"""Shared `[UNTRUSTED EVIDENCE BEGIN/END]` wrap utilities for the finding recorders.

The sanitizer (``verification/sanitizer.py``) wraps every LLM-bound evidence string
with two marker tokens for prompt-injection visibility. The wrap is a hot-path LLM
visibility seam — it must NOT leak into stored findings (the leak this module fixes
is the root cause of task #20).

Three recorders share the same shape: ``record_observation``, ``record_interpretation``,
``record_narrative``, ``record_pivot``. Putting the strip logic here keeps the four
sites byte-for-byte identical and the constants in one place — a future sanitizer-format
tweak lands in one file, not four.

Hardening: an "impossible" half-wrapped input (only one marker present) is an explicit
error rather than a silent passthrough — the sanitizer today never emits such a thing,
but a future refactor or a corrupted buffer would land partial markers in
``findings.json`` if we permissively returned the raw bytes. See `_StripError`.
"""

from __future__ import annotations

import logging
from typing import Final

from silentwitness_mcp.verification.sanitizer import _MARKER_BEGIN, _MARKER_END

_LOG = logging.getLogger(__name__)


_WRAP_BEGIN: Final = f"{_MARKER_BEGIN}\n"
_WRAP_END: Final = f"\n{_MARKER_END}"


class StripError(ValueError):
    """Raised when a wrapped payload contains exactly one of the two markers.

    The sanitizer today either wraps both ends or wraps neither (the latter is
    unreachable from the public ``sanitize()`` API). A half-wrap is an "impossible"
    state that, if quietly accepted, would persist a stray marker fragment into
    ``findings.json`` — the exact failure mode task #20 closes. Surfacing it as an
    exception lets the recorder turn it into a structured PIPELINE_INTERNAL_ERROR
    rejection instead of silently leaking."""


def content_after_wrap(sanitized: str) -> str:
    """Strip the sanitizer's outer envelope; return inner content.

    The sanitizer wraps as ``f"{_MARKER_BEGIN}\\n{text}\\n{_MARKER_END}"``. A
    non-wrapped string is returned verbatim (so this is safe to call on legacy
    records). A half-wrapped string raises :class:`StripError` — see class docstring."""
    has_begin = sanitized.startswith(_WRAP_BEGIN)
    has_end = sanitized.endswith(_WRAP_END)
    if has_begin and has_end:
        return sanitized[len(_WRAP_BEGIN) : -len(_WRAP_END)]
    if has_begin or has_end:
        # One but not both — an inconsistent envelope is never a leak we silently let pass.
        _LOG.error(
            "content_after_wrap: half-wrapped payload (has_begin=%s, has_end=%s, len=%d)",
            has_begin,
            has_end,
            len(sanitized),
        )
        raise StripError(f"sanitizer envelope is half-present (begin={has_begin}, end={has_end})")
    # No markers at all — already-clean (legacy record, plain string, etc.).
    return sanitized


__all__ = ["_WRAP_BEGIN", "_WRAP_END", "StripError", "content_after_wrap"]
