"""Line-terminator scrubber for ``payload.text`` (round-2 silent-failure C2).

``append_jsonl_line`` rejects U+2028, U+2029, NEL, VT, FF, FS, GS, RS.
The sanitizer covers BIDI / zero-width / tag-char but NOT these line
terminators — an attacker-planted U+2028 in observation text would
otherwise erase the audit row + leak a raw ValueError past the envelope.
Substitute with U+FFFD so the substitution is grep-visible in audit logs.
"""

from __future__ import annotations

_LINE_TERMINATOR_CHARS = (
    " ",  # noqa: RUF001 - LINE SEPARATOR
    " ",  # noqa: RUF001 - PARAGRAPH SEPARATOR
    "\x85",  # NEL
    "\x0b",  # VT
    "\x0c",  # FF
    "\x1c",  # FS
    "\x1d",  # GS
    "\x1e",  # RS
)


def scrub_line_terminators(value: str) -> str:
    """Replace forbidden line-terminator chars with U+FFFD."""
    for ch in _LINE_TERMINATOR_CHARS:
        value = value.replace(ch, "�")
    return value


__all__ = ["scrub_line_terminators"]
