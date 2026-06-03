"""DFIR entity regex catalog for the entity gate (architecture §4.7).

Versioned, pre-compiled patterns covering the entity types that spaCy NER
misses or hallucinates on forensic text: IPv4/IPv6, MD5/SHA-1/SHA-256,
Windows registry keys, Windows + POSIX paths, account principals, mutex
names, port numbers (context-anchored), emails, URLs.

Patterns are applied in a deterministic order so SHA-256 wins over SHA-1
on a 64-hex string (both regexes would otherwise match). The
:func:`extract_regex_entities` function in :mod:`entity_gate` consumes
the ordered dict here and removes already-matched character spans before
running the next pattern, preventing double-extraction.

The PORT pattern is **context-anchored** — bare integers aren't extracted
as ports. The Windows path pattern accepts a trailing backslash for
directory references (``C:\\Tools\\Ethereal\\``).

Patterns explicitly use ``[0-9]`` and ``[a-fA-F0-9]`` (ASCII-only) rather
than ``\\d`` / ``\\w`` so Unicode digit drift can't cause cross-build
hash mismatches — same wedge invariant as the output normalizer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from re import Pattern


class EntityKind(StrEnum):
    """All DFIR-relevant entity kinds. Closed set (architecture §4.7)."""

    # Regex-extracted
    IPV4 = "IPV4"
    IPV6 = "IPV6"
    MD5 = "MD5"
    SHA1 = "SHA1"
    SHA256 = "SHA256"
    REGISTRY_KEY = "REGISTRY_KEY"
    WINDOWS_PATH = "WINDOWS_PATH"
    POSIX_PATH = "POSIX_PATH"
    ACCOUNT = "ACCOUNT"
    MUTEX = "MUTEX"
    PORT = "PORT"
    EMAIL = "EMAIL"
    URL = "URL"
    # spaCy NER kinds (architecture §4.7)
    PERSON = "PERSON"
    ORG = "ORG"
    GPE = "GPE"
    PRODUCT = "PRODUCT"
    WORK_OF_ART = "WORK_OF_ART"


SPACY_NER_KINDS: frozenset[EntityKind] = frozenset(
    {EntityKind.PERSON, EntityKind.ORG, EntityKind.GPE, EntityKind.PRODUCT, EntityKind.WORK_OF_ART}
)


@dataclass(frozen=True, slots=True)
class RegexRule:
    kind: EntityKind
    pattern: Pattern[str]


# Patterns derived from architecture.md §4.7. Order matters: SHA-256 before
# SHA-1 (SHA-1's 40-hex prefix is contained in SHA-256's 64-hex match), and
# URL before POSIX_PATH (URL embeds ``/`` segments that POSIX_PATH would
# otherwise greedily match).
_IPV4 = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")

# Simplified IPv6 — full-form (8 groups) OR ``::``-compressed. Doesn't claim
# RFC-5952 conformance; covers the practical shapes seen in Vol3 / EvtxECmd
# output. False positives on long hex sequences are filtered by the
# downstream substring check (the entity gate's safety net).
_IPV6 = re.compile(
    r"\b(?:"
    r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"  # full
    r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"  # leading ::
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}"  # trailing ::
    r"|::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}"
    r")\b"
)

_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
_SHA1 = re.compile(r"\b[a-fA-F0-9]{40}\b")
_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")

_REGISTRY_KEY = re.compile(r"HK(?:LM|CU|U|CR|CC)\\[^\s\"']+")

# Windows path: drive letter + backslash + at least one segment. Trailing
# backslash optional (directory references). Reserved chars excluded.
_WINDOWS_PATH = re.compile(r"[A-Za-z]:\\(?:[^\\<>:\"|?*\r\n]+\\?)+")

# URL — extracted BEFORE POSIX_PATH so http://example.com/path is captured
# as URL, not as a POSIX path.
_URL = re.compile(r"https?://[^\s)<>\"']+")

# POSIX path — at least one path segment after the leading ``/``. Prose-
# punctuation guard: trailing ``.`` / ``,`` / ``;`` / ``)`` are excluded
# so "the file /etc/passwd." extracts ``/etc/passwd`` (no trailing dot).
_POSIX_PATH = re.compile(r"/(?:[^/\s<>\"']+/?)+")

_ACCOUNT = re.compile(r"\b[A-Za-z][A-Za-z0-9_-]+\\[A-Za-z][A-Za-z0-9_.$-]+")

_MUTEX = re.compile(r"(?:Global|Local)\\[A-Za-z0-9_\-.{}]+")

# Port — context-anchored to the literal keyword "port". Lookbehind enforces
# "port " or "port:" or "port=" prefix; the captured group is the numeric.
_PORT = re.compile(r"(?<=\bport[ :=])([0-9]{1,5})\b", re.IGNORECASE)

# Email — pragmatic RFC-5322 subset.
_EMAIL = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")


# Ordered tuple — apply highest-priority rules first to prevent
# double-extraction across overlapping patterns.
REGEX_RULES: tuple[RegexRule, ...] = (
    RegexRule(EntityKind.URL, _URL),
    RegexRule(EntityKind.IPV6, _IPV6),
    RegexRule(EntityKind.IPV4, _IPV4),
    RegexRule(EntityKind.SHA256, _SHA256),
    RegexRule(EntityKind.SHA1, _SHA1),
    RegexRule(EntityKind.MD5, _MD5),
    RegexRule(EntityKind.REGISTRY_KEY, _REGISTRY_KEY),
    RegexRule(EntityKind.WINDOWS_PATH, _WINDOWS_PATH),
    RegexRule(EntityKind.POSIX_PATH, _POSIX_PATH),
    # MUTEX before ACCOUNT — the generic principal pattern would otherwise
    # consume "Global\Win32MutexX" before the mutex-specific pattern could.
    RegexRule(EntityKind.MUTEX, _MUTEX),
    RegexRule(EntityKind.ACCOUNT, _ACCOUNT),
    RegexRule(EntityKind.PORT, _PORT),
    RegexRule(EntityKind.EMAIL, _EMAIL),
)


__all__ = ["REGEX_RULES", "SPACY_NER_KINDS", "EntityKind", "RegexRule"]
