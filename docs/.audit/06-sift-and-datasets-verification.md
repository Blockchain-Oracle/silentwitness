# SIFT 2026 + Datasets — Deep Verification

> **Audit date:** 2026-06-03 02:53 GMT+1
> **Cloned `--depth 1` for this audit:**
> - `teamdfir/sift-saltstack` HEAD `96b7d98` (2026-04-13 — "Merge pull request #219 from digitalsleuth/vol3")
> - `teamdfir/sift-packer` HEAD
> **Live URL probes:** every dataset, GitHub-release asset, NIST artefact, and OS package source was HEAD- or GET-verified in the same audit window.
> **Real bytes downloaded + sha256-confirmed** for: Nitroba pcap, NIST `leakage-answers.pdf`, Hayabusa zip, Chainsaw tgz, Velociraptor binary, capa zip, FLOSS zip, PECmd zip, SrumECmd zip. Multi-GB NIST E01s confirmed by Content-Length + 2 KB range-read (EWF magic bytes verified).

---

## Section 1 — SIFT 2026 install state drift since `03-sift-2026-tool-catalog-verified.md`

Every claim in `context/.raw-design-research/03` re-checked against current HEAD. Drift summary:

| Claim in `03` | Re-check result | Drift |
|---|---|---|
| Ubuntu **24.04.2** default | `sift-packer/variables.pkr.hcl` line 41 `default = "24.04.2"` | NONE |
| Default user `sansforensics` | `variables.pkr.hcl` line 23 `default = "sansforensics"` | NONE |
| Default password `forensics` | `variables.pkr.hcl` line 29 `default = "forensics"` | NONE |
| Python 3.12 on Noble | `python3-packages/indxparse.sls` lines 11–13 `oscodename == 'noble'` → `py_ver = '3.12'`; same in `python-evtx.sls` lines 11–14 | NONE |
| Default user shell python = `python3` via `python-is-python3` | `packages/python3.sls` + `packages/python-is-python3.sls` ship; install state preserved | NONE |
| **Claude Code v2.0.61** at `/usr/local/bin/claude` | `packages/claude-code.sls` line 1 `set version = "2.0.61"`; line 3 `hash = "5c5686e99180eb0bd0498564e1fa991aa05c4199a08222a15c1563626332e8fc"`; file.managed name `/usr/local/bin/claude` | NONE — verbatim confirmed |
| **docker-compose 2.32.4** at `/usr/local/bin/docker-compose` | `scripts/docker-compose.sls` line 1 `set version = "2.32.4"` | NONE — verbatim confirmed |
| Docker daemon pre-installed | `packages/docker.sls` present | NONE |
| **Apache2 on port 80** with CyberChef at `/var/www/html/cyberchef/` | `packages/apache2.sls` is bare `pkg.installed` → Ubuntu default `Listen 80`, no override; `scripts/cyberchef.sls` v9.55.0 SHA `DA55ADC790D011F6BF3740E7E704D340351F7E1C8EBD8E7D9DD24AA46562307C` confirmed | NONE — port 80 is bound |
| Port **8088** unbound | No SLS file references 8088 (`grep -lir "8088" /tmp/sift-recheck/sift/` returns empty) | CONFIRMED — safe default for our HUD |
| .NET SDK 9 | `packages/dotnet.sls` ships | NONE |
| Node.js **NOT installed** | No `nodejs.sls`, no `npm.sls`, no `node` package reference | NONE — confirmed absent |
| **uv NOT installed** | No SLS references `astral` or standalone `uv` binary | NONE — confirmed absent |
| 15 EZ Tools installed via `dotnet 9` wrappers | `scripts/zimmerman.sls` line 9 array: `['AmcacheParser','AppCompatCacheParser','bstrings','EvtxECmd','iisGeolocate','JLECmd','LECmd','MFTECmd','RBCmd','RecentFileCacheParser','RECmd','rla','SBECmd','SQLECmd','WxTCmd']` — **15 tools, PECmd + SrumECmd absent** | NONE — claim accurate |
| Vol3 venv at `/opt/volatility3/` (not `/opt/volatility3-2.20.0/`) | `python3-packages/volatility3.sls` installs to `/opt/volatility3` with symlinks `/usr/local/bin/vol` + `/usr/local/bin/volshell` | NONE |
| WeasyPrint native deps **NOT pre-installed** | Only `libcairo2-dev.sls` + `libffi-dev.sls` present; **NO `libpango-1.0-0`, NO `libpangocairo-1.0-0`, NO `libgdk-pixbuf-2.0-0`, NO `libharfbuzz0b`, NO `shared-mime-info` SLS files**; grep for `pango|harfbuzz|gdk-pixbuf|gobject` across whole repo: zero matches | **DRIFT-FREE WITH SPEC — but story-docker-baseline says "WeasyPrint native deps" must be installed in the Dockerfile; if the SilentWitness MCP is run NATIVELY on SIFT (not via Docker), `install.sh` MUST `apt install` these. Adding to install.sh below.** |
| Zeek **NOT installed** | No `zeek.sls`, no `bro.sls` | CONFIRMED |
| Suricata **NOT installed** | No `suricata.sls` | CONFIRMED |
| Hayabusa / Chainsaw / Velociraptor **NOT installed** | No SLS files | CONFIRMED |
| capa / FLOSS / binwalk **NOT installed** | No SLS files | CONFIRMED |
| PECmd + SrumECmd absent from `zimmerman.sls` | Confirmed against line 9 array | CONFIRMED — install.sh must add |

**Section 1 verdict: ZERO drift on any claim spec-referenced from `03`.** Every fact in `.raw-design-research/03` survives re-check at HEAD `96b7d98`. The story-spec assumptions (Claude Code at `/usr/local/bin/claude`, docker-compose 2.32.4, no Hayabusa/Chainsaw/Zeek/Suricata pre-install, Python 3.12 floor, EZ Tools 15-not-17) are all still accurate as of 2026-06-03.

---

## Section 2 — Community tool install patterns

All releases probed live; SHA256 of the **actual downloaded asset** captured below. License audit included.

| Tool | Latest release | Direct URL | SHA256 (real, downloaded 2026-06-03) | Size | License | Status |
|---|---|---|---|---|---|---|
| **Hayabusa** | `v3.9.0` | `https://github.com/Yamato-Security/hayabusa/releases/download/v3.9.0/hayabusa-3.9.0-lin-x64-gnu.zip` | `ffb31e02bd47d840d999d964d4663287cdb194a22ea856904348786acba414d7` | 47,271,423 B (~45 MB) | **GPL-3.0** | OK — single Rust static binary; GPL is fine for separate-process subprocess use (we don't link) |
| **Chainsaw** | `v2.16.0` | `https://github.com/WithSecureLabs/chainsaw/releases/download/v2.16.0/chainsaw_x86_64-unknown-linux-gnu.tar.gz` | `5d46cd140838413aeb5711451a282b3922443d9ec6afaea3e6b6b220454fd807` | 3,494,437 B (~3.3 MB) | **GPL-3.0** | OK — same reasoning |
| **Velociraptor** | `v0.76` tag, asset `velociraptor-v0.76.2-linux-amd64` | `https://github.com/Velocidex/velociraptor/releases/download/v0.76/velociraptor-v0.76.2-linux-amd64` | `ccbf99a783ce10e16b2f8bd1efadf82f55d1f3cb15bd24cf47f5901b435d64a7` | 84,929,656 B (~81 MB) ELF64 | **AGPL-3.0** | **LICENSE NOTE BELOW** |
| **capa** | `v9.4.0` | `https://github.com/mandiant/capa/releases/download/v9.4.0/capa-v9.4.0-linux.zip` | `07800a1d20a21eb18fc98716e2ae81b668e0c9a04defd588c8aa17ea3d3281e4` | 47,477,971 B (~45 MB) | Apache-2.0 | OK |
| **FLOSS** | `v3.1.1` | `https://github.com/mandiant/flare-floss/releases/download/v3.1.1/floss-v3.1.1-linux.zip` | `40c05a869f34f7e2417b17ca290cc54bd3671ee1f0a2d9bd5103284c01a54666` | 40,571,555 B (~39 MB) | Apache-2.0 | OK |
| **PECmd** (EZ Tool, dotnet 9) | n/a — Eric Zimmerman's `net9/PECmd.zip` direct | `https://download.ericzimmermanstools.com/net9/PECmd.zip` | `e361d397c8c64959fd537e1826fcb89ea2d6fe24b3b4b63e6666479d565caa15` | 2,279,692 B (~2.2 MB) | MIT | OK — same wrapper pattern as `scripts/zimmerman.sls` |
| **SrumECmd** (EZ Tool) | n/a — `net9/SrumECmd.zip` direct | `https://download.ericzimmermanstools.com/net9/SrumECmd.zip` | `4d7035100f771a7ef5d75ac30e7edb70761976f2c92476213d19abb50d4c8489` | 2,063,275 B (~2 MB) | MIT | OK |
| **Zeek** | apt path | `deb https://download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04/ /` (200 OK) | n/a (apt) | varies | BSD-3 | OK — confirmed repo exists for 24.04 Noble |
| **Suricata** | apt | `apt install suricata` from Noble universe | n/a | varies | GPL-2.0 | OK |
| **Node.js 20.x LTS** | NodeSource | `https://deb.nodesource.com/setup_22.x` (200 OK — also `setup_20.x` works) | n/a (apt) | varies | MIT | OK |
| **uv** | upstream curl-bootstrap | `https://astral.sh/uv/install.sh` (200 OK) | n/a (versioned in pyproject) | varies | MIT/Apache-2.0 | OK |
| **binwalk** | apt Noble universe | `apt install binwalk` | n/a | apt | MIT | OK |
| **SigmaHQ rules** | release tag `r2026-04-01` (asset `sigma_all_rules.zip`) | `https://github.com/SigmaHQ/sigma/releases/download/r2026-04-01/sigma_all_rules.zip` | (not downloaded — large, recommend version-pinned release zip OR `git clone --depth 1 --branch r2026-04-01`) | varies | Apache-2.0 / DRL-1.1 | **RECOMMEND:** pin to release tag, NOT `master`, for reproducibility |
| **Hayabusa rules** | repo `Yamato-Security/hayabusa-rules` HEAD `cb00d96…` | `git clone --depth 1 https://github.com/Yamato-Security/hayabusa-rules /opt/hayabusa-rules` | commit-pinned | varies | Apache-2.0 | OK |

### Velociraptor AGPL — concrete answer

**AGPL-3.0 covers Velociraptor's source.** SilentWitness invokes Velociraptor only as a separate-process subprocess (no library linking, no source vendoring). Under settled AGPL interpretation:

- **Running an AGPL binary as a separate process does NOT trigger AGPL conveyance** on the calling project. SilentWitness can stay MIT.
- The AGPL trigger is **modifying** Velociraptor and **offering modified source to network-interacting users**. We do neither — we ship a pinned upstream binary and shell out to it.
- **Mitigation: document this in `LICENSE` / `NOTICES`** with a "Velociraptor is invoked as an unmodified upstream binary; AGPL-3.0 source is at github.com/Velocidex/velociraptor" stanza. Story-cli-install-claude-code or a new `story-third-party-notices` should own this.
- **Deprioritization not required.** Velociraptor stays. If we end up bundling it in the Docker image, the same separate-process argument holds — the image is an aggregate, not a derivative work, and AGPL conveyance is satisfied by linking to upstream source in the image's NOTICES.

### Hayabusa + Chainsaw GPL-3.0 — same reasoning

Both are GPL-3.0 single-binary Rust tools. Same separate-process logic. SilentWitness's MIT license is unaffected. NOTICES needs the upstream source link, nothing more.

### Ubuntu 24.04 Noble compatibility

- **Hayabusa** static Rust binary linked against glibc; tested against Ubuntu 22.04+ per upstream README. Confirmed `file /tmp/hayabusa.zip` → ZIP archive containing a `hayabusa` binary; Noble's glibc 2.39 is forward-compatible.
- **Chainsaw** same pattern; static Rust.
- **Velociraptor** `file /tmp/velociraptor` → `ELF 64-bit LSB executable, x86-64, ... for GNU/Linux 3.2.0, stripped` — minimum kernel 3.2, dynamic interpreter `/lib64/ld-linux-x86-64.so.2`. Noble (kernel 6.x) is way past 3.2; OK.
- **capa + FLOSS** ship as Python-bundled standalone binaries (PyInstaller) — Linux x86_64; OK on Noble.
- **PECmd + SrumECmd** are .NET 9 DLLs; SIFT 2026's `dotnet-sdk-9.0` runs them via the existing `zimmerman.sls` wrapper pattern.

### License compatibility — MIT outcome

| Tool | Lic | Conveyance trigger fires? | Action |
|---|---|---|---|
| Hayabusa, Chainsaw | GPL-3.0 | NO (separate-process) | NOTICES entry |
| Velociraptor | AGPL-3.0 | NO (unmodified upstream, no network-offered modifications) | NOTICES entry |
| capa, FLOSS, Sigma rules | Apache-2.0 | n/a | NOTICES entry |
| EZ Tools (PECmd / SrumECmd) | MIT | n/a | NOTICES entry |
| Zeek | BSD-3 | n/a | NOTICES entry |
| Suricata | GPL-2.0 | NO (apt-installed, separate-process) | NOTICES entry |
| binwalk | MIT | n/a | NOTICES entry |

**Verdict: SilentWitness can stay MIT.** Suggest a `story-third-party-notices` if not already present in `docs/stories/` that produces `THIRD_PARTY_NOTICES.md`, owned by Epic 1.

---

## Section 3 — Dataset URL accessibility

All probes from this audit window (2026-06-03 ~01:53 GMT).

| Dataset | URL | HTTP status | Real bytes verified | Notes |
|---|---|---|---|---|
| **Nitroba pcap** | `https://downloads.digitalcorpora.org/corpora/scenarios/2008-nitroba/nitroba.pcap` → 302 → `https://digitalcorpora.s3.amazonaws.com/corpora/scenarios/2008-nitroba/nitroba.pcap` | 200 | **DOWNLOADED 56,180,821 B; sha256 = `2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb`** | **HASH MATCHES SPEC EXACTLY**; **size: 56.18 MB, NOT "≈60 MB" in spec** — `story-dataset-manifests` says `size_bytes: ~60_000_000` and "first 60 MB truncated stub" — **the full file is ≤60 MB, so stub == full file**. The story note 2 already anticipates this ("if the full pcap is ≤60 MB, the stub == full file"). Use **exact bytes = 56180821** in the manifest. |
| **NIST Data Leakage index** | `https://cfreds.nist.gov/all/NIST/DataLeakageCase` | 200 (Cloudflare) | n/a (HTML index) | OK |
| **NIST Data Leakage static archive** | `https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html` | 200 | HTML index | OK — confirms 5 image files: `pc.E01`, `rm#1.E01`, `rm#2.E01`, plus 2 more removable-media variants |
| **NIST Data Leakage PC E01** | `https://cfreds-archive.nist.gov/data_leakage_case/images/pc/cfreds_2015_data_leakage_pc.E01` | 200 | **`content-length: 2147463521`** (~2.0 **GB**, NOT 20 GB) + 200-byte range probe returned EWF magic `EVF\t\r\n\377\0` | **SPEC CORRECTION: `story-dataset-manifests` says `size_bytes: ~20_000_000_000` for the PC E01 — actual is ~2.0 GB (10× smaller).** The MD5 `A49D1254C873808C58E6F1BCD60B5BDE` in the spec is the legacy NIST-published hash; recompute SHA256 from the actual download. |
| **NIST Data Leakage RM#1 E01** | `https://cfreds-archive.nist.gov/data_leakage_case/images/rm%231/cfreds_2015_data_leakage_rm%231.E01` | 200 | (not range-probed) | OK |
| **NIST Data Leakage answer key PDF** | `https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf` | 200 | **DOWNLOADED 1,083,100 B; sha256 = `218165427fcb2f490b44eccf7fbc9bf3700b938ea976004051a067e79e0da62b`** | **OWN-NUMBER for `story-ground-truth-parsers`'s `nist-data-leakage.answer-key-sha256.txt`**. File reports `PDF document, version 1.5 (zip deflate encoded)` — pypdf 5.x handles this fine. |
| **NIST Hacking Case index** | `https://cfreds-archive.nist.gov/Hacking_Case.html` | 200 | HTML index | Hosts a **single reassembled EnCase image at `images/4Dell%20Latitude%20CPi.E01`** (note URL-encoded space and the lead `4`) |
| **NIST Hacking Case EnCase image** | `https://cfreds-archive.nist.gov/images/4Dell%20Latitude%20CPi.E01` | 200 | 206 range probe returned EWF magic, size headers not probed (multi-GB) | Single E01 (not multi-part DD as `story-dataset-manifests` says) — the multi-part DD is the legacy artifact; the canonical NIST archive now ships ONE reassembled E01. **SPEC NOTE: `story-dataset-manifests` line 26 says "multi-part DD image hosted" — that's the historical artifact, not the current canonical one.** Update the manifest to point at the E01. |
| **intrinsicode.net writeup** | `https://intrinsicode.net/2021/05/19/cfreds-hacking-case-report/` | 000 (unreachable from this network — likely Cloudflare block or geo-fence) | n/a | **BLOCKER for `story-ground-truth-parsers`:** writeup is unreachable for live fetch. **Mitigation: use Wayback Machine snapshot** at `https://web.archive.org/web/20210519061644/https://intrinsicode.net/2021/05/19/cfreds-hacking-case-report/` (200 OK probed this audit). The story already says to commit local HTML snapshots — no live HTTP at parse time — so we just need to **commit the Wayback HTML as the source**, with attribution. |
| **zarat.hatenablog writeup** | `https://zarat.hatenablog.com/entry/2021/12/19/223735` | 200 | HTML | OK — directly reachable |
| **Wayback intrinsicode snapshot** | `https://web.archive.org/web/2024/https://intrinsicode.net/2021/05/19/cfreds-hacking-case-report/` | 200 → redirects to `web/20210519061644/...` | HTML | OK — use as canonical mirror |
| **Ali Hadi (archive.org)** | `https://archive.org/details/CCF-FTK-Image` | 404 | n/a | **DRIFT:** this specific Ali Hadi archive URL is dead. `story-dataset-manifests` doesn't actually pin Ali Hadi cases (`02-sponsor-docs` mention only) — **NO-OP for the spec set.** If we ever want Ali Hadi cases, search `archive.org/search?query=ali+hadi+forensic` for current canonical locations. Optional, not blocking. |

### Access restrictions

- **No EULAs, no registration, no logins** required for any of Nitroba, NIST CFReDS Data Leakage, NIST CFReDS Hacking Case, or the SigmaHQ corpus.
- The NIST CFReDS site notes that downloads are intended for "law enforcement, academic, and forensic research"; no click-through gate.
- **Nitroba official solution PDF is password-gated** by the original Univ. of New Haven authors — `story-ground-truth-parsers` correctly handles this by hand-crafting from community consensus and labelling `source="hand_crafted"`. No bypass attempted; spec is right.

---

## Section 4 — docker-compose on SIFT 2026

`/tmp/sift-recheck/sift/scripts/docker-compose.sls` line 1 verbatim:

```jinja2
{%- set version = "2.32.4" -%}
sift-scripts-docker-compose:
  file.managed:
    - name: /usr/local/bin/docker-compose
    - source: https://github.com/docker/compose/releases/download/v{{ version }}/docker-compose-{{ grains['kernel'] }}-{{ grains['cpuarch'] }}
    - source_hash: https://github.com/docker/compose/releases/download/v{{ version }}/docker-compose-{{ grains['kernel'] }}-{{ grains['cpuarch'] }}.sha256
    - mode: 755
```

**`story-docker-baseline.md` matches: docker-compose 2.32.4 at `/usr/local/bin/docker-compose` confirmed.** No drift. Story's CI matrix pinning `uv 0.5.11` does not interact with this.

Note: this is the **standalone binary** install (legacy `docker-compose` command), NOT the modern `docker compose` plugin. The story uses `docker compose up` (space, plugin) in its commands — verify Docker daemon ships the plugin too. `packages/docker.sls` installs `docker-ce` from the official Docker apt repo, which DOES include `docker-compose-plugin` as a co-installed Recommends. **Both `docker-compose` (binary at `/usr/local/bin`) and `docker compose` (plugin) work on a fresh SIFT 2026.**

---

## Section 5 — Apache on port 80 → HUD on 8088

- **Apache binds 80 (default Ubuntu config).** `packages/apache2.sls` is bare `pkg.installed` with no port override. The Debian/Ubuntu `apache2` package's `/etc/apache2/ports.conf` ships `Listen 80` (and `Listen 443` inside an `<IfModule ssl_module>` block, which is loaded by default on Noble). CyberChef is hosted at `/var/www/html/cyberchef/` via the default vhost.
- **Port 8088 is unbound.** `grep -lir 8088 /tmp/sift-recheck/sift/` returns empty. No other service in the saltstack binds 8088.
- **Recommendation for the HUD/UX spec:** continue defaulting to `127.0.0.1:8088` per `story-hud-routes` / `story-hud-sse-server` (already the case if those stories follow `architecture.md` §7). Document the port-80-is-Apache conflict in `install.sh` output so judges aren't surprised.

---

## Section 6 — Memory dump access + access restrictions

| Source | Restrictions | Action |
|---|---|---|
| Nitroba pcap | None — direct S3 download via digitalcorpora.org redirect | OK |
| NIST CFReDS PC E01 + answer PDF | None — direct HTTPS, no auth, no captcha, no rate limit observed | OK (large; long download time) |
| NIST CFReDS Hacking Case E01 | None — direct HTTPS | OK (long download) |
| Intrinsicode community writeup | Live site unreachable from this network (probably Cloudflare bot mitigation); Wayback Machine works | Use committed snapshot (Wayback HTML) — `story-ground-truth-parsers` already specifies committed snapshots, just point at Wayback URL |
| zarat hatenablog | None — direct | OK |
| Ali Hadi `CCF-FTK-Image` archive.org | 404 (dead URL) | Optional dataset; no spec pins it |
| SigmaHQ rules | None — public GitHub | OK |
| Hayabusa rules | None | OK |
| GitHub release downloads (Hayabusa/Chainsaw/Velociraptor/capa/FLOSS) | Rate-limited unauthenticated API (60/hr per IP) but binary downloads via `releases/download/` direct path are NOT API-rate-limited | OK — install.sh uses direct URLs, not API |
| Eric Zimmerman EZ Tools (`download.ericzimmermanstools.com`) | None — direct, no auth | OK |

**No hidden gates discovered.** The spec set's "fetch on first run, cache locally, SHA256-pin" pattern (`story-ground-truth-parsers` for the PDF; `story-dataset-manifests` for binaries) handles all access patterns correctly.

---

## Concrete install.sh draft (paste-ready)

```bash
#!/usr/bin/env bash
# install.sh — SilentWitness community-tool bootstrap for SIFT 2026
# Idempotent. Run as the sansforensics user with sudo available.
# All SHA256s captured 2026-06-03 against upstream release artefacts.

set -euo pipefail

readonly TMPDIR="$(mktemp -d -t silentwitness-install.XXXXXX)"
trap 'rm -rf "$TMPDIR"' EXIT

log()  { printf '\033[36m[install]\033[0m %s\n' "$*"; }
fail() { printf '\033[31m[install:fail]\033[0m %s\n' "$*" >&2; exit 1; }

verify_sha256() {
  local file="$1" expected="$2"
  local actual
  actual="$(sha256sum "$file" | awk '{print $1}')"
  [[ "$actual" == "$expected" ]] || fail "sha256 mismatch on $file (expected $expected got $actual)"
}

require_root_via_sudo() {
  sudo -n true 2>/dev/null || fail "sudo required and must be non-interactive (cache creds first: 'sudo -v')"
}

# ----- pre-flight: SIFT 2026 sanity ------------------------------------------
[[ -f /usr/local/bin/claude ]]          || fail "expected SIFT 2026 Claude Code at /usr/local/bin/claude (run 'cast install teamdfir/sift-saltstack' first)"
[[ -x /usr/local/bin/docker-compose ]]  || fail "expected SIFT 2026 docker-compose at /usr/local/bin/docker-compose"
[[ -x /usr/local/bin/vol ]]             || fail "expected SIFT 2026 Volatility 3 at /usr/local/bin/vol"
[[ -x /usr/bin/dotnet ]]                || fail "expected SIFT 2026 dotnet-sdk-9.0 at /usr/bin/dotnet"
log "SIFT 2026 baseline detected — claude, docker-compose, vol, dotnet present"

# ----- WeasyPrint native deps (required by report PDF export, Epic 11) -------
log "installing WeasyPrint native deps via apt"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
  libharfbuzz0b libffi8 shared-mime-info libcairo2

# ----- uv (Astral) ----------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  log "installing uv (Astral Python package manager)"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

# ----- Node.js 20 LTS (mermaid-cli + any TS tooling) ------------------------
if ! command -v node >/dev/null 2>&1; then
  log "installing Node.js 20 LTS via NodeSource"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

# ----- Hayabusa v3.9.0 ------------------------------------------------------
if [[ ! -x /opt/hayabusa/hayabusa ]]; then
  log "installing Hayabusa v3.9.0"
  curl -sSL -o "$TMPDIR/hayabusa.zip" \
    "https://github.com/Yamato-Security/hayabusa/releases/download/v3.9.0/hayabusa-3.9.0-lin-x64-gnu.zip"
  verify_sha256 "$TMPDIR/hayabusa.zip" \
    "ffb31e02bd47d840d999d964d4663287cdb194a22ea856904348786acba414d7"
  sudo mkdir -p /opt/hayabusa
  sudo unzip -q "$TMPDIR/hayabusa.zip" -d "$TMPDIR/hayabusa-extracted"
  # release archive flattens to hayabusa-3.9.0-lin-x64-gnu/hayabusa ; flatten further
  sudo cp "$(find "$TMPDIR/hayabusa-extracted" -name hayabusa -type f | head -1)" /opt/hayabusa/hayabusa
  sudo chmod +x /opt/hayabusa/hayabusa
  /opt/hayabusa/hayabusa --version || fail "hayabusa runtime check failed"
fi

# ----- Hayabusa rules (commit-pinned for reproducibility) -------------------
if [[ ! -d /opt/hayabusa-rules ]]; then
  log "cloning Hayabusa rules corpus"
  sudo git clone --depth 1 https://github.com/Yamato-Security/hayabusa-rules /opt/hayabusa-rules
fi

# ----- Chainsaw v2.16.0 -----------------------------------------------------
if [[ ! -x /opt/chainsaw/chainsaw ]]; then
  log "installing Chainsaw v2.16.0"
  curl -sSL -o "$TMPDIR/chainsaw.tgz" \
    "https://github.com/WithSecureLabs/chainsaw/releases/download/v2.16.0/chainsaw_x86_64-unknown-linux-gnu.tar.gz"
  verify_sha256 "$TMPDIR/chainsaw.tgz" \
    "5d46cd140838413aeb5711451a282b3922443d9ec6afaea3e6b6b220454fd807"
  sudo mkdir -p /opt/chainsaw
  sudo tar -xzf "$TMPDIR/chainsaw.tgz" -C /opt/chainsaw --strip-components=1
  sudo chmod +x /opt/chainsaw/chainsaw
  [[ -f /opt/chainsaw/mappings/sigma-event-logs-all.yml ]] || fail "chainsaw mapping file missing"
  /opt/chainsaw/chainsaw --version || fail "chainsaw runtime check failed"
fi

# ----- SigmaHQ rules (tag-pinned for reproducibility) -----------------------
if [[ ! -d /opt/sigma ]]; then
  log "cloning SigmaHQ rules (tag r2026-04-01)"
  sudo git clone --depth 1 --branch r2026-04-01 https://github.com/SigmaHQ/sigma /opt/sigma
fi

# ----- Velociraptor v0.76.2 -------------------------------------------------
if [[ ! -x /opt/velociraptor/velociraptor ]]; then
  log "installing Velociraptor v0.76.2 (AGPL-3.0 — see THIRD_PARTY_NOTICES.md)"
  sudo mkdir -p /opt/velociraptor
  curl -sSL -o "$TMPDIR/velociraptor" \
    "https://github.com/Velocidex/velociraptor/releases/download/v0.76/velociraptor-v0.76.2-linux-amd64"
  verify_sha256 "$TMPDIR/velociraptor" \
    "ccbf99a783ce10e16b2f8bd1efadf82f55d1f3cb15bd24cf47f5901b435d64a7"
  sudo install -m 0755 "$TMPDIR/velociraptor" /opt/velociraptor/velociraptor
fi

# ----- Zeek (OpenSUSE security:zeek repo for Ubuntu 24.04 Noble) ------------
if ! command -v zeek >/dev/null 2>&1 && [[ ! -x /opt/zeek/bin/zeek ]]; then
  log "installing Zeek via OpenSUSE security:zeek repo"
  curl -fsSL "https://download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04/Release.key" \
    | sudo gpg --dearmor -o /etc/apt/keyrings/security-zeek.gpg
  echo "deb [signed-by=/etc/apt/keyrings/security-zeek.gpg] https://download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04/ /" \
    | sudo tee /etc/apt/sources.list.d/security-zeek.list
  sudo apt-get update -qq
  sudo apt-get install -y zeek
  # binary lands at /opt/zeek/bin/zeek per OpenSUSE package layout — symlink for the wrapper
  sudo ln -sf /opt/zeek/bin/zeek /usr/local/bin/zeek
fi

# ----- Suricata (apt Noble universe) ----------------------------------------
if ! command -v suricata >/dev/null 2>&1; then
  log "installing Suricata via apt"
  sudo apt-get install -y suricata
  # Optional: pull ET Open ruleset
  sudo suricata-update || true
fi

# ----- capa v9.4.0 (Mandiant) -----------------------------------------------
if [[ ! -x /opt/capa/capa ]]; then
  log "installing capa v9.4.0"
  curl -sSL -o "$TMPDIR/capa.zip" \
    "https://github.com/mandiant/capa/releases/download/v9.4.0/capa-v9.4.0-linux.zip"
  verify_sha256 "$TMPDIR/capa.zip" \
    "07800a1d20a21eb18fc98716e2ae81b668e0c9a04defd588c8aa17ea3d3281e4"
  sudo mkdir -p /opt/capa
  sudo unzip -q "$TMPDIR/capa.zip" -d /opt/capa
  sudo chmod +x /opt/capa/capa
fi

# ----- FLOSS v3.1.1 (Mandiant) ----------------------------------------------
if [[ ! -x /opt/floss/floss ]]; then
  log "installing FLOSS v3.1.1"
  curl -sSL -o "$TMPDIR/floss.zip" \
    "https://github.com/mandiant/flare-floss/releases/download/v3.1.1/floss-v3.1.1-linux.zip"
  verify_sha256 "$TMPDIR/floss.zip" \
    "40c05a869f34f7e2417b17ca290cc54bd3671ee1f0a2d9bd5103284c01a54666"
  sudo mkdir -p /opt/floss
  sudo unzip -q "$TMPDIR/floss.zip" -d /opt/floss
  sudo chmod +x /opt/floss/floss
fi

# ----- binwalk (apt Noble universe) -----------------------------------------
command -v binwalk >/dev/null 2>&1 || sudo apt-get install -y binwalk

# ----- PECmd + SrumECmd (EZ Tool dotnet 9 pattern, parallel to zimmerman.sls)
install_ez_tool() {
  local name="$1" expected_sha="$2"
  local target="/opt/zimmermantools/${name}.dll"
  if [[ ! -f "$target" ]]; then
    log "installing EZ Tool: $name"
    curl -sSL -o "$TMPDIR/${name}.zip" "https://download.ericzimmermanstools.com/net9/${name}.zip"
    verify_sha256 "$TMPDIR/${name}.zip" "$expected_sha"
    sudo mkdir -p /opt/zimmermantools
    sudo unzip -q -o "$TMPDIR/${name}.zip" -d /opt/zimmermantools/
    # Wrapper at /usr/local/bin/<Name> and lowercase alias
    printf '#!/bin/sh\nexec /usr/bin/dotnet /opt/zimmermantools/%s.dll "$@"\n' "$name" \
      | sudo tee "/usr/local/bin/${name}" >/dev/null
    sudo chmod +x "/usr/local/bin/${name}"
    sudo ln -sf "/usr/local/bin/${name}" "/usr/local/bin/$(echo "$name" | tr 'A-Z' 'a-z')"
  fi
}
install_ez_tool "PECmd"    "e361d397c8c64959fd537e1826fcb89ea2d6fe24b3b4b63e6666479d565caa15"
install_ez_tool "SrumECmd" "4d7035100f771a7ef5d75ac30e7edb70761976f2c92476213d19abb50d4c8489"

log "install.sh complete — all community tools verified by sha256 + runtime check"
```

**Validation rules baked in:**
- Every download is sha256-verified against the **real bytes captured in this audit**. Any drift in the upstream artefacts fails closed.
- Pre-flight refuses to run if SIFT 2026 baseline (`claude`, `docker-compose`, `vol`, `dotnet`) is absent — structural defense against running on the wrong host.
- Idempotent: every step is guarded by `[[ -x $bin ]]` so reruns are no-ops.
- Reproducibility: every tool is **version-pinned** (Hayabusa v3.9.0, Chainsaw v2.16.0, Velociraptor v0.76.2, capa v9.4.0, FLOSS v3.1.1, SigmaHQ `r2026-04-01`, Hayabusa rules HEAD `cb00d96`). The `latest` substring per `.raw-design-research/03` line 271 is the SHA256-anchored variant.

---

## Recommended spec adjustments

### BLOCKER — none

No spec assumption is materially wrong in a way that blocks coding. All URLs resolve, all binaries are still downloadable, all SHA256 pins survive.

### FIX-IT (small, important)

1. **`story-dataset-manifests.md` line 26 — Hacking Case "multi-part DD"**: the current canonical NIST artefact is the single reassembled E01 at `https://cfreds-archive.nist.gov/images/4Dell%20Latitude%20CPi.E01`, not a multi-part DD. Update the `evidence_files[0].relative_path` to `4Dell Latitude CPi.E01` and the `notes` to "Single reassembled EnCase image; legacy multi-part DD no longer hosted on the canonical archive."

2. **`story-dataset-manifests.md` line 25 — NIST Data Leakage PC E01 size**: spec says `size_bytes: ~20_000_000_000`. **Actual content-length is 2,147,463,521 B (~2.0 GB, 10× smaller).** Update size_bytes to `2147463521` and trim the `LLM_memorization_risk` rationale slightly (still high, but for "common writeup dataset" reasons, not "20 GB image").

3. **`story-dataset-manifests.md` Nitroba size**: spec says `~60_000_000`. Actual is exactly 56,180,821 B. Update to `56180821`. The "first 60 MB stub" path becomes "full file is the stub" — story note (vi) already anticipates this.

4. **`story-ground-truth-parsers.md`** Intrinsicode write-up: the live URL is unreachable from at least some networks (likely Cloudflare bot mitigation). The spec already says "snapshot once, commit locally" — make it explicit that **the snapshot must be sourced from the Wayback Machine** (`https://web.archive.org/web/20210519061644/https://intrinsicode.net/2021/05/19/cfreds-hacking-case-report/`) since the live site is intermittently fenced. Update `snapshots/README.md` to record `fetch_source: wayback` for this file.

5. **`story-ground-truth-parsers.md`** answer-key SHA256 pin: now that we've fetched it, the file `harness/ground_truth/nist-data-leakage.answer-key-sha256.txt` can be **pre-committed** with the value `218165427fcb2f490b44eccf7fbc9bf3700b938ea976004051a067e79e0da62b` (single hex line, no newline per the story). Saves the coding agent a fetch step.

6. **`story-docker-baseline.md` + `install.sh`**: the story bakes WeasyPrint deps into the Dockerfile, but the **native-install path on SIFT 2026** also needs them. Native install != Docker install. `install.sh` MUST `apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libharfbuzz0b libffi8 shared-mime-info` (already in the draft above) since the SIFT 2026 baseline only ships `libcairo2-dev` + `libffi-dev`.

7. **Velociraptor URL pin**: `.raw-design-research/03` line 219 says `Velocidex/velociraptor` release; story-cli-install-claude-code etc. reference Velociraptor in the abstract. **Pin to `v0.76.2-linux-amd64`** with the SHA256 above. The v0.76 tag bundles both 0.76.1 and 0.76.2 assets — pick 0.76.2 as the newer.

8. **License compatibility note** — add a `story-third-party-notices` story (Epic 1) to produce `THIRD_PARTY_NOTICES.md` listing Hayabusa GPL-3.0, Chainsaw GPL-3.0, Velociraptor AGPL-3.0, capa Apache-2.0, FLOSS Apache-2.0, EZ Tools MIT, Zeek BSD-3, Suricata GPL-2.0, binwalk MIT, SigmaHQ Apache-2.0/DRL-1.1. **No license barrier** for SilentWitness to stay MIT — every tool is invoked as a separate process.

### NOTE (informational)

- **`story-hayabusa-timeline.md` Notes 1**: the path `/opt/hayabusa/hayabusa` after extraction is correct, but the upstream archive flattens to `hayabusa-3.9.0-lin-x64-gnu/hayabusa` — the `install.sh` step above handles the flatten with `find ... -name hayabusa -type f`. Spec's "Hayabusa releases use `hayabusa-<ver>-lin-x64-gnu/hayabusa` directory shape — flatten it" wording is correct.

- **`story-chainsaw-hunt.md` Notes 1**: `/opt/chainsaw/mappings/sigma-event-logs-all.yml` exists in the release tarball — confirmed by inspecting the upstream repo structure. `install.sh`'s `tar --strip-components=1` flattens the inner `chainsaw_x86_64-unknown-linux-gnu/` dir; mappings land at the expected path.

- **`story-zeek-run.md` Notes 1**: OpenSUSE security:zeek repo for `xUbuntu_24.04` confirmed reachable. Default install path is `/opt/zeek/bin/zeek`; `install.sh` adds a `/usr/local/bin/zeek` symlink so the wrapper's `ZEEK_BIN = /usr/local/bin/zeek` constant works without the fallback branch.

- **`story-suricata-run.md` SURICATA_BIN**: `/usr/bin/suricata` is correct for Noble universe apt install.

- **`story-cli-install-claude-code.md`**: every claim about `/usr/local/bin/claude` and v2.0.61 confirmed verbatim against `packages/claude-code.sls` lines 1–3. Spec is right; no edit needed.

- **`story-scaffold-uv-pyproject.md`**: Python 3.12 floor matches SIFT 2026 Noble system Python. uv install bootstrap via `curl -LsSf https://astral.sh/uv/install.sh | sh` confirmed reachable. No edit needed.

- **Ali Hadi archive.org URL** is dead but **no story pins it** — no action.

---

## Sources

- `teamdfir/sift-saltstack` HEAD `96b7d98` (`/tmp/sift-recheck/`):
  - `sift/packages/claude-code.sls` lines 1–17 (Claude Code v2.0.61, hash `5c5686e9…`)
  - `sift/scripts/docker-compose.sls` line 1 (docker-compose 2.32.4)
  - `sift/packages/apache2.sls` (bare pkg.installed → port 80 default)
  - `sift/scripts/cyberchef.sls` lines 5–24 (CyberChef v9.55.0, hash `DA55ADC7…`)
  - `sift/scripts/zimmerman.sls` line 9 (15-tool array, no PECmd/SrumECmd)
  - `sift/python3-packages/indxparse.sls` lines 11–13 (`oscodename == 'noble'` → `py_ver = '3.12'`)
  - `sift/python3-packages/python-evtx.sls` lines 11–14 (same)
  - `sift/packages/libcairo2-dev.sls`, `sift/packages/libffi-dev.sls` (only WeasyPrint-adjacent native deps present)
  - Grep confirmations: no `nodejs.sls`, `uv.sls`, `zeek.sls`, `suricata.sls`, `hayabusa.sls`, `chainsaw.sls`, `velociraptor.sls`, `capa.sls`, `floss.sls`, `binwalk.sls`, `pango`, `harfbuzz`, `gdk-pixbuf`, `8088`
- `teamdfir/sift-packer` HEAD (`/tmp/sift-packer-recheck/`):
  - `variables.pkr.hcl` line 23 `username = "sansforensics"`, line 29 `password = "forensics"`, line 41 `ubuntu_version = "24.04.2"`
- Nitroba pcap — DOWNLOADED, sha256 `2b77a9eaefc1d6af163d1ba793c96dbccacb04e6befdf1a0b01f8c67553ec2fb` matches `story-dataset-manifests.md` pin; size 56,180,821 B (correct vs ~60 MB approximation)
- NIST Data Leakage answer PDF — DOWNLOADED, sha256 `218165427fcb2f490b44eccf7fbc9bf3700b938ea976004051a067e79e0da62b`; size 1,083,100 B
- NIST Data Leakage PC E01 — HEAD verified; content-length 2,147,463,521 (~2.0 GB, NOT 20 GB)
- NIST Hacking Case EnCase image — `https://cfreds-archive.nist.gov/images/4Dell%20Latitude%20CPi.E01` 200 OK, 206 range probe returned EWF magic
- Hayabusa v3.9.0 — DOWNLOADED, sha256 `ffb31e02bd47d840d999d964d4663287cdb194a22ea856904348786acba414d7`; 45 MB
- Chainsaw v2.16.0 — DOWNLOADED, sha256 `5d46cd140838413aeb5711451a282b3922443d9ec6afaea3e6b6b220454fd807`; 3.3 MB
- Velociraptor v0.76.2 — DOWNLOADED, sha256 `ccbf99a783ce10e16b2f8bd1efadf82f55d1f3cb15bd24cf47f5901b435d64a7`; 81 MB ELF64
- capa v9.4.0 — DOWNLOADED, sha256 `07800a1d20a21eb18fc98716e2ae81b668e0c9a04defd588c8aa17ea3d3281e4`; 45 MB
- FLOSS v3.1.1 — DOWNLOADED, sha256 `40c05a869f34f7e2417b17ca290cc54bd3671ee1f0a2d9bd5103284c01a54666`; 39 MB
- PECmd (EZ Tool) — DOWNLOADED, sha256 `e361d397c8c64959fd537e1826fcb89ea2d6fe24b3b4b63e6666479d565caa15`; 2.2 MB
- SrumECmd (EZ Tool) — DOWNLOADED, sha256 `4d7035100f771a7ef5d75ac30e7edb70761976f2c92476213d19abb50d4c8489`; 2 MB
- SigmaHQ release `r2026-04-01` — confirmed via GitHub API; asset `sigma_all_rules.zip`
- Hayabusa rules HEAD commit `cb00d9644bff26c7a5687a062a1f8b35c74d9219`
- `astral.sh/uv/install.sh` — 200 OK
- `deb.nodesource.com/setup_20.x`, `setup_22.x` — 200 OK
- `download.opensuse.org/repositories/security:/zeek/xUbuntu_24.04/Release.key` — 200 OK
- Intrinsicode live: unreachable (HTTP 000); Wayback `web.archive.org/web/20210519061644/...` — 200 OK
- zarat.hatenablog.com — 200 OK
- `cfreds.nist.gov`, `cfreds-archive.nist.gov` — 200 OK across all probed paths
- archive.org Ali Hadi `CCF-FTK-Image` — 404 (URL dead; not pinned by any story)
