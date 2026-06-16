#!/usr/bin/env bash
# install.sh — Provision SilentWitness tool dependencies on SIFT 2026.
# Every tool is version-pinned with a SHA256 checksum; never installs "latest".
# Run as a user with sudo. Idempotent — skips already-installed tools.

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
    # Release archive layout (verified v3.9.0): the binary sits at the archive
    # root, version-suffixed as `hayabusa-3.9.0-lin-x64-gnu` (NOT a plain
    # `hayabusa` inside a wrapper dir). Match the versioned name and flatten.
    local hb_bin
    hb_bin="$(find "$TMPDIR/hayabusa-extracted" -type f -name 'hayabusa-*-lin-x64-gnu' | head -1)"
    [[ -n "$hb_bin" ]] || fail "hayabusa binary not found in extracted archive"
    sudo cp "$hb_bin" /opt/hayabusa/hayabusa
    sudo chmod +x /opt/hayabusa/hayabusa
    # Hayabusa is a subcommand CLI (clap): it rejects `--version`/`-V`/`-h`.
    # `help` is the only zero-exit smoke check and prints the version banner.
    /opt/hayabusa/hayabusa help >/dev/null 2>&1 || fail "hayabusa runtime check failed"
    # Assert the exact version so a wrong/corrupt/mismatched binary fails loudly.
    # Capturing without comparing would silently accept a blank banner (pipefail
    # is masked inside command substitution), so the banner must be load-bearing.
    local hb_ver
    hb_ver="$(/opt/hayabusa/hayabusa help 2>&1 | grep -ioE 'Hayabusa v[0-9.]+' | head -1)"
    [[ "$hb_ver" == "Hayabusa v3.9.0" ]] \
        || fail "hayabusa version check failed (expected Hayabusa v3.9.0, got: '${hb_ver:-<none>}')"
    log "Hayabusa installed: $hb_ver"
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
    # Suricata's version flag is `-V` (not `--version`, which it rejects).
    /usr/bin/suricata -V || fail "suricata runtime check failed"
    log "Suricata installed at /usr/bin/suricata"
    # Fetch ET Open rules to /var/lib/suricata/rules/suricata.rules.
    # suricata_run uses -S <rules> to load ONLY the caller-specified rules file;
    # the default rules are NOT consumed by the tool but are useful for ad-hoc checks.
    if command -v suricata-update &>/dev/null; then
        sudo suricata-update || log "suricata-update failed (non-fatal — rules can be provided manually)"
    fi
}

# ---------------------------------------------------------------------------
# Evidence-access stack (Phase 0) — open E01 images + decompress memory archives.
# dfVFS is the opt-in `forensics` extra: its libyal C-extension bindings
# (pytsk3/libvsgpt/libvshadow/...) compile from sdists, so the box needs a build
# toolchain + pkg-config + python headers. p7zip-full unwraps the nested memory
# capture (zip->7z->raw). dosfstools/mtools build the FAT fixtures the access
# integration tests use. sleuthkit + libewf back dfVFS's E01 reading.
# ---------------------------------------------------------------------------
install_evidence_access() {
    log "installing evidence-access apt deps (p7zip + dfVFS build toolchain + test tools)"
    sudo apt-get update -q
    sudo apt-get install -y --no-install-recommends \
        p7zip-full build-essential pkg-config python3-dev \
        sleuthkit libewf-dev dosfstools mtools \
        ewf-tools ntfs-3g fuse3
    log "evidence-access apt deps installed — now install the Python extra:"
    log "    uv sync --extra forensics   # builds dfVFS + libyal bindings on this Linux box"
}

# ---------------------------------------------------------------------------
# spaCy NER model (RUNTIME, load-bearing). The entity gate (§4.7, hallucination
# firewall) loads en_core_web_lg at the first record_observation. Without it
# EVERY observation is rejected ENTITY_GATE_UNAVAILABLE and the agent stages
# ZERO findings — the exact failure a fresh-OVA reproduction hits (surfaced by
# the live ROCBA run). `uv run` supplies the installer the bare model wheel
# needs (the project venv ships no pip). Idempotent: skip if already loadable.
# ---------------------------------------------------------------------------
install_spacy_model() {
    log "installing spaCy en_core_web_lg (entity-gate NER model, ~560 MB)"
    if uv run python -c "import spacy; spacy.load('en_core_web_lg')" 2>/dev/null; then
        log "en_core_web_lg already present — skipping"
        return
    fi
    uv run python -m spacy download en_core_web_lg \
        || fail "spaCy en_core_web_lg install failed — entity gate would reject every observation"
    uv run python -c "import spacy; spacy.load('en_core_web_lg')" \
        || fail "en_core_web_lg installed but does not load"
}

# ---------------------------------------------------------------------------
# Mermaid CLI (optional, --diagrams flag) — DOCS-TIME ONLY, NOT RUNTIME.
#
# Why this exists: SIFT 2026 ships dotnet 9 + Python but NOT Node.js.
# The CLI never invokes mmdc at
# runtime; only docs/diagrams/*.mmd regeneration needs it. We gate behind
# `--diagrams` so the base install path stays fast for judges who only need
# `silentwitness investigate`.
#
# Required by: tests/unit/test_architecture_diagram.py (CI uses the committed
# PNG so the runner needs no Node; this block is for docs maintainers running
# `just diagrams` locally before pushing diagram changes).
#
# nvm install.sh v0.40.1: pinned by SHA256 (matches verify_sha256 convention
# at install.sh:15). mmdc pin: @^10 per story-architecture-diagram-png spec.
# ---------------------------------------------------------------------------
NVM_INSTALL_SHA256="abdb525ee9f5b48b34d8ed9fc67c6013fb0f659712e401ecd88ab989b3af8f53"  # pragma: allowlist secret

install_mermaid_cli() {
    log "provisioning Node 20 + @mermaid-js/mermaid-cli@^10 (docs-time)"
    # Probe both `command -v` and the canonical nvm.sh path — fresh non-interactive
    # shells don't pick up the .bashrc nvm function registration.
    if [ ! -s "$HOME/.nvm/nvm.sh" ] && ! command -v nvm >/dev/null 2>&1; then
        local nvm_tmp="$TMPDIR/nvm-install.sh"
        curl -fsSL -o "$nvm_tmp" https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh \
            || fail "nvm install.sh download failed"
        verify_sha256 "$nvm_tmp" "$NVM_INSTALL_SHA256"
        bash "$nvm_tmp" || fail "nvm v0.40.1 install failed"
    fi
    export NVM_DIR="$HOME/.nvm"
    # nvm.sh references unset vars internally; relax `set -u` while sourcing
    # (documented nvm gotcha, see nvm README).
    set +u
    # shellcheck source=/dev/null
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    set -u
    nvm install 20 || fail "nvm install 20 failed"
    nvm use 20 || fail "nvm use 20 failed"
    npm install -g "@mermaid-js/mermaid-cli@^10" || fail "npm install @mermaid-js/mermaid-cli failed"
    mmdc --version || fail "mmdc runtime check failed"
}

# ---------------------------------------------------------------------------
# silentwitness Python CLI — uv + global tool install.
#
# Closes the gap between "subprocess tools installed" and "`silentwitness`
# command available." Without this step the README's quickstart broke at
# step 2: judges had no `silentwitness` on PATH. With it, `silentwitness
# --help` works in the same shell session.
#
# uv is the bootstrapper (single static binary; no Python needed to install
# it). Once present, `uv tool install` puts the CLI shim at
# ``~/.local/bin/silentwitness`` (already on PATH per the uv installer's
# shell hook).
#
# Repo root resolution: prefer the caller's CWD if it looks like a
# silentwitness checkout; otherwise clone fresh to ``/opt/silentwitness/repo``
# so the curl-pipe-bash flow works.
#
# Forensics extra (dfvfs / pytsk3 / libyal) is included on Linux — pyproject
# explicitly marks it macOS-incompatible (those wheels don't build on
# Darwin), so we omit on non-Linux.
# ---------------------------------------------------------------------------
install_silentwitness_cli() {
    log "installing uv + silentwitness CLI globally"

    if ! command -v uv >/dev/null 2>&1; then
        log "uv not found — installing via astral.sh installer (no root needed)"
        # Download to a file FIRST + sanity-check the body BEFORE piping to sh.
        # `curl … | sh` runs whatever bytes come back; a captive portal / proxy
        # returning HTML would otherwise have sh parse <html> as commands and
        # produce a wall of "Syntax error" with no clear cause (silent-failure
        # hunter #6, PR #238 review).
        local uv_installer="$TMPDIR/uv-install.sh"
        curl -fsSL -o "$uv_installer" https://astral.sh/uv/install.sh \
            || fail "uv installer download failed"
        # Astral's installer starts with `#!/bin/sh` and a recognisable marker
        # comment. Reject anything that isn't a POSIX shell script.
        head -1 "$uv_installer" | grep -q '^#!/.*sh' \
            || fail "uv installer body is not a shell script — captive portal / proxy intercept?"
        grep -q -i 'astral\|uv' "$uv_installer" \
            || fail "uv installer body missing astral/uv marker — refusing to execute"
        sh "$uv_installer" || fail "uv installer execution failed"
        # uv installer attempts to patch the shell rc; behaviour varies by
        # shell/OS/interactive state, so hard-export PATH for this script's
        # duration regardless.
        export PATH="$HOME/.local/bin:$PATH"
    fi

    command -v uv >/dev/null 2>&1 || fail "uv still not on PATH after install"

    # CLAUDE.md pins uv==0.11.18 (0.5.x has breaking semantics for `uv lock`
    # and `uv tool`). FAIL (not warn) on drift so a judge with a wrong uv on
    # PATH doesn't get an inscrutable failure 30 lines later attributed to
    # uv when the real cause is version skew. Override with the env var when
    # intentionally testing a different uv.
    local uv_ver
    uv_ver="$(uv --version | awk '{print $2}')"
    if [[ "$uv_ver" != "0.11.18" ]]; then
        if [[ "${SILENTWITNESS_ALLOW_UV_DRIFT:-0}" == "1" ]]; then
            log "WARNING: uv $uv_ver vs pinned 0.11.18 — SILENTWITNESS_ALLOW_UV_DRIFT=1 set, continuing"
        else
            fail "uv $uv_ver does not match pinned 0.11.18; set SILENTWITNESS_ALLOW_UV_DRIFT=1 to override"
        fi
    fi

    # Resolve the silentwitness repo.
    local repo_root="${SILENTWITNESS_REPO_ROOT:-$PWD}"
    if [[ ! -f "$repo_root/pyproject.toml" ]] || ! grep -q '^name = "silentwitness"' "$repo_root/pyproject.toml" 2>/dev/null; then
        repo_root="/opt/silentwitness/repo"
        if [[ ! -d "$repo_root/.git" ]]; then
            log "cloning silentwitness into $repo_root (no checkout in CWD)"
            sudo mkdir -p /opt/silentwitness
            # Use the user's actual primary group (not username — Debian uses
            # `users`, macOS uses `staff`); the prior `$USER:$USER` form
            # silently fell back to bare $USER which strips group perms.
            sudo chown -R "$USER:$(id -gn)" /opt/silentwitness
            git clone --depth 1 https://github.com/Blockchain-Oracle/silentwitness.git "$repo_root" \
                || fail "git clone of silentwitness repo failed"
            # Defense in depth: a "successful" clone can still produce an
            # empty / partial checkout (network drop mid-pack, renamed
            # default branch, bad mirror). Assert the manifest is there
            # BEFORE handing the repo to uv tool install — otherwise the
            # failure surfaces 20 lines later as "pyproject.toml not found"
            # and the user blames uv.
            [[ -f "$repo_root/pyproject.toml" ]] \
                || fail "git clone succeeded but pyproject.toml missing at $repo_root — corrupt clone?"
            grep -q '^name = "silentwitness"' "$repo_root/pyproject.toml" \
                || fail "git clone produced wrong repo at $repo_root — pyproject.toml is not silentwitness's"
        else
            log "using existing checkout at $repo_root"
            # Stale local edits → `git pull --ff-only` rebases-but-fails; we
            # FAIL not WARN so the install doesn't proceed against a stale
            # tree and produce wrong-version artefacts. Override with the
            # env var when explicitly testing a local fork.
            if ! (cd "$repo_root" && git pull --ff-only) >/dev/null 2>&1; then
                if [[ "${SILENTWITNESS_ALLOW_STALE_CHECKOUT:-0}" == "1" ]]; then
                    log "WARNING: git pull failed in $repo_root — SILENTWITNESS_ALLOW_STALE_CHECKOUT=1 set, continuing"
                else
                    fail "git pull --ff-only failed in $repo_root; set SILENTWITNESS_ALLOW_STALE_CHECKOUT=1 to override"
                fi
            fi
        fi
    else
        log "using silentwitness repo at $repo_root (already on disk)"
    fi

    # Pick install target: include the forensics extra on Linux (dfVFS + plaso
    # + libyal bindings have native deps we just installed in
    # install_evidence_access); omit on macOS so the Darwin smoke path also
    # finishes — the forensics extra explicitly does not build there.
    local install_target="$repo_root"
    if [[ "$(uname -s)" == "Linux" ]]; then
        # `silentwitness[forensics] @ file://...` is PEP 508; uv understands it.
        install_target="silentwitness[forensics] @ file://$repo_root"
    fi

    # Capture stderr to a tempfile so a uv failure (network blip, missing
    # build toolchain, dep resolution conflict) surfaces with its real cause
    # instead of just "uv tool install failed".
    local uv_err="$TMPDIR/uv-tool-install.err"
    if ! uv tool install --reinstall "$install_target" 2>"$uv_err"; then
        cat "$uv_err" >&2
        fail "uv tool install $install_target failed (see error above)"
    fi

    command -v silentwitness >/dev/null 2>&1 \
        || fail "silentwitness not on PATH after uv tool install (check ~/.local/bin)"
    silentwitness --help >/dev/null 2>&1 \
        || fail "silentwitness --help smoke check failed"
    log "silentwitness installed at $(command -v silentwitness)"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
DIAGRAMS=0
for arg in "$@"; do
    case "$arg" in
        --diagrams) DIAGRAMS=1 ;;
        *) fail "unknown flag: $arg (supported: --diagrams)" ;;
    esac
done

# The CLI install runs first so a fail-fast at the very first step short-
# circuits before we spend time pulling Hayabusa / Chainsaw / Zeek etc. —
# the subprocess tools are useless without `silentwitness` to drive them.
install_silentwitness_cli
install_hayabusa
install_hayabusa_rules
install_chainsaw
install_sigma_rules
install_zeek
install_suricata
install_evidence_access
install_spacy_model
[ "$DIAGRAMS" = "1" ] && install_mermaid_cli

log "all tools provisioned successfully"
log "next: run \`silentwitness --help\` (it's a global command now)"
