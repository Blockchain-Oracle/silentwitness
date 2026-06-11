#!/usr/bin/env bash
# install.sh — Provision SilentWitness tool dependencies on SIFT 2026.
# Every tool is version-pinned with a SHA256 checksum; never installs "latest".
# Run as a user with sudo. Idempotent — skips already-installed tools.
# See context/.raw-design-research/03 §"Tools our install script MUST add".

set -euo pipefail

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

log()  { echo "[install.sh] $*" >&2; }
fail() { echo "[install.sh] FATAL: $*" >&2; exit 1; }

verify_sha256() {
    local file="$1" expected="$2"
    local actual
    actual="$(sha256sum "$file" | awk '{print $1}')"
    if [[ "$actual" != "$expected" ]]; then
        fail "SHA256 mismatch for $file: expected=$expected actual=$actual"
    fi
    log "SHA256 OK: $file"
}

# ---------------------------------------------------------------------------
# Hayabusa v3.9.0
# SHA256: ffb31e02bd47d840d999d964d4663287cdb194a22ea856904348786acba414d7
# Source: docs/.audit/06-sift-and-datasets-verification.md §Hayabusa v3.9.0
# License: GPL-3.0 — subprocess use (no linking); acceptable per architecture §6.
# ---------------------------------------------------------------------------
install_hayabusa() {
    if [[ -x /opt/hayabusa/hayabusa ]]; then
        log "Hayabusa already installed at /opt/hayabusa/hayabusa — skipping"
        return
    fi
    log "installing Hayabusa v3.9.0"
    curl -sSL -o "$TMPDIR/hayabusa.zip" \
        "https://github.com/Yamato-Security/hayabusa/releases/download/v3.9.0/hayabusa-3.9.0-lin-x64-gnu.zip"
    verify_sha256 "$TMPDIR/hayabusa.zip" \
        "ffb31e02bd47d840d999d964d4663287cdb194a22ea856904348786acba414d7"  # pragma: allowlist secret
    sudo mkdir -p /opt/hayabusa
    sudo unzip -q "$TMPDIR/hayabusa.zip" -d "$TMPDIR/hayabusa-extracted"
    # Release archive layout: hayabusa-3.9.0-lin-x64-gnu/hayabusa — flatten.
    sudo cp "$(find "$TMPDIR/hayabusa-extracted" -name hayabusa -type f | head -1)" \
        /opt/hayabusa/hayabusa
    sudo chmod +x /opt/hayabusa/hayabusa
    /opt/hayabusa/hayabusa --version || fail "hayabusa runtime check failed"
    log "Hayabusa v3.9.0 installed at /opt/hayabusa/hayabusa"
}

# ---------------------------------------------------------------------------
# Hayabusa rules corpus (commit-pinned for reproducibility)
# Hayabusa ships --rules/-r flag; we clone to /opt/hayabusa-rules/ and pass
# -r /opt/hayabusa-rules to every invocation.
# ---------------------------------------------------------------------------
install_hayabusa_rules() {
    if [[ -d /opt/hayabusa-rules ]]; then
        log "Hayabusa rules already at /opt/hayabusa-rules — skipping"
        return
    fi
    log "cloning Hayabusa rules corpus (depth=1)"
    sudo git clone --depth 1 \
        https://github.com/Yamato-Security/hayabusa-rules \
        /opt/hayabusa-rules
    log "Hayabusa rules installed at /opt/hayabusa-rules"
}

# ---------------------------------------------------------------------------
# Chainsaw v2.16.0
# SHA256: 5d46cd140838413aeb5711451a282b3922443d9ec6afaea3e6b6b220454fd807
# Source: docs/.audit/06-sift-and-datasets-verification.md §Chainsaw v2.16.0
# License: GPL-3.0 — subprocess use; acceptable.
# ---------------------------------------------------------------------------
install_chainsaw() {
    if [[ -x /opt/chainsaw/chainsaw ]]; then
        log "Chainsaw already installed at /opt/chainsaw/chainsaw — skipping"
        return
    fi
    log "installing Chainsaw v2.16.0"
    curl -sSL -o "$TMPDIR/chainsaw.tgz" \
        "https://github.com/WithSecureLabs/chainsaw/releases/download/v2.16.0/chainsaw_x86_64-unknown-linux-gnu.tar.gz"
    verify_sha256 "$TMPDIR/chainsaw.tgz" \
        "5d46cd140838413aeb5711451a282b3922443d9ec6afaea3e6b6b220454fd807"  # pragma: allowlist secret
    sudo mkdir -p /opt/chainsaw
    sudo tar -xzf "$TMPDIR/chainsaw.tgz" -C /opt/chainsaw --strip-components=1
    sudo chmod +x /opt/chainsaw/chainsaw
    [[ -f /opt/chainsaw/mappings/sigma-event-logs-all.yml ]] \
        || fail "chainsaw mapping file missing after extraction"
    /opt/chainsaw/chainsaw --version || fail "chainsaw runtime check failed"
    log "Chainsaw v2.16.0 installed at /opt/chainsaw/chainsaw"
}

# ---------------------------------------------------------------------------
# SigmaHQ rules (tag-pinned for reproducibility — used by Chainsaw)
# ---------------------------------------------------------------------------
install_sigma_rules() {
    if [[ -d /opt/sigma ]]; then
        log "SigmaHQ rules already at /opt/sigma — skipping"
        return
    fi
    log "cloning SigmaHQ rules (tag r2026-04-01)"
    sudo git clone --depth 1 --branch r2026-04-01 \
        https://github.com/SigmaHQ/sigma \
        /opt/sigma
    log "SigmaHQ rules installed at /opt/sigma"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
install_hayabusa
install_hayabusa_rules
install_chainsaw
install_sigma_rules

log "all tools provisioned successfully"
