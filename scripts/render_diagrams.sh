#!/usr/bin/env bash
# Render every docs/diagrams/*.mmd to a same-name *.png via mmdc.
# Exit 0 on success; 1 on missing mmdc or oversized PNG.
set -euo pipefail

DIAGRAMS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/docs/diagrams"
MAX_BYTES=512000

if ! command -v mmdc >/dev/null 2>&1; then
    echo "ERROR: mmdc not installed. Run './install.sh --diagrams' to provision." >&2
    exit 1
fi

shopt -s nullglob
for src in "$DIAGRAMS_DIR"/*.mmd; do
    out="${src%.mmd}.png"
    echo "rendering $src → $out" >&2
    mmdc -i "$src" -o "$out" -t dark -b transparent -w 1600 -H 1000 >/dev/null
    size=$(wc -c <"$out")
    if [ "$size" -gt "$MAX_BYTES" ]; then
        echo "ERROR: $out exceeds 500 KB (${size} bytes)" >&2
        exit 1
    fi
done
