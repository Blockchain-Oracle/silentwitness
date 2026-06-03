"""Dataset manifest verifier — stub until Epic 14 lands.

The full implementation (SHA-256-pinned manifest of forensic image stubs +
fair-compare evaluation harness) is owned by Epic 14 stories. For Epic 1, this
stub exists so the CI `dataset-hash-verify` job has something concrete to call.

The ``--stub-only`` flag is what CI invokes; it succeeds quietly when no
manifest is present yet. Any other invocation raises so a future change can't
silently no-op the real check.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Verify dataset manifest hashes.")
    parser.add_argument(
        "--stub-only",
        action="store_true",
        help="Stub mode (Epic 1): succeed if no manifests are present yet.",
    )
    args = parser.parse_args(argv[1:])
    if args.stub_only:
        print("verify_manifest: stub mode — no manifests present (Epic 14 not yet merged).")
        return 0
    print(
        "verify_manifest: real verification not implemented yet (owned by Epic 14).",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
