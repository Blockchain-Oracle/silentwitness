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
# Zeek — NOT pre-installed on SIFT 2026.
# context/.raw-design-research/03 §"Tools NEEDED but NOT pre-installed" line 217.
# Install via OpenSUSE security:zeek repo (Ubuntu Noble). The package installs
# to /opt/zeek/bin/zeek; we symlink to /usr/local/bin/zeek for get_zeek_bin().
# Use zeek-lts (LTS series) rather than zeek (always-latest) for reproducibility.
# ---------------------------------------------------------------------------
install_zeek() {
    if command -v zeek &>/dev/null || [[ -x /opt/zeek/bin/zeek ]]; then
        log "Zeek already installed — skipping"
        return
    fi
    log "installing Zeek (LTS) via OpenSUSE security:zeek repo (Ubuntu Noble)"
    sudo mkdir -p /etc/apt/keyrings
    curl -sSL \
        "https://download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04/Release.key" \
        | gpg --dearmor \
        | sudo tee /etc/apt/keyrings/security_zeek.gpg > /dev/null
    echo "deb [signed-by=/etc/apt/keyrings/security_zeek.gpg] http://download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04/ /" \
        | sudo tee /etc/apt/sources.list.d/security:zeek.list
    sudo apt-get update -q
    # zeek-lts pins to the current LTS minor series (6.0.x) rather than always-latest.
    sudo apt-get install -y --no-install-recommends zeek-lts
    # Package installs to /opt/zeek/bin/zeek — symlink to the expected get_zeek_bin() path.
    if [[ ! -x /usr/local/bin/zeek ]] && [[ -x /opt/zeek/bin/zeek ]]; then
        sudo ln -sf /opt/zeek/bin/zeek /usr/local/bin/zeek
        log "created /usr/local/bin/zeek → /opt/zeek/bin/zeek"
    fi
    # Verify.
    if command -v zeek &>/dev/null; then
        zeek --version || fail "zeek runtime check failed"
        log "Zeek installed at $(command -v zeek)"
    elif [[ -x /opt/zeek/bin/zeek ]]; then
        /opt/zeek/bin/zeek --version || fail "zeek runtime check failed"
        log "Zeek installed at /opt/zeek/bin/zeek"
    else
        fail "zeek not found after installation — check apt output above"
    fi
}

# ---------------------------------------------------------------------------
# Suricata — NOT pre-installed on SIFT 2026.
# context/.raw-design-research/03 §"Tools NEEDED but NOT pre-installed" line 218.
# Ubuntu Noble universe ships Suricata 7.x at /usr/bin/suricata — no third-party
# repo needed. After install, run suricata-update to fetch ET Open rules.
# ---------------------------------------------------------------------------
install_suricata() {
    if command -v suricata &>/dev/null; then
        log "Suricata already installed at $(command -v suricata) — skipping"
        return
    fi
    log "installing Suricata from Ubuntu Noble universe"
    sudo apt-get update -q
    sudo apt-get install -y --no-install-recommends suricata
    /usr/bin/suricata --version || fail "suricata runtime check failed"
    log "Suricata installed at /usr/bin/suricata"
    # Fetch ET Open rules to /var/lib/suricata/rules/suricata.rules.
    # suricata_run uses -S <rules> to load ONLY the caller-specified rules file;
    # the default rules are NOT consumed by the tool but are useful for ad-hoc checks.
    if command -v suricata-update &>/dev/null; then
        sudo suricata-update || log "suricata-update failed (non-fatal — rules can be provided manually)"
    fi
}

# ---------------------------------------------------------------------------
# Mermaid CLI (optional, --diagrams flag) — docs-time only.
# SIFT 2026 ships dotnet 9 + Python but NOT Node.js (context/.raw-design-research/03
# line 207). We provision Node 20 LTS via nvm and install @mermaid-js/mermaid-cli@^10
# globally to give docs maintainers `mmdc` for regenerating docs/diagrams/*.png.
# Pinned major: ^10 (mmdc 10.x stable; v11 introduces breaking flags).
# ---------------------------------------------------------------------------
install_mermaid_cli() {
    log "provisioning Node 20 + @mermaid-js/mermaid-cli@^10 (docs-time)"
    if ! command -v nvm >/dev/null 2>&1; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        # shellcheck source=/dev/null
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi
    nvm install 20
    nvm use 20
    npm install -g "@mermaid-js/mermaid-cli@^10"
    mmdc --version || fail "mmdc runtime check failed"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
DIAGRAMS=0
for arg in "$@"; do
    case "$arg" in
        --diagrams) DIAGRAMS=1 ;;
    esac
done

install_hayabusa
install_hayabusa_rules
install_chainsaw
install_sigma_rules
install_zeek
install_suricata
[ "$DIAGRAMS" = "1" ] && install_mermaid_cli

log "all tools provisioned successfully"
