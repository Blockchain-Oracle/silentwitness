"""Dataset manifest verifier — stub until Epic 14 lands.

The full implementation (SHA-256-pinned manifest of forensic image stubs +
fair-compare evaluation harness) is owned by Epic 14 stories. For Epic 1, this
stub exists so the CI `dataset-hash-verify` job has something concrete to call.

Forcing-function design: when Epic 14 lands real manifests under
``harness/datasets/manifests/``, ``--stub-only`` will refuse to run — that
prevents the gate from silently no-opping at submission time. A future Epic 14
PR has to flip CI to the real verifier in the same commit that introduces the
first manifest file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_MANIFEST_DIR = Path(__file__).resolve().parent / "manifests"


def _manifest_files_present() -> list[Path]:
    if not _MANIFEST_DIR.exists():
        return []
    return sorted(p for p in _MANIFEST_DIR.iterdir() if p.is_file())


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify dataset manifest hashes.")
    parser.add_argument(
        "--stub-only",
        action="store_true",
        help="Stub mode (Epic 1): succeed if no manifests are present yet.",
    )
    args = parser.parse_args(argv[1:])
    if args.stub_only:
        manifests = _manifest_files_present()
        if manifests:
            print(
                "verify_manifest: STUB MODE INVOKED BUT MANIFESTS EXIST — "
                "Epic 14 landed but CI is still calling --stub-only. "
                f"Found: {[m.name for m in manifests]}. "
                "Flip .github/workflows/ci.yml `dataset-hash-verify` to the real verifier.",
                file=sys.stderr,
            )
            return 2
        print("verify_manifest: stub mode — no manifests present (Epic 14 not yet merged).")
        return 0
    print(
        "verify_manifest: real verification not implemented yet (owned by Epic 14).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
