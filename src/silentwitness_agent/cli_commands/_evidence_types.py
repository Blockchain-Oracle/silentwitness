"""Evidence type detection and I/O helpers for the register-evidence CLI command."""

from __future__ import annotations

import hashlib
from pathlib import Path

from silentwitness_common.types import EvidenceType

_SUFFIX_TYPE: dict[str, EvidenceType] = {
    ".e01": EvidenceType.DISK_IMAGE,
    ".ewf": EvidenceType.DISK_IMAGE,
    ".dd": EvidenceType.DISK_IMAGE,
    ".img": EvidenceType.DISK_IMAGE,
    ".raw": EvidenceType.DISK_IMAGE,
    ".mem": EvidenceType.MEMORY_DUMP,
    ".vmem": EvidenceType.MEMORY_DUMP,
    ".dmp": EvidenceType.MEMORY_DUMP,
    ".evtx": EvidenceType.EVTX,
    ".pcap": EvidenceType.PCAP,
    ".pcapng": EvidenceType.PCAP,
    ".hve": EvidenceType.HIVE,
    ".hiv": EvidenceType.HIVE,
}

_HIVE_NAMES: frozenset[str] = frozenset(
    {"SYSTEM", "SOFTWARE", "SAM", "SECURITY", "NTUSER.DAT", "DEFAULT", "USRCLASS.DAT"}
)


def detect_evidence_type(path: Path) -> EvidenceType:
    """Map path to EvidenceType via suffix lookup, then _HIVE_NAMES; OTHER if neither matches."""
    t = _SUFFIX_TYPE.get(path.suffix.lower())
    if t is not None:
        return t
    if path.name.upper() in _HIVE_NAMES:
        return EvidenceType.HIVE
    return EvidenceType.OTHER


def sha256_hex(path: Path) -> tuple[str, int]:
    """SHA256 hash a file in 8 KiB chunks; return (hex_digest, byte_count)."""
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def human_size(size: int) -> str:
    """Return a 1024-based human-readable size string (e.g. '4.2 GiB')."""
    f = float(size)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    for unit in units[:-1]:
        if f < 1024.0:
            return f"{f:.1f} {unit}"
        f /= 1024.0
    return f"{f:.1f} {units[-1]}"
