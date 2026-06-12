"""Recompute and rewrite sha256 + size_bytes in a manifest in-place.

Used after a fixture intentionally changes (e.g., stub pcap regenerated or
a full binary is fetched and pinned for the first time).

Usage:
  uv run python harness/datasets/recompute_manifest.py <manifest.json> [<manifest.json> ...]
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

_CHUNK = 8192


def _sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def _recompute(manifest_path: Path) -> int:
    base_dir = manifest_path.parent
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))

    changed = False
    primary_sha: str | None = None
    primary_size: int | None = None

    for ef in raw.get("evidence_files", []):
        file_path = base_dir / ef["relative_path"]
        if not file_path.exists():
            print(f"  skip (missing): {ef['relative_path']}", file=sys.stderr)
            continue
        sha256, size = _sha256_file(file_path)
        if ef.get("sha256") != sha256 or ef.get("size_bytes") != size:
            print(f"  {ef['relative_path']}: {ef.get('sha256', '?')[:16]}… → {sha256[:16]}…")
            ef["sha256"] = sha256
            ef["size_bytes"] = size
            changed = True
        else:
            print(f"  {ef['relative_path']}: unchanged")
        if primary_sha is None:
            primary_sha = sha256
            primary_size = size

    # Sync manifest-level sha256/size_bytes to the primary evidence file
    if primary_sha is not None and (
        raw.get("sha256") != primary_sha or raw.get("size_bytes") != primary_size
    ):
        raw["sha256"] = primary_sha
        raw["size_bytes"] = primary_size
        changed = True

    if changed:
        manifest_path.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"  {manifest_path.name}: written")
    else:
        print(f"  {manifest_path.name}: no changes")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: recompute_manifest.py <manifest.json> [...]", file=sys.stderr)
        return 2
    for arg in argv[1:]:
        p = Path(arg)
        if not p.exists():
            print(f"not found: {p}", file=sys.stderr)
            return 2
        print(f"recomputing {p.name}:")
        code = _recompute(p)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
