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
 * runtimes is a debugging nightmare; we delegate cleanly instead.
 */

"use strict";

const { spawnSync, execSync } = require("child_process");
const { existsSync } = require("fs");

function canExec(cmd) {
  try {
    execSync(`command -v ${cmd}`, { stdio: "ignore" });
    return true;
  } catch (_) {
    return false;
  }
}

function execAndExit(cmd, args) {
  const result = spawnSync(cmd, args, { stdio: "inherit" });
  if (result.error) {
    process.stderr.write(`silentwitness: failed to spawn ${cmd}: ${result.error.message}\n`);
    process.exit(1);
  }
  process.exit(result.status === null ? 1 : result.status);
}

function printInstallHelp() {
  process.stderr.write(`
SilentWitness is a Python CLI. The npm package is a discoverability alias —
the actual install needs Python 3.12+ and one of these commands:

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

// 1. Native Python install on PATH wins — no extra hop.
if (canExec("silentwitness")) {
  execAndExit("silentwitness", args);
}

// 2. uvx is the runner Python's uv ships with; runs an ephemeral env.
if (canExec("uvx")) {
  execAndExit("uvx", ["--from", "silentwitness", "silentwitness", ...args]);
}

// 3. Neither — print the install instructions.
printInstallHelp();
process.exit(127);
