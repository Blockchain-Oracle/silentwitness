"""Dataset manifest verifier — Epic 14 accuracy harness.

Usage:
  uv run python harness/datasets/verify_manifest.py [--stub-only] [--strict] [--manifest <path>]

Reads every *.manifest.json under harness/datasets/ (or the single path given by
--manifest), computes SHA256 of each file listed in evidence_files that exists on
disk, and prints a rich table comparing expected vs actual hashes.

Note: size_bytes in manifests is informational only and is NOT checked at runtime;
the only integrity check is SHA256.

All output (table and result lines) is written to stdout via Rich Console.

Exit codes:
  0 — all present, pinned files match their SHA256
  1 — at least one SHA256 mismatch, parse error, or no manifest files found
  2 — --strict and at least one evidence file is missing from disk
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Allow direct execution as `python harness/datasets/verify_manifest.py` without
# installing the harness package — the repo root (two levels up) must be on sys.path
# for `from harness.datasets.schema import ...` to resolve.
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pydantic import ValidationError  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

from harness.datasets.schema import DatasetManifest  # noqa: E402

_MANIFEST_DIR = Path(__file__).resolve().parent
_CHUNK = 8192
_PLACEHOLDERS = frozenset({"<computed-on-fetch>", "<filled-by-epic-15>"})


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _verify_one(
    manifest_path: Path,
    *,
    strict: bool,
    table: Table,
) -> tuple[int, int]:
    """Verify one manifest. Returns (mismatch_count, missing_count)."""
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        manifest = DatasetManifest.model_validate(json.loads(raw))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        table.add_row(
            manifest_path.name,
            "—",
            "—",
            "—",
            f"[red]parse error: {str(exc)[:60]}[/red]",
        )
        return 1, 0

    base_dir = manifest_path.parent

    mismatches = 0
    missing = 0
    for ef in manifest.evidence_files:
        file_path = base_dir / ef.relative_path

        if not file_path.exists():
            missing += 1
            table.add_row(
                manifest.dataset_id,
                ef.relative_path,
                "[yellow]unpinned[/yellow]" if ef.sha256 in _PLACEHOLDERS else ef.sha256[:16] + "…",
                "[yellow]—[/yellow]",
                "[yellow]missing (skipped)[/yellow]",
            )
            continue

        if ef.sha256 in _PLACEHOLDERS:
            table.add_row(
                manifest.dataset_id,
                ef.relative_path,
                "[yellow]unpinned[/yellow]",
                "[yellow]—[/yellow]",
                "[yellow]placeholder — run recompute_manifest.py[/yellow]",
            )
            continue

        try:
            actual = _sha256_file(file_path)
        except OSError as exc:
            mismatches += 1
            table.add_row(
                manifest.dataset_id,
                ef.relative_path,
                ef.sha256[:16] + "…",
                "[red]READ ERROR[/red]",
                f"[red]io error: {exc}[/red]",
            )
            continue

        match = actual == ef.sha256
        if not match:
            mismatches += 1
        table.add_row(
            manifest.dataset_id,
            ef.relative_path,
            ef.sha256[:16] + "…",
            actual[:16] + "…",
            "[green]match=True[/green]" if match else "[red]match=False (sha256 mismatch)[/red]",
        )

    return mismatches, missing


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify dataset manifest hashes.")
    parser.add_argument("--stub-only", action="store_true", help="Only verify -stub manifests.")
    parser.add_argument("--strict", action="store_true", help="Exit 2 if evidence files missing.")
    parser.add_argument("--manifest", type=Path, help="Verify a single manifest file.")
    args = parser.parse_args(argv[1:])

    if args.manifest:
        manifest_paths = [args.manifest]
    else:
        manifest_paths = sorted(_MANIFEST_DIR.glob("*.manifest.json"))

    if args.stub_only:
        manifest_paths = [p for p in manifest_paths if "-stub" in p.name]

    console = Console()
    table = Table("dataset_id", "file", "expected (16…)", "actual (16…)", "result")

    if not manifest_paths:
        console.print(
            "[yellow]⚠[/yellow] no manifest files found"
            + (" matching --stub-only filter" if args.stub_only else ""),
            highlight=False,
        )
        return 1

    total_mismatches = 0
    total_missing = 0
    for mp in manifest_paths:
        mismatches, missing = _verify_one(mp, strict=args.strict, table=table)
        total_mismatches += mismatches
        total_missing += missing

    console.print(table)

    if total_mismatches > 0:
        console.print(f"[red]✗[/red] {total_mismatches} sha256 mismatch(es)", highlight=False)
        return 1
    if args.strict and total_missing > 0:
        console.print(
            f"[red]✗[/red] {total_missing} evidence file(s) missing (--strict)",
            highlight=False,
        )
        return 2
    console.print("[green]✓[/green] all present files match their pinned sha256", highlight=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
