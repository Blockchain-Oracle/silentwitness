#!/usr/bin/env bash
# sift_probe.sh — establish GROUND TRUTH on the real SANS SIFT Workstation.
#
# Why this exists: our docs (CLAUDE.md, context/) disagree about where the
# forensic tools actually live (e.g. vol at /opt/silentwitness/vol3-venv vs
# /opt/volatility3 vs /usr/local/bin). Docs can be wrong. This script asks the
# BOX, not the docs. Run it on the SIFT VM; paste the output back so we fix the
# code's hardcoded paths to match reality.
#
# Read-only. Installs nothing. Safe to run repeatedly.

set -uo pipefail

hr() { printf '%s\n' "------------------------------------------------------------"; }
probe() {  # probe "<label>" "<candidate path or command>"
    local label="$1" target="$2"
    if command -v "$target" >/dev/null 2>&1; then
        printf '  %-22s FOUND (on PATH): %s\n' "$label" "$(command -v "$target")"
    elif [[ -e "$target" ]]; then
        printf '  %-22s FOUND (file):    %s\n' "$label" "$target"
    else
        printf '  %-22s MISSING:         %s\n' "$label" "$target"
    fi
}

echo "SIFT GROUND-TRUTH PROBE  ($(date -u +%FT%TZ))"
echo "host: $(uname -a)"
hr
echo "OS / release:"
( . /etc/os-release 2>/dev/null && echo "  $PRETTY_NAME" ) || echo "  (unknown)"
hr

echo "VOLATILITY 3 (memory) — code calls /opt/silentwitness/vol3-venv/bin/vol:"
probe "vol (PATH)"            "vol"
probe "/usr/local/bin/vol"    "/usr/local/bin/vol"
probe "/opt/volatility3"      "/opt/volatility3/bin/vol"
probe "our pinned venv"       "/opt/silentwitness/vol3-venv/bin/vol"
command -v vol >/dev/null 2>&1 && echo "  version: $(vol --help 2>&1 | head -1)"
hr

echo "DISK — Sleuth Kit + EZ Tools (.NET):"
probe "dotnet"               "/usr/bin/dotnet"
probe "mmls (TSK)"           "mmls"
probe "fls (TSK)"            "fls"
probe "MFTECmd.dll"          "/opt/zimmermantools/MFTECmd.dll"
probe "EvtxECmd.dll"         "/opt/zimmermantools/EvtxeCmd/EvtxECmd.dll"
echo "  searching for EZ Tools .dll locations (first 10):"
find /opt /usr /home -iname 'MFTECmd.dll' -o -iname 'EvtxECmd.dll' 2>/dev/null | head -10 | sed 's/^/    /' || true
hr

echo "REGISTRY — RegRipper:"
probe "rip.pl (PATH)"        "rip.pl"
probe "/usr/local/bin/rip.pl" "/usr/local/bin/rip.pl"
probe "regripper"            "regripper"
hr

echo "LOG/NETWORK — install.sh-provisioned (should be MISSING on fresh SIFT until install.sh runs):"
probe "hayabusa"             "/opt/hayabusa/hayabusa"
probe "chainsaw"             "/opt/chainsaw/chainsaw"
probe "zeek (PATH)"          "zeek"
probe "zeek (/opt)"          "/opt/zeek/bin/zeek"
probe "suricata"             "suricata"
hr

echo "AGENT RUNTIME:"
probe "claude (Claude Code)" "/usr/local/bin/claude"
probe "python3"              "python3"
probe "uv"                   "uv"
probe "git"                  "git"
hr
echo "PROBE COMPLETE — paste this whole output back."
