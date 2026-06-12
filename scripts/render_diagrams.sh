#!/usr/bin/env bash
# render_diagrams.sh — regenerate docs/diagrams/*.png from .mmd source.
#
# Why this exists: docs/diagrams/architecture.png is the README's
# above-the-fold visual asset. We commit the PNG (judges hit GitHub raw
# without Node available) and use this script to keep it in sync with the
# .mmd source. The 500 KiB (= 500 × 1024 = 512000-byte) cap keeps the
# README asset cheap to fetch and the PR diff reviewable.
#
# Required by: tests/unit/test_architecture_diagram.py (asserts size cap +
# magic bytes + parses each .mmd via mmdc).
#
# Failure aggregation: all .mmd files are processed even if one render
# fails or one PNG exceeds the cap; exit 1 at end with combined report.
#
# Exit 0 on success; 1 on missing mmdc, render failure, or oversized PNG.

set -euo pipefail

DIAGRAMS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docs/diagrams"
MAX_BYTES=512000  # 500 KiB (= 500 × 1024)

if [ ! -d "$DIAGRAMS_DIR" ]; then
    echo "ERROR: $DIAGRAMS_DIR not found" >&2
    exit 1
fi

if ! command -v mmdc >/dev/null 2>&1; then
    echo "ERROR: mmdc not installed. Run './install.sh --diagrams' to provision." >&2
    exit 1
fi

shopt -s nullglob
declare -a FAILURES=()

for src in "$DIAGRAMS_DIR"/*.mmd; do
    out="${src%.mmd}.png"
    echo "rendering $src → $out" >&2
    # Stream mmdc stdout+stderr through so font/Chromium/parse warnings reach
    # the operator. Silencing stdout (mmdc 11 emits parse errors there on
    # some configs) masks real diagnostics on a silent-but-wrong render.
    if ! mmdc -i "$src" -o "$out" -t dark -b transparent -w 1600 -H 1000; then
        FAILURES+=("$src: mmdc render failed")
        continue
    fi
    size=$(wc -c <"$out")
    if [ "$size" -gt "$MAX_BYTES" ]; then
        FAILURES+=("$out: $size bytes exceeds 500 KiB cap ($MAX_BYTES)")
    fi
done

if [ ${#FAILURES[@]} -gt 0 ]; then
    echo "ERROR: render_diagrams.sh failed:" >&2
    printf '  - %s\n' "${FAILURES[@]}" >&2
    exit 1
fi
