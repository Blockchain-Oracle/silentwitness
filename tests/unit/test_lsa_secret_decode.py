"""Unit tests for the LSA-secret decoder helpers + LsaSecretEntry
model-boundary contracts. Split out of ``test_vol_lsadump.py`` to
keep both files under the 400-LOC CI budget while letting each focus
on a single review surface (wrapper-level integration vs. typed-model
+ helper invariants)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from silentwitness_mcp.tools._lsa_models import LsaSecretEntry
from silentwitness_mcp.tools._lsa_secret_decode import (
    BINARY_KEY_NAMES,
    decode_secret,
    is_printable_secret,
)


def _utf16le_hex(text: str) -> str:
    """Encode ``text`` as UTF-16LE bytes + null-terminator, hex-encoded
    (the shape Vol3's lsadump renderer emits in the ``Hex`` field)."""
    return (text.encode("utf-16-le") + b"\x00\x00").hex()


# ---------------------------------------------------------------------------
# is_printable_secret — acceptance-band branch coverage
# ---------------------------------------------------------------------------


def test_is_printable_secret_rejects_empty_string() -> None:
    assert is_printable_secret("") is False


def test_is_printable_secret_rejects_pure_whitespace() -> None:
    """Pure-whitespace 'secrets' are implausible enough that the case
    more likely reflects a scrubbed/poisoned LSA slot. Fail closed —
    an analyst seeing secret='   ' cannot tell padding from artefact."""
    assert is_printable_secret(" ") is False
    assert is_printable_secret("   ") is False
    # NBSP (U+00A0) is Zs — pin the non-ASCII Z-class branch.
    assert is_printable_secret("  ") is False


def test_is_printable_secret_accepts_ascii_with_internal_whitespace() -> None:
    """Whitespace EMBEDDED in an otherwise-printable string is fine —
    only pure-whitespace is rejected."""
    assert is_printable_secret("hello world") is True


def test_is_printable_secret_rejects_control_chars() -> None:
    assert is_printable_secret("Hi\x01") is False


# ---------------------------------------------------------------------------
# decode_secret — error-paths and branch coverage
# ---------------------------------------------------------------------------


def test_decode_secret_raises_on_malformed_hex() -> None:
    """Malformed Hex is schema drift, not "binary bytes happened to
    be unrenderable". Must raise ValueError so the wrapper surfaces
    OUTPUT_PARSE_FAILED rather than a silent secret=None."""
    with pytest.raises(ValueError, match="not valid hex"):
        decode_secret("zz-totally-not-hex")


def test_decode_secret_returns_none_for_non_printable_bytes() -> None:
    """Random binary that decodes to control chars → secret=None
    (the legitimate non-printable path, distinct from schema drift)."""
    # 0x01 0x00 0x02 0x00 → U+0001 U+0002 (both Cc).
    assert decode_secret("01000200") is None


def test_decode_secret_returns_none_for_binary_key_names() -> None:
    """The host-managed-key allowlist short-circuits decode for keys
    whose values are by-design random bytes — even when the bytes
    happen to land in the printable Unicode band, the rendering is
    operationally meaningless."""
    # "AB" UTF-16LE = 4100 4200 → U+0041 U+0042 → "AB" (printable),
    # but NL$KM is in BINARY_KEY_NAMES so we still get None.
    printable_hex = _utf16le_hex("AB")
    for key in BINARY_KEY_NAMES:
        assert decode_secret(printable_hex, key=key) is None
    # Without the key= guard, the same bytes decode normally.
    assert decode_secret(printable_hex) == "AB"


def test_decode_secret_returns_none_for_empty_after_null_strip() -> None:
    """Two NUL bytes → empty string after rstrip-NUL → None
    (the "no rendering exists" case, distinct from schema drift)."""
    assert decode_secret("0000") is None


# ---------------------------------------------------------------------------
# LsaSecretEntry — model-boundary defense-in-depth
# ---------------------------------------------------------------------------


def test_lsasecretentry_field_validator_blocks_direct_unprintable_construction() -> None:
    """A future caller invoking LsaSecretEntry.model_validate(...)
    directly with a non-printable secret string MUST fail — the
    field_validator closes the printable contract at the model
    boundary, not only at the parser."""
    with pytest.raises(ValidationError):
        LsaSecretEntry.model_validate(
            {
                "Key": "_SC_MSSQLServer",
                "Hex": "0123abcd",  # pragma: allowlist secret
                "Secret": "Hi\x01",  # pragma: allowlist secret
            }
        )


def test_lsasecretentry_rejects_empty_hex() -> None:
    """min_length=1 on Hex — empty hex is silent-empty-string drift."""
    with pytest.raises(ValidationError):
        LsaSecretEntry.model_validate({"Key": "_SC_MSSQLServer", "Hex": ""})


def test_lsasecretentry_rejects_non_hex_pattern() -> None:
    """The Hex regex catches non-hex strings at the model boundary,
    even if the parser is bypassed."""
    with pytest.raises(ValidationError):
        LsaSecretEntry.model_validate({"Key": "_SC_MSSQLServer", "Hex": "definitely-not-hex"})


def test_lsasecretentry_rejects_whitespace_only_hex() -> None:
    """Regex starts with ``[0-9a-fA-F]`` (require at least one hex
    digit) to forbid the whitespace-only case — would otherwise
    produce a silent empty-decode."""
    with pytest.raises(ValidationError):
        LsaSecretEntry.model_validate({"Key": "_SC_MSSQLServer", "Hex": "   "})


def test_lsasecretentry_rejects_odd_length_hex() -> None:
    """Hex is byte-paired; odd length after whitespace strip is
    schema drift. The hex_value field_validator catches it cleanly."""
    with pytest.raises(ValidationError):
        LsaSecretEntry.model_validate({"Key": "_SC_MSSQLServer", "Hex": "deadb"})


def test_lsasecretentry_rejects_empty_key() -> None:
    """min_length=1 on key — a zero-length Key is never legitimate."""
    with pytest.raises(ValidationError):
        LsaSecretEntry.model_validate({"Key": "", "Hex": "0123abcd"})


def test_lsasecretentry_binary_key_forces_secret_none_at_model_boundary() -> None:
    """BINARY_KEY allowlist must hold at the model boundary, not only
    in the parser. A direct ``model_validate`` from a future caller
    MUST not surface a "decrypted" rendering of an NTLM hash / DPAPI
    seed / NL$KM AES key — even if the bytes incidentally decoded to
    a printable Unicode glyph."""
    for binary_key in BINARY_KEY_NAMES:
        with pytest.raises(ValidationError):
            LsaSecretEntry.model_validate({"Key": binary_key, "Hex": "61006200", "Secret": "ab"})


def test_decode_secret_raises_on_truncated_utf16le() -> None:
    """UnicodeDecodeError branch coverage — a 1-byte hex is too short
    to be a valid UTF-16LE codepoint and surfaces as ValueError."""
    with pytest.raises(ValueError, match=r"not valid hex|UTF-16LE"):
        decode_secret("ab")


def test_decode_secret_raises_on_lone_high_surrogate() -> None:
    """Lone surrogate halves fail UTF-16LE decode in strict mode (the
    default) and surface as ValueError → OUTPUT_PARSE_FAILED. This is
    stricter than the Cs-category check but more honest about the
    underlying byte stream being malformed."""
    # 0x00 0xD8 → U+D800 lone high surrogate; strict decode rejects.
    with pytest.raises(ValueError, match="UTF-16LE"):
        decode_secret("00d8")


def test_decode_secret_handles_hex_with_internal_whitespace() -> None:
    """Vol3 may wrap long Hex blobs with whitespace. The strip-then-
    fromhex path must round-trip transparently."""
    assert decode_secret("48 00 69 00") == "Hi"
