#!/usr/bin/env python3
"""Compatibility driver for official Find Evil starter-case downloads.

The share at https://sansorg.egnyte.com/fl/HhH7crTYT4JK holds three cases:
"Standard Forensic Case" (ROCBA / Mr. Evil — single host), "Standard Forensics
Case 2", and "Compromised APT Attack Scenarios" (multi-host APT). No Egnyte
account needed.

Prefer the packaged CLI:

Usage::

    silentwitness starter-cases catalog
    silentwitness starter-cases catalog "Standard Forensic Case"
    silentwitness starter-cases download "Standard Forensic Case" /tmp/rocba
    silentwitness starter-cases download "Standard Forensic Case" /tmp/rocba --dry-run

This script remains for older automation. Its preferred verbs mirror the CLI:

    python scripts/download_starter_cases.py catalog
    python scripts/download_starter_cases.py download "Standard Forensic Case" /tmp/rocba
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from egnyte_share import (
    human_size,
    list_contents,
    open_session,
    resolve_case_root,
    stream_file,
    verify_sidecar,
    walk,
)


def cmd_catalog(args: argparse.Namespace) -> int:
    client = open_session()
    try:
        root = resolve_case_root(client, args.case)
        print(f"# {root}")
        if args.case is None:
            for sub in list_contents(client, root):
                if sub.type != "folder":
                    continue
                sub_size = 0
                sub_files = 0
                for f in walk(client, sub.path):
                    sub_size += f.size or 0
                    sub_files += 1
                print(f"  {sub.name}: {sub_files} files, {human_size(sub_size)}")
            return 0
        total_size = 0
        file_count = 0
        for f in walk(client, root):
            total_size += f.size or 0
            file_count += 1
            print(f"  {human_size(f.size):>10}  {f.path}")
        print(f"# Total: {file_count} files, {human_size(total_size)}")
        return 0
    finally:
        client.close()


def cmd_download(args: argparse.Namespace) -> int:
    client = open_session()
    try:
        root = resolve_case_root(client, args.case)
        target_root = Path(args.target).resolve()
        target_root.mkdir(parents=True, exist_ok=True)
        print(f"# downloading {root} → {target_root}")
        total_size = 0
        file_count = 0
        for f in walk(client, root):
            rel = f.path[len(root) :].lstrip("/")
            target = target_root / rel
            if args.dry_run:
                print(f"  DRY  {human_size(f.size):>10}  {target}")
                total_size += f.size or 0
                file_count += 1
                continue
            if target.exists() and f.size is not None and target.stat().st_size == f.size:
                if verify_sidecar(target):
                    print(f"  SKIP {human_size(f.size):>10}  {target}  (sha256 verified)")
                    total_size += f.size or 0
                    file_count += 1
                    continue
                # Size matches but sidecar disagrees — silent corruption.
                # Treat as not-present and re-download.
                print(
                    f"  REDO {human_size(f.size):>10}  {target}  (sha256 mismatch)",
                    file=sys.stderr,
                )
                target.unlink()
            digest = stream_file(client, f, target)
            print(f"  OK   {human_size(f.size):>10}  {target}  sha256={digest[:12]}…")
            total_size += f.size or 0
            file_count += 1
        print(f"# Done: {file_count} files, {human_size(total_size)}")
        return 0
    finally:
        client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download SANS Find Evil! 2026 starter cases from the Egnyte public share.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_catalog = sub.add_parser("catalog", help="enumerate cases or files in a case")
    p_catalog.add_argument(
        "case",
        nargs="?",
        default=None,
        help="case folder name (omit to summarise all cases at the root)",
    )
    p_catalog.set_defaults(func=cmd_catalog)

    p_dl = sub.add_parser("download", help="download a case to a local directory")
    p_dl.add_argument("case", help="case folder name (e.g. 'Standard Forensic Case')")
    p_dl.add_argument(
        "target",
        help="target directory — created if missing; existing files with matching "
        "size + verified SHA256 sidecar are skipped (idempotent + resumable via HTTP Range)",
    )
    p_dl.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be downloaded without making any GET requests",
    )
    p_dl.set_defaults(func=cmd_download)

    args = parser.parse_args(argv)
    return cast(int, args.func(args))


if __name__ == "__main__":
    # Make scripts/ importable so `from egnyte_share import …` works when the
    # CLI is invoked directly (without `uv run -m`).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
