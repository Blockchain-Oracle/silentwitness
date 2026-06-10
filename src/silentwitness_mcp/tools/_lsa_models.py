"""Typed models for the Vol3 LSA-secret family.

Split out of :mod:`_memory_models` because the LsaSecretEntry contract
(field_validator on the printable-Unicode invariant, ``hex_value``
regex, host-managed-key allowlist) is the densest in the memory
family and warrants its own review boundary alongside the rest of the
credential-material code path (see :mod:`memory_extras` and
:mod:`_lsa_secret_decode`).

The standard ``_ROW_CONFIG`` / ``_OUT_CONFIG`` configs are re-used so
schema-drift behaviour matches the sibling models in
:mod:`_memory_models`."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from silentwitness_mcp.tools._lsa_secret_decode import is_printable_secret

_ROW_CONFIG = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)
_OUT_CONFIG = ConfigDict(frozen=True, extra="forbid")


class LsaSecretEntry(BaseModel):
    """Vol3 ``windows.registry.lsadump`` row — one decrypted LSA secret.

    The Python attribute API is snake_case (matching ``PslistEntry`` /
    ``NetscanEntry`` / ``HandleEntry`` family); the Vol3 wire-schema
    PascalCase names live only as ``alias=`` declarations. Consumers
    that access ``entry.hex_value`` are decoupled from Vol3 renderer
    naming.

    ``hex_value`` is the authoritative byte stream (verbatim hex-
    encoded output from Vol3). ``secret`` is a best-effort UTF-16LE
    printable rendering — convenience only; the entity gate cites
    ``hex_value``. ``secret`` is ``None`` when the bytes are
    non-printable, when the key is in
    :data:`_lsa_secret_decode.BINARY_KEY_NAMES`, or when the rendering
    would be all-whitespace. The invariant ``secret is not None means
    "we showed a printable rendering" and never "we silently mangled
    bytes"`` is enforced both at the parser (which calls
    :func:`decode_secret`) AND at the model boundary via
    :meth:`_check_secret_printable_contract`, so a future caller
    invoking ``LsaSecretEntry.model_validate(...)`` directly cannot
    bypass the contract.

    No cross-field ``key``/``secret`` invariant by design — Vol3's
    threat model includes implants tampering with hive contents, and
    forcing a tampered row to be un-representable would defeat the
    tool's purpose. The caveat layer flags the surprise; the type
    permits it. (Same rationale as :class:`HandleEntry` keeping
    ``type`` an open ``str`` over the kernel ``ObTypeIndexTable``
    namespace, and :class:`CmdlineEntry` keeping ``args`` an opaque
    ``str | None``.)

    ``model_construct`` bypasses validators — never use it on this
    type. The parser is the only sanctioned construction site."""

    model_config = _ROW_CONFIG

    # min_length=1: a zero-length key is never legitimate (Vol3 never
    # emits one); guards the silent-empty-string failure mode.
    key: str = Field(alias="Key", min_length=1)
    # pattern: hex digits with optional internal whitespace (Vol3 may
    # wrap long blobs); min_length=1 guards the silent-empty-hex case.
    # Forcing the shape here disambiguates "binary bytes, non-printable"
    # (legitimate, surfaces secret=None) from "schema drift / malformed
    # Hex" (forces OUTPUT_PARSE_FAILED at the model boundary).
    hex_value: str = Field(
        alias="Hex",
        min_length=1,
        pattern=r"^[0-9a-fA-F\s]+$",
    )
    secret: str | None = Field(default=None, alias="Secret")

    @field_validator("secret", mode="after")
    @classmethod
    def _check_secret_printable_contract(cls, value: str | None) -> str | None:
        """Type-level enforcement of the printable-Unicode invariant.
        The parser already short-circuits malformed hex to ``None``,
        but a direct ``model_validate`` call from a future caller
        could otherwise supply a non-printable string. Fail closed."""
        if value is not None and not is_printable_secret(value):
            raise ValueError(
                "LsaSecretEntry.secret must be a printable Unicode string "
                "or None; see _lsa_secret_decode.is_printable_secret"
            )
        return value


class LsaDumpOutput(BaseModel):
    model_config = _OUT_CONFIG
    entries: tuple[LsaSecretEntry, ...]


__all__ = ["LsaDumpOutput", "LsaSecretEntry"]
