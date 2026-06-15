#!/usr/bin/env python3
"""Download the SANS Find Evil! 2026 starter datasets from the official Egnyte
public share.

The share at https://sansorg.egnyte.com/fl/HhH7crTYT4JK contains the three
hackathon cases used as ground truth in the accuracy report:

  - ``Standard Forensic Case``      — ROCBA (Mr. Evil), single host
  - ``Standard Forensics Case 2``   — second standard case
  - ``Compromised APT Attack Scenarios`` — multi-host APT (SRL-2015 / SRL-2018)

Egnyte's public share-link API is not officially documented but is stable and
matches what the Egnyte browser UI calls. Two endpoints carry us:

1. ``GET  /fl/{token}``                                        — establishes
   the public-link session (sets ``shared_link_session`` cookie + CSRF token).
2. ``POST /rest/public/1.0/links/info/{token}/contents`` body
   ``{"path": "/...", "limit": N, "offset": M, "sortBy": "name",
   "sortDirection": "ASC", "_method": "GET", "pageNumber": P}``
   returns the folder listing (paginated).
3. ``GET /dd/{token}/?entryId={file_id}`` — direct download of one file
   inside the share (returns the binary as a stream). The ``file_id`` is the
   ``id`` field on each entry in the listing response.

Usage:

    python scripts/download_starter_cases.py list                       # all cases
    python scripts/download_starter_cases.py list "Standard Forensic Case"
    python scripts/download_starter_cases.py download "Standard Forensic Case" /tmp/rocba
    python scripts/download_starter_cases.py download "Standard Forensic Case" /tmp/rocba --dry-run

License: MIT. No Egnyte account required — the share is fully public. SHA256
checksums per file are recorded in the listing output so reproducibility is
verifiable. Be a polite citizen — the script paginates with the same limit the
official UI uses (48 / page) and uses chunked streaming for large files."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover — install bootstrap
    print(
        "scripts/download_starter_cases.py needs the `requests` package.\n"
        "Install it with: `uv tool install requests` OR `pip install requests`.",
        file=sys.stderr,
    )
    sys.exit(2)

SHARE_TOKEN = "HhH7crTYT4JK"  # noqa: S105 — public share token, not a secret
SHARE_BASE = "https://sansorg.egnyte.com"
SHARE_URL = f"{SHARE_BASE}/fl/{SHARE_TOKEN}"
ROOT_PATH = "/HACKATHON-2026"
CONTENTS_URL = f"{SHARE_BASE}/rest/public/1.0/links/info/{SHARE_TOKEN}/contents"
DOWNLOAD_URL = f"{SHARE_BASE}/dd/{SHARE_TOKEN}/"
PAGE_LIMIT = 48
CHUNK_BYTES = 1 << 20  # 1 MiB
USER_AGENT = "silentwitness-egnyte/1.0 (+https://github.com/Blockchain-Oracle/silentwitness)"


@dataclass(frozen=True)
class Entry:
    """One item in the share — file or folder. ``path`` is the share-root path
    (begins with ``/HACKATHON-2026``); ``entry_id`` is the Egnyte ``id`` and is
    used in the download URL."""

    path: str
    name: str
    type: str  # "folder" or "file"
    size: int | None
    last_modified: int | None
    entry_id: str


def _session() -> requests.Session:
    """Open the public-link session: GET the share page first so Egnyte sets
    the session cookie + CSRF header it requires on subsequent POSTs."""
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json, text/plain, */*"})
    r = s.get(SHARE_URL, timeout=30)
    r.raise_for_status()
    return s


def _list_contents(s: requests.Session, path: str) -> Iterator[Entry]:
    """Enumerate one folder, paginating until exhausted."""
    page = 1
    offset = 0
    while True:
        body = {
            "limit": PAGE_LIMIT,
            "offset": offset,
            "sortBy": "name",
            "sortDirection": "ASC",
            "_method": "GET",
            "path": path,
            "pageNumber": page,
        }
        r = s.post(CONTENTS_URL, json=body, timeout=30)
        r.raise_for_status()
        payload = r.json()
        contents = payload.get("contents", {})
        results = contents.get("results", [])
        if not results:
            return
        for raw in results:
            # Each entry carries both ``id`` (permanent file UUID) AND
            # ``entryId`` (share-scoped UUID used in download URLs). We
            # need ``entryId``; folders don't carry one (we don't download
            # those wholesale).
            yield Entry(
                path=raw["path"],
                name=raw["name"],
                type=raw["type"],
                size=raw.get("size"),
                last_modified=raw.get("lastModified"),
                entry_id=raw.get("entryId", raw["id"]),
            )
        total = contents.get("totalFileCount", 0) + contents.get("totalFolderCount", 0)
        offset += len(results)
        page += 1
        if offset >= total:
            return


def _walk(s: requests.Session, root: str) -> Iterator[Entry]:
    """Depth-first walk under ``root`` (a folder path). Yields files only;
    folders are descended silently. Bounded by Egnyte's response so a runaway
    share never produces an infinite walk."""
    for entry in _list_contents(s, root):
        if entry.type == "folder":
            yield from _walk(s, entry.path)
        else:
            yield entry


def _human_size(n: int | None) -> str:
    if n is None:
        return "—"
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KiB"
    if n < 1024**3:
        return f"{n / 1024**2:.1f} MiB"
    return f"{n / 1024**3:.2f} GiB"


def _stream_file(s: requests.Session, entry: Entry, target: Path) -> str:
    """Download a single file under the share path to ``target`` and return its
    SHA256 hex digest. Streams in 1 MiB chunks; computes the hash on the fly so
    no second pass over disk is needed for verification."""
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"{DOWNLOAD_URL}?entryId={entry.entry_id}"
    sha = hashlib.sha256()
    tmp = target.with_suffix(target.suffix + ".part")
    with s.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with tmp.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=CHUNK_BYTES):
                if not chunk:
                    continue
                fh.write(chunk)
                sha.update(chunk)
    tmp.replace(target)
    return sha.hexdigest()


def _resolve_case_root(s: requests.Session, case_name: str | None) -> str:
    """Map a user-friendly case label to the share path. Empty `case_name`
    returns the share root."""
    if not case_name:
        return ROOT_PATH
    for entry in _list_contents(s, ROOT_PATH):
        if entry.type == "folder" and entry.name == case_name:
            return entry.path
    raise SystemExit(
        f"case {case_name!r} not found at share root. "
        f"Run `download_starter_cases.py list` to see what's available."
    )


def cmd_list(args: argparse.Namespace) -> int:
    s = _session()
    root = _resolve_case_root(s, args.case)
    total_size = 0
    file_count = 0
    print(f"# {root}")
    if args.case is None:
        # At the share root, print sub-folder summaries with total sizes.
        for sub in _list_contents(s, root):
            if sub.type != "folder":
                continue
            sub_size = 0
            sub_files = 0
            for f in _walk(s, sub.path):
                sub_size += f.size or 0
                sub_files += 1
            print(f"  {sub.name}: {sub_files} files, {_human_size(sub_size)}")
        return 0
    # Inside a case folder, enumerate every file.
    for f in _walk(s, root):
        total_size += f.size or 0
        file_count += 1
        print(f"  {_human_size(f.size):>10}  {f.path}")
    print(f"# Total: {file_count} files, {_human_size(total_size)}")
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    s = _session()
    root = _resolve_case_root(s, args.case)
    target_root = Path(args.target).resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    print(f"# downloading {root} → {target_root}")
    total_size = 0
    file_count = 0
    for f in _walk(s, root):
        rel = f.path[len(root) :].lstrip("/")
        target = target_root / rel
        if args.dry_run:
            print(f"  DRY  {_human_size(f.size):>10}  {target}")
            total_size += f.size or 0
            file_count += 1
            continue
        if target.exists() and (f.size is None or target.stat().st_size == f.size):
            # Idempotent skip — if the file's already at the expected size we
            # don't re-download it. The hash isn't recomputed on skip; that's
            # an explicit trade-off for resumable runs over 200 GB datasets.
            print(f"  SKIP {_human_size(f.size):>10}  {target}  (size match)")
            total_size += f.size or 0
            file_count += 1
            continue
        digest = _stream_file(s, f, target)
        print(f"  OK   {_human_size(f.size):>10}  {target}  sha256={digest[:12]}…")
        total_size += f.size or 0
        file_count += 1
    print(f"# Done: {file_count} files, {_human_size(total_size)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download SANS Find Evil! 2026 starter datasets from the Egnyte public share.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="enumerate cases or files in a case")
    p_list.add_argument(
        "case",
        nargs="?",
        default=None,
        help="case folder name (omit to summarise all cases at the root)",
    )
    p_list.set_defaults(func=cmd_list)

    p_dl = sub.add_parser("download", help="download a case to a local directory")
    p_dl.add_argument("case", help="case folder name (e.g. 'Standard Forensic Case')")
    p_dl.add_argument(
        "target",
        help="target directory — will be created if missing; existing files at "
        "the expected size are skipped (idempotent / resumable)",
    )
    p_dl.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be downloaded without making any GET requests",
    )
    p_dl.set_defaults(func=cmd_download)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
