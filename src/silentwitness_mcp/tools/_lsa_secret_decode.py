"""Shared UTF-16LE printable-acceptance and host-managed-key catalogue
for the LSA-secret tool family. Lives in a standalone module so the
pure-function helpers (acceptance band, binary-key allowlist, UTF-16LE
decode) are unit-testable in isolation from the Pydantic model
boundary — exercised directly by ``tests/unit/test_lsa_secret_decode.py``.

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
# Pre-casefolded mirror of :data:`BINARY_KEY_NAMES` for case-insensitive
# comparison. Windows registry value names are case-insensitive in the
# underlying NTRegistry semantics — comparing case-foldedly here closes
# a speculative future-bug surface where an upstream key-normalization
# step (parser refactor, Pydantic ``field_validator("key", mode="before")``)
# could cause a byte-exact ``in BINARY_KEY_NAMES`` check to silently miss.
_BINARY_KEY_NAMES_CASEFOLDED: Final = frozenset(n.casefold() for n in BINARY_KEY_NAMES)


def is_binary_key(key: str) -> bool:
    """Case-insensitive membership check against :data:`BINARY_KEY_NAMES`.
    Matches Windows registry value-name semantics and guards against
    an upstream casing-normalization regression."""
    return key.casefold() in _BINARY_KEY_NAMES_CASEFOLDED


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
    rely on the :class:`LsaSecretEntry.hex_value` shape regex AND
    :meth:`LsaSecretEntry._check_hex_byte_paired` together catching
    it at the model boundary. The two layers are jointly load-
    bearing — do not reorder without also adding a parser-side
    hex-shape check, or schema drift on binary-key rows will
    silently return ``None`` indistinguishable from the legitimate
    binary-bytes case."""
    # `None in frozenset({...})` is False; the helper accepts str only,
    # so a bare `if key and is_binary_key(key)` is equivalent — keep the
    # explicit `is not None` for legibility on a credential-material path.
    if key is not None and is_binary_key(key):
        return None
    try:
        raw = bytes.fromhex("".join(hex_str.split()))
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


__all__ = ["BINARY_KEY_NAMES", "decode_secret", "is_binary_key", "is_printable_secret"]
