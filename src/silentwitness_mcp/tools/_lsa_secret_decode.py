"""Shared UTF-16LE printable-acceptance and host-managed-key catalogue
for the LSA-secret tool family. Lives in a standalone module so the
pure-function helpers (acceptance band, binary-key allowlist, UTF-16LE
decode) are unit-testable in isolation from the Pydantic model boundary,
and so a future second LSA-family model can import the helpers without
pulling in :class:`LsaSecretEntry`.

A printable rendering of LSA-secret Hex bytes is best-effort: it
exists for analyst comfort, not as the audit-trail authority. The Hex
field is what the entity gate cites. The invariants enforced here:

* Empty string after rstrip-NUL is not "printable" — it is "no
  rendering exists".
* Any chr in Unicode category C (control), Cs (surrogate), or Cn
  (unassigned) reduces the string to "no rendering" — silently
  mangling bytes into a string would corrupt the audit chain.
* Pure-whitespace strings (all chars in Unicode Z category) are
  rejected. A real LSA secret being all-whitespace is implausible
  enough that the case more likely reflects a scrubbed/poisoned slot,
  and an analyst reading ``Secret="   "`` would not be able to tell
  the two apart.
* Keys whose values are by-design random bytes (NTLM hashes, AES key
  material, DPAPI seeds) skip the decode entirely — surfacing a
  CJK-glyph "decoded secret" for an NTLM hash is operationally
  misleading, even when the bytes happen to land in the printable
  band."""

from __future__ import annotations

import unicodedata
from typing import Final

# Acceptance band for the convenience-only Secret field. Includes the
# major-category letters/marks/numbers/punctuation/symbols/separators.
# Deliberately excludes C (control), surrogate halves, and unassigned.
_ACCEPTED_UNICODE_CATEGORIES: Final = frozenset({"L", "M", "N", "P", "S", "Z"})

# Keys whose values are host-managed random bytes (NTLM hashes, AES
# key material, DPAPI master-key seeds). The convenience Secret
# rendering for these is by-definition meaningless even when the bytes
# accidentally land in the printable Unicode band — surfacing a CJK
# glyph or symbol string here would be actively misleading. Hex
# remains the authoritative citation.
BINARY_KEY_NAMES: Final = frozenset(
    {
        "$MACHINE.ACC",  # NTLM hash of the machine account
        "NL$KM",  # cached-credential AES key material
        "DPAPI_SYSTEM",  # DPAPI master-key seed (machine + user halves)
    }
)


def is_printable_secret(text: str) -> bool:
    """``True`` iff ``text`` is non-empty, non-pure-whitespace, and
    every codepoint falls into the accepted Unicode major categories.

    Used as both the parser-side decode-acceptance gate and the
    type-level :class:`LsaSecretEntry` field_validator post-check, so
    a model constructed via ``LsaSecretEntry.model_validate(...)``
    from a future direct caller cannot silently bypass the printable
    contract."""
    if not text:
        return False
    if all(unicodedata.category(c)[0] == "Z" for c in text):
        return False
    return all(unicodedata.category(c)[0] in _ACCEPTED_UNICODE_CATEGORIES for c in text)


def decode_secret(hex_str: str, *, key: str | None = None) -> str | None:
    """Best-effort UTF-16LE printable rendering of ``hex_str``. Raise
    :class:`ValueError` on malformed hex (so the wrapper surfaces it
    as ``OUTPUT_PARSE_FAILED`` — a malformed Hex string is schema
    drift on a Restricted surface, not "binary bytes happened to be
    unrenderable"). Return ``None`` when the bytes decode successfully
    but the result is non-printable per :func:`is_printable_secret`,
    or when ``key`` is in :data:`BINARY_KEY_NAMES` (host-managed
    random bytes — Hex is the only meaningful representation).

    The BINARY_KEY short-circuit fires BEFORE ``bytes.fromhex``;
    callers that need malformed-hex detection on a binary-key row
    rely on the :class:`LsaSecretEntry.hex_value` regex catching
    it at the model boundary (the primary guard). The two layers
    are jointly load-bearing — do not reorder without also adding
    a parser-side hex-shape check, or schema drift on binary-key
    rows will silently return ``None`` indistinguishable from the
    legitimate binary-bytes case."""
    if key is not None and key in BINARY_KEY_NAMES:
        return None
    try:
        raw = bytes.fromhex(hex_str.replace(" ", "").replace("\n", ""))
    except ValueError as exc:
        raise ValueError(f"lsadump Hex field is not valid hex (len={len(hex_str)}): {exc}") from exc
    try:
        text = raw.decode("utf-16-le").rstrip("\x00")
    except UnicodeDecodeError as exc:
        # UnicodeDecodeError is NOT a ValueError subclass; re-raise as
        # ValueError so the wrapper's parse-failure catch surfaces it
        # uniformly as OUTPUT_PARSE_FAILED.
        raise ValueError(
            f"lsadump Hex bytes do not decode as UTF-16LE (len={len(raw)} bytes): {exc}"
        ) from exc
    return text if is_printable_secret(text) else None


__all__ = ["BINARY_KEY_NAMES", "decode_secret", "is_printable_secret"]
