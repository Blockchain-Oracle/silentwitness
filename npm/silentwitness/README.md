# silentwitness (npm)

> Discoverability alias for the **SilentWitness** Python CLI.

This npm package does NOT install SilentWitness — it locates the Python CLI (installed via `uv tool install silentwitness` or `pipx install silentwitness`) and execs into it. Users who arrive via `npm i -g silentwitness` get the same UX without us forking the install story across two package managers.

## Install

```bash
npm install -g silentwitness
```

You'll also need the Python CLI installed:

```bash
# Recommended (uv tool)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install silentwitness

# Or via pipx
pipx install silentwitness
```

After both, `silentwitness investigate <case>` works from anywhere.

## Why both managers?

- **uv / pipx**: the actual Python package + dependencies. This is the source of truth.
- **npm**: discoverability. People search npm for CLI tools too. `npm i -g silentwitness` should "just work" rather than 404.

The npm wrapper is ~80 lines of Node and does no heavy lifting — it execs `silentwitness` (or `uvx silentwitness` as a fallback) and prints honest install instructions if neither is available.

## Links

- Project: https://github.com/Blockchain-Oracle/silentwitness
- License: MIT
