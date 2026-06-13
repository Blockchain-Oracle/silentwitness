"""``silentwitness prepare`` — turn registered disk images / memory archives into
extracted, tool-ready artifacts, each recorded in the evidence registry with
audit provenance.

Phase 0 of the real-evidence re-architecture. The dfVFS mechanics live in
:mod:`silentwitness_mcp.evidence.access`; this module is the wiring: filter the
registered evidence, extract artifacts from each disk image / decompress each
nested archive, emit one audit entry per source, and register every produced
file so downstream parsing/indexing (Phase 1) can reach it.

``access`` (and its dfVFS/libyal C extensions) is imported lazily — only once
there is real work — so this module and its no-op path stay importable on dev
machines without the forensic toolchain installed.
"""

from __future__ import annotations

import time
from pathlib import Path

from rich.console import Console

from silentwitness_common.types import EvidenceType
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry, EvidenceRegistryError

_PREPARED_SUBDIR = "prepared"
# Suffixes we treat as containers to unwrap (mirrors access._ARCHIVE_SUFFIXES).
_ARCHIVE_SUFFIXES = frozenset({".zip", ".7z", ".gz", ".tar", ".tgz", ".bz2", ".xz"})
# Artifact labels (from access.ROCBA_ARTIFACT_TARGETS) that are registry hives.
_HIVE_LABELS = frozenset(
    {
        "hive_software",
        "hive_system",
        "hive_sam",
        "hive_security",
        "hive_default",
        "ntuser",
        "usrclass",
        "amcache",
    }
)


def _artifact_evidence_type(label: str) -> EvidenceType:
    """Map an extracted-artifact label to its registry :class:`EvidenceType`."""
    if label == "evtx":
        return EvidenceType.EVTX
    if label in _HIVE_LABELS:
        return EvidenceType.HIVE
    return EvidenceType.OTHER  # $MFT, $UsnJrnl, SRUM, Prefetch, etc.


def run(case_dir: Path, case_id: str, *, examiner: str, no_color: bool) -> int:
    """Prepare every registered disk image + compressed archive in the case.

    Returns 0 on success, 1 if there is nothing to prepare or a forensic
    extraction fails, 2 on a registry/system error.
    """
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)
    registry = EvidenceRegistry(case_dir)
    try:
        records = registry.list_all()
    except EvidenceRegistryError as exc:
        err.print(f"[red]✗[/red] evidence registry error: {exc}", highlight=False)
        return 2

    images = [r for r in records if r.type == EvidenceType.DISK_IMAGE]
    archives = [
        r
        for r in records
        if r.type in (EvidenceType.MEMORY_DUMP, EvidenceType.OTHER)
        and r.path.suffix.lower() in _ARCHIVE_SUFFIXES
    ]
    if not images and not archives:
        err.print(
            "[yellow]⚠[/yellow] nothing to prepare: no DISK_IMAGE or compressed "
            "archive is registered (run register-evidence first)",
            highlight=False,
        )
        return 1

    # Lazy: only import the dfVFS-backed mechanics once there is real work, so
    # this module imports on machines lacking the forensic C-extension stack.
    from silentwitness_mcp.evidence import access

    workroot = case_dir / _PREPARED_SUBDIR
    audit = AuditLogger(case_dir, examiner)
    produced = 0
    try:
        for rec in images:
            t0 = time.monotonic()
            try:
                opened = access.open_image(rec.path)
                workdir = workroot / rec.path.stem
                artifacts = access.extract_artifacts(opened, workdir)
            except access.EvidenceAccessError as exc:
                err.print(f"[red]✗[/red] {rec.path.name}: {exc}", highlight=False)
                return 1
            entry = audit.emit(
                backend="cli",
                tool="prepare.extract_artifacts",
                params={"source": str(rec.path), "source_sha256": rec.sha256},
                result_summary={
                    "artifact_count": len(artifacts),
                    "labels": sorted({a.label for a in artifacts}),
                    "workdir": str(workdir),
                },
                result_sha256=rec.sha256,
                stdout_path=workdir,
                elapsed_ms=(time.monotonic() - t0) * 1000,
                model_used="cli",
            )
            for art in artifacts:
                registry.register(
                    art.output_path, _artifact_evidence_type(art.label), entry.audit_id
                )
                produced += 1
            out.print(
                f"[green]✓[/green] {rec.path.name}: extracted {len(artifacts)} artifact(s)",
                highlight=False,
            )

        for rec in archives:
            t0 = time.monotonic()
            workdir = workroot / f"{rec.path.stem}_decompressed"
            try:
                leaves = access.decompress_archive(rec.path, workdir)
            except access.EvidenceAccessError as exc:
                err.print(f"[red]✗[/red] {rec.path.name}: {exc}", highlight=False)
                return 1
            entry = audit.emit(
                backend="cli",
                tool="prepare.decompress_archive",
                params={"source": str(rec.path), "source_sha256": rec.sha256},
                result_summary={"leaf_count": len(leaves), "leaves": [str(p) for p in leaves]},
                result_sha256=rec.sha256,
                stdout_path=workdir,
                elapsed_ms=(time.monotonic() - t0) * 1000,
                model_used="cli",
            )
            for leaf in leaves:
                registry.register(leaf, EvidenceType.MEMORY_DUMP, entry.audit_id)
                produced += 1
            out.print(
                f"[green]✓[/green] {rec.path.name}: decompressed to {len(leaves)} file(s)",
                highlight=False,
            )
    except EvidenceRegistryError as exc:
        err.print(f"[red]✗[/red] registry error during prepare: {exc}", highlight=False)
        return 2
    finally:
        audit.close()

    out.print(f"[green]✓[/green] prepared {produced} artifact(s) into {workroot}", highlight=False)
    return 0
