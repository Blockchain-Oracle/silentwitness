"""HMAC-signed approval ledger (architecture §4.9 + ADR-007).

Every examiner-approved Finding / Observation / Interpretation / timeline
event is recorded as one line of ``/var/lib/silentwitness/verification/<case_id>.jsonl``
with an HMAC-SHA256 over the **substantive content bytes** the caller
supplies (composed via :class:`LedgerComposer` for §4.9-prescribed shapes),
keyed by a PBKDF2-SHA256 derived key (600,000 iterations — OWASP 2023 floor,
Valhuntir's choice). The password never persists; only the derived key is
held in process memory and zeroed on completion.

Layered defences:

* PBKDF2-SHA256 600K iterations — each forgery attempt costs ~100ms even
  after the ledger file is exfiltrated.
* Per-case salt — blast radius containment.
* HMAC is over the live ``content_bytes``, not over a metadata triple —
  any single-byte change to the substantive bytes invalidates verification.
  ``content_hash = sha256(content_bytes)`` is stored alongside so upstream
  callers can independently compare against a live artefact.
* :func:`hmac.compare_digest` constant-time compare on every verify.
* Directory mode ``0o700`` + file mode ``0o600`` — only the analyst owner
  can read. Refuses-to-proceed if the dir grants ANY group/other access
  (mode & 0o077 != 0) — strictly stronger postures (setgid+0o700) pass.
* ``fsync`` on every append via :func:`silentwitness_common.atomic_io.append_jsonl_line`.
* Stdlib only (ADR-007).

:class:`LedgerComposer` exposes architecture §4.9 verbatim composition
rules (observation = text|sorted(audit_ids), interpretation =
obs_id|text|conf, finding = obs_bytes\\x00interp_bytes) so the signer
(Epic 4 ``approve_finding`` tool) and the verifier (Epic 12 CLI
``silentwitness verify``) compose IDENTICAL bytes. Composer functions
reject fields containing the separator chars for their specific position
(``|`` / ``\\x00`` in text fields, plus ``,`` in comma-joined audit IDs) so
two semantically distinct inputs cannot collapse to the same canonical
bytes.

Honest limitation: Python ``str`` is immutable and interned, so the
*password* itself cannot be zeroed from process memory once received. The
*derived key* CAN be zeroed if held as :class:`bytearray` — :func:`zero_key`
does this best-effort and raises ``TypeError`` on non-bytearray inputs.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import stat
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from silentwitness_common.atomic_io import append_jsonl_line
from silentwitness_common.types import Confidence, LedgerEntry, LedgerItemType

_PBKDF2_MIN_ITERATIONS: Final = 600_000
_DERIVED_KEY_BYTES: Final = 32
_LEDGER_DIR_MODE: Final = 0o700
_LEDGER_FILE_MODE: Final = 0o600
_PRF: Final = "sha256"
_FIELD_FORBIDDEN: Final = frozenset({"\x00", "|"})
_AUDIT_ID_FORBIDDEN: Final = frozenset({"\x00", "|", ","})


class LedgerError(Exception):
    """Base for every ledger-raised error so callers can ``except LedgerError``."""


class LedgerKeyError(LedgerError, ValueError):
    """Raised when key derivation parameters violate the architectural floor."""


class LedgerSecurityError(LedgerError, PermissionError):
    """Raised when the on-disk security posture (mode bits) is too weak."""


class LedgerCorruptionError(LedgerError, ValueError):
    """Raised when on-disk ledger content is corrupt (malformed / blank line).

    Distinct from :class:`LedgerSecurityError` so the two failure modes map
    to different runbooks: "compromised host" vs "crash mid-fsync, decide
    truncate-and-continue or fail the case."
    """


class LedgerCompositionError(LedgerError, ValueError):
    """Raised when a composer input contains a separator char.

    Architecture §4.9's stringly-typed separators are collision-prone if a
    field contains the separator. The composer rejects such inputs rather
    than producing canonical bytes that map back to two semantically
    distinct (text, audit_ids) tuples — the wedge depends on injectivity.
    """


# ---------------------------------------------------------------------------
# Composition rules — architecture §4.9 verbatim, separator-collision-safe
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ObservationParts:
    """Substantive bytes of an observation: text + sorted audit_ids."""

    text: str
    audit_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InterpretationParts:
    """Substantive bytes of an interpretation: obs_id + text + confidence."""

    observation_id: str
    text: str
    confidence: Confidence


def _check_no_separator(
    value: str,
    field_name: str,
    *,
    forbidden_chars: frozenset[str] = _FIELD_FORBIDDEN,
) -> None:
    forbidden = forbidden_chars & set(value)
    if forbidden:
        codes = ", ".join(f"\\u{ord(c):04x}" for c in sorted(forbidden))
        raise LedgerCompositionError(
            f"{field_name!r} contains separator char(s) {codes} — refusing to "
            "compose canonical bytes that would collide with a distinct input"
        )


class LedgerComposer:
    """Reproduce the substantive bytes a signer/verifier hashes.

    Both signer (Epic 4 ``approve_finding``) and verifier (Epic 12 CLI
    ``silentwitness verify``) call these to produce IDENTICAL bytes. Drift
    is impossible if both sides import the same function. Text fields reject
    ``|`` and NUL. Audit IDs additionally reject ``,`` because the IDs are
    comma-joined. Commas in evidence prose are safe because they are not field
    delimiters.
    """

    @staticmethod
    def observation(parts: ObservationParts) -> bytes:
        """``text + "|" + sorted(audit_ids).join(",")`` per architecture §4.9."""
        _check_no_separator(parts.text, "ObservationParts.text")
        for aid in parts.audit_ids:
            _check_no_separator(
                aid,
                "ObservationParts.audit_ids[]",
                forbidden_chars=_AUDIT_ID_FORBIDDEN,
            )
        joined = ",".join(sorted(parts.audit_ids))
        return f"{parts.text}|{joined}".encode()

    @staticmethod
    def interpretation(parts: InterpretationParts) -> bytes:
        """``observation_id + "|" + text + "|" + confidence.value`` per architecture §4.9."""
        _check_no_separator(parts.observation_id, "InterpretationParts.observation_id")
        _check_no_separator(parts.text, "InterpretationParts.text")
        return f"{parts.observation_id}|{parts.text}|{parts.confidence.value}".encode()

    @staticmethod
    def finding(observation: ObservationParts, interpretation: InterpretationParts) -> bytes:
        """``observation_bytes + b"\\x00" + interpretation_bytes`` per architecture §4.9."""
        return (
            LedgerComposer.observation(observation)
            + b"\x00"
            + LedgerComposer.interpretation(interpretation)
        )


# ---------------------------------------------------------------------------
# HMACLedger — the gate
# ---------------------------------------------------------------------------


class HMACLedger:
    """Per-case append-only HMAC-signed approval ledger.

    Construction enforces the on-disk security posture (dir mode rejects
    any group/other access). The crypto primitives
    (:meth:`derive_key` / :meth:`compute_hmac` / :meth:`verify_hmac` /
    :meth:`zero_key`) are static methods; the per-case I/O operations
    (:meth:`append` / :meth:`read_all` / :meth:`verify_entry`) are instance
    methods bound to one ``ledger_dir`` + ``case_id``.
    """

    def __init__(self, ledger_dir: Path, case_id: str) -> None:
        if not case_id:
            raise ValueError("case_id must be non-empty")
        self._ledger_dir = ledger_dir
        self._case_id = case_id
        self._ledger_path = ledger_dir / f"{case_id}.jsonl"
        self._ensure_dir_mode()

    @property
    def ledger_dir(self) -> Path:
        return self._ledger_dir

    @property
    def ledger_path(self) -> Path:
        return self._ledger_path

    # ------------------------------------------------------------------ Crypto
    @staticmethod
    def derive_key(password: str, salt: bytes, iterations: int = _PBKDF2_MIN_ITERATIONS) -> bytes:
        """PBKDF2-SHA256, ``iterations`` rounds (≥ OWASP 600K floor), 32-byte output.

        ``iterations`` < 600,000 raises :class:`LedgerKeyError` — never tunable.
        """
        if iterations < _PBKDF2_MIN_ITERATIONS:
            raise LedgerKeyError(
                f"iterations={iterations} below OWASP minimum {_PBKDF2_MIN_ITERATIONS} "
                "— architecture §4.9 floor is non-negotiable"
            )
        if not isinstance(password, str):
            raise TypeError("password must be str (caller is responsible for zeroing)")
        if not isinstance(salt, bytes | bytearray):
            raise TypeError("salt must be bytes")
        return hashlib.pbkdf2_hmac(
            _PRF, password.encode(), bytes(salt), iterations, dklen=_DERIVED_KEY_BYTES
        )

    @staticmethod
    def compute_hmac(key: bytes, message: bytes) -> str:
        """HMAC-SHA256 of ``message`` keyed by ``key``; returns lowercase hex."""
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    @staticmethod
    def verify_hmac(key: bytes, message: bytes, expected_hex: str) -> bool:
        """Constant-time HMAC verify via :func:`hmac.compare_digest`. Hex inputs
        are normalised to lowercase so an uppercase ``expected_hex`` (which
        ``compute_hmac`` never produces) is still compared correctly."""
        actual_hex = HMACLedger.compute_hmac(key, message)
        return hmac.compare_digest(actual_hex, expected_hex.lower())

    @staticmethod
    def zero_key(key_buf: bytearray) -> None:
        """Best-effort overwrite of a derived-key buffer in place with ``\\x00``.

        Raises ``TypeError`` on non-bytearray inputs (silent-failure-hunter
        H6 — caller passing ``bytes`` would silently no-op the security
        intent). Caller must wrap the key in ``bytearray(key)`` if zero-
        after-use matters. Honest limitation: Python may have copied the
        buffer to swap / page cache before this runs — best-effort, not a
        guarantee against a kernel-level attacker.
        """
        if not isinstance(key_buf, bytearray):
            raise TypeError(
                f"zero_key requires bytearray (mutable); got {type(key_buf).__name__} — "
                "wrap with bytearray(key) at the call site"
            )
        for i in range(len(key_buf)):
            key_buf[i] = 0

    # ------------------------------------------------------------------ Append
    def append(
        self,
        key: bytes,
        item_id: str,
        item_type: LedgerItemType,
        content_bytes: bytes,
        examiner: str,
        *,
        now: datetime | None = None,
    ) -> LedgerEntry:
        """HMAC ``content_bytes``, hash them, append one JSONL line.

        The HMAC is over the substantive ``content_bytes`` the caller
        supplies (architecture §4.9; for §4.9-prescribed shapes use
        :class:`LedgerComposer` to produce these bytes). ``content_hash``
        is ``sha256(content_bytes)`` so upstream callers can independently
        verify the live artefact matches what was approved.
        """
        ts = now if now is not None else datetime.now(UTC)
        hmac_hex = self.compute_hmac(key, content_bytes)
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        entry = LedgerEntry(
            ts=ts,
            item_id=item_id,
            item_type=item_type,
            content_hash=content_hash,
            hmac=hmac_hex,
            examiner=examiner,
        )
        append_jsonl_line(self._ledger_path, entry.model_dump_json(), mode=_LEDGER_FILE_MODE)
        return entry

    def read_all(self) -> list[LedgerEntry]:
        """Parse every JSONL line into a :class:`LedgerEntry`. Empty if no ledger yet.

        Blank lines and malformed JSON BOTH raise
        :class:`LedgerCorruptionError` — a tamper-evident, fsync'd, append-
        only ledger has no legitimate blank line. Silently skipping would
        let an attacker selectively erase entries by overwriting them with
        whitespace.
        """
        if not self._ledger_path.exists():
            return []
        entries: list[LedgerEntry] = []
        with self._ledger_path.open("r", encoding="utf-8") as fh:
            for idx, raw in enumerate(fh):
                line = raw.rstrip("\n")
                if not line:
                    raise LedgerCorruptionError(
                        f"ledger {self._ledger_path} line #{idx} is blank — "
                        "tamper-evident ledger must not contain blank lines"
                    )
                try:
                    entries.append(LedgerEntry.model_validate_json(line))
                except ValueError as exc:
                    truncated = line[:200] + ("..." if len(line) > 200 else "")
                    raise LedgerCorruptionError(
                        f"ledger {self._ledger_path} line #{idx} malformed: {exc}\n"
                        f"  raw bytes: {truncated!r}"
                    ) from exc
        return entries

    def verify_entry(self, key: bytes, entry: LedgerEntry, content_bytes: bytes) -> bool:
        """Verify ``entry.hmac`` against HMAC(``key``, ``content_bytes``).

        The caller passes the same substantive bytes used at sign time
        (typically re-composed with :class:`LedgerComposer`). First check:
        ``sha256(content_bytes) == entry.content_hash`` — if the caller
        passed the WRONG bytes, return False rather than silently relying
        on the HMAC comparison alone. Then constant-time HMAC compare.
        """
        if hashlib.sha256(content_bytes).hexdigest() != entry.content_hash:
            return False
        return self.verify_hmac(key, content_bytes, entry.hmac)

    # ------------------------------------------------------------------ Internals
    def _ensure_dir_mode(self) -> None:
        """Create ``ledger_dir`` mode 0o700 if absent; refuse if any group/other
        access is granted on an existing dir.

        Uses ``mode & 0o077 == 0`` rather than exact 0o700 equality so
        strictly stronger postures pass (setgid + 0o700 is a legitimate
        forensic-workstation setup; exact-equality would falsely reject).
        macOS umask 022 masks ``os.makedirs(mode=0o700)`` down to 0o755 —
        the explicit chmod after makedirs is belt-and-suspenders.
        """
        if self._ledger_dir.exists():
            mode = os.stat(self._ledger_dir).st_mode
            if mode & 0o077:
                raise LedgerSecurityError(
                    f"ledger_dir {self._ledger_dir} grants group/other access "
                    f"(mode 0o{stat.S_IMODE(mode):o}) — refusing to operate"
                )
            return
        os.makedirs(self._ledger_dir, mode=_LEDGER_DIR_MODE)
        os.chmod(self._ledger_dir, _LEDGER_DIR_MODE)


@contextmanager
def _silence(_: object) -> Generator[None, None, None]:
    """Module-level no-op for symmetry with future per-call locking."""
    yield


__all__ = [
    "HMACLedger",
    "InterpretationParts",
    "LedgerComposer",
    "LedgerCompositionError",
    "LedgerCorruptionError",
    "LedgerError",
    "LedgerKeyError",
    "LedgerSecurityError",
    "ObservationParts",
]
