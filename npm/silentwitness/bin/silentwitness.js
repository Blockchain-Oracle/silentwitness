#!/usr/bin/env node
/**
 * SilentWitness npm wrapper — DISCOVERABILITY ALIAS, not a functional install.
 *
 * SilentWitness is a Python CLI (it lives at src/silentwitness_agent/cli.py and
 * is installed by `uv tool install silentwitness` or `pipx install silentwitness`).
 * This wrapper just locates the Python entry point and execs into it so users
 * who arrived via `npm i -g silentwitness` get the same UX.
 *
 * Resolution order:
 *   1. `silentwitness` already on PATH (user installed via uv/pipx earlier) → exec
 *   2. `uvx silentwitness` is available → exec uvx
 *   3. Neither → print the install instructions and exit non-zero
 *
 * No Python install is attempted from Node. Mixing package managers across
 * runtimes is a debugging nightmare; we delegate cleanly instead — and the
 * install-help message at the bottom says so explicitly.
 *
 * Hardened per PR #238 silent-failure review:
 * - `command -v` runs via `spawnSync` with `shell: false`. The prior
 *   `execSync(\`command -v ${cmd}\`)` interpolated through a shell, which
 *   was a footgun for any future caller that pulled the cmd from user input
 *   (RCE via shell metachars). Today's call sites pass literals, but the
 *   hardening removes the foot from the gun.
 * - Errors are classified, not blanket-caught: `ENOENT` on `sh` itself is
 *   reported distinctly from "binary not found". Silent fall-through to the
 *   install-help when the underlying error is `EACCES` / OOM / kill is the
 *   exact pattern that masks real bugs.
 */

"use strict";

const { spawnSync } = require("child_process");

/**
 * Return true iff the given command resolves on PATH.
 *
 * Returns `false` only for "binary not present" (the `command -v` exit
 * status is 1 on miss). Any other failure mode — child process couldn't
 * spawn (ENOENT on /bin/sh, EACCES, OOM, killed by signal) — re-throws
 * with a clear classification so the user sees what actually went wrong
 * instead of the install-help message that doesn't apply.
 */
function isOnPath(cmd) {
  const result = spawnSync("sh", ["-c", `command -v "${cmd}"`], {
    stdio: "ignore",
    shell: false,
  });
  if (result.error) {
    // Most common cause on systems with broken minimal images.
    if (result.error.code === "ENOENT") {
      throw new Error(
        `silentwitness wrapper: cannot find /bin/sh (ENOENT) — the wrapper requires a POSIX shell to probe PATH`,
      );
    }
    throw new Error(
      `silentwitness wrapper: PATH probe for '${cmd}' failed: ${result.error.message} (${result.error.code})`,
    );
  }
  if (result.signal) {
    throw new Error(
      `silentwitness wrapper: PATH probe for '${cmd}' was killed by signal ${result.signal}`,
    );
  }
  // exit 0 → present; exit 1 → missing; anything else is unexpected.
  if (result.status === 0) return true;
  if (result.status === 1) return false;
  throw new Error(
    `silentwitness wrapper: PATH probe for '${cmd}' exited ${result.status} (expected 0 or 1)`,
  );
}

function execAndExit(cmd, args) {
  const result = spawnSync(cmd, args, { stdio: "inherit", shell: false });
  if (result.error) {
    process.stderr.write(
      `silentwitness wrapper: failed to spawn ${cmd}: ${result.error.message} (${result.error.code})\n`,
    );
    process.exit(1);
  }
  if (result.signal) {
    process.stderr.write(`silentwitness wrapper: ${cmd} killed by signal ${result.signal}\n`);
    process.exit(128 + 15); // SIGTERM convention
  }
  process.exit(result.status === null ? 1 : result.status);
}

function printInstallHelp() {
  process.stderr.write(`
SilentWitness is a Python CLI. This npm package is a discoverability alias —
the wrapper deliberately does NOT bootstrap Python (mixing package managers
across runtimes is a debugging nightmare; we delegate cleanly instead).

You need Python 3.12+ and one of these commands:

  Recommended (uv tool — fastest):
    curl -LsSf https://astral.sh/uv/install.sh | sh   # install uv
    uv tool install silentwitness                     # install CLI globally

  Alternative (pipx):
    pipx install silentwitness

  SIFT 2026 OVA (subprocess tools + CLI in one step):
    curl -sSf https://raw.githubusercontent.com/Blockchain-Oracle/silentwitness/main/install.sh | bash

After install, retry the command. Project: https://github.com/Blockchain-Oracle/silentwitness
`);
}

const args = process.argv.slice(2);

try {
  if (isOnPath("silentwitness")) {
    execAndExit("silentwitness", args);
  }
  if (isOnPath("uvx")) {
    execAndExit("uvx", ["--from", "silentwitness", "silentwitness", ...args]);
  }
} catch (err) {
  // Probe failure (ENOENT on sh, OOM, signal) — surface it clearly, do NOT
  // fall through to the install-help (which would imply "not installed"
  // when the real cause is something else entirely).
  process.stderr.write(`${err.message}\n`);
  process.exit(2);
}

printInstallHelp();
process.exit(127);
