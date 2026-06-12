"""install --claude-code command — namespaced Claude Code drop-in config (architecture §6.3)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from rich.console import Console

# SIFT 2026 pre-installed Claude Code path — context/.raw-design-research/03 line 31
_SIFT_CLAUDE_PATH: Final = Path("/usr/local/bin/claude")
_TARGET_DIR_NAME: Final = Path(".claude") / "silentwitness"
_CONFIG_DIR_NAME: Final = "claude-code-config"

_REQUIRED_FILES: Final = ("CLAUDE.md", "settings.json")

_REQUIRED_MCP_BLOCK: Final[dict[str, object]] = {
    "type": "stdio",
    "command": "python",
    "args": ["-m", "silentwitness_mcp"],
}

_REQUIRED_DENY_ENTRIES: Final = frozenset(
    {
        "Bash(silentwitness approve*)",
        "Edit(cases/*/audit/*.jsonl)",
        "Edit(cases/*/evidence.json)",
        "Edit(/var/lib/silentwitness/**)",
    }
)


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from start until pyproject.toml is found."""
    current = start.resolve()
    for _ in range(20):
        if (current / "pyproject.toml").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _strip_jsonc_comments(text: str) -> str:
    """Strip // line comments from JSONC text.

    Caveat: the regex also strips // sequences that appear inside quoted strings.
    This is acceptable because our bundled settings.json has no // inside values.
    """
    return re.sub(r"//[^\n]*", "", text)


def _verify_settings_structure(settings_path: Path, *, err: Console) -> bool:
    """Return True if settings.json has the required MCP block and deny entries."""
    try:
        raw = settings_path.read_text(encoding="utf-8")
        parsed = json.loads(_strip_jsonc_comments(raw))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        err.print(f"[red]✗[/red] settings.json parse error: {exc}", highlight=False)
        return False

    mcp_block = (parsed.get("mcpServers") or {}).get("silentwitness")
    if mcp_block is None:
        err.print(
            "[red]✗[/red] settings.json missing mcpServers.silentwitness block",
            highlight=False,
        )
        return False
    for key, expected in _REQUIRED_MCP_BLOCK.items():
        if mcp_block.get(key) != expected:
            err.print(
                f"[red]✗[/red] settings.json mcpServers.silentwitness.{key}="
                f"{mcp_block.get(key)!r} (expected {expected!r})",
                highlight=False,
            )
            return False

    deny_list: list[str] = (parsed.get("permissions") or {}).get("deny") or []
    deny_set = set(deny_list)
    missing = _REQUIRED_DENY_ENTRIES - deny_set
    if missing:
        err.print(
            f"[red]✗[/red] settings.json deny list missing required entries: {missing}",
            highlight=False,
        )
        return False
    return True


def _sha256_content(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    *,
    claude_code: bool,
    cursor: bool,
    continue_ide: bool,
    dry_run: bool,
    force: bool,
    no_color: bool,
) -> int:
    """Run the install command. Returns exit code."""
    out = Console(no_color=no_color)
    err = Console(stderr=True, no_color=no_color)

    if cursor or continue_ide:
        out.print(
            "[yellow]⚠[/yellow] --cursor / --continue not yet implemented; Claude Code only in v1",
            highlight=False,
        )
        return 0

    if not claude_code:
        err.print(
            "[red]✗[/red] specify --claude-code (--cursor/--continue not yet implemented)",
            highlight=False,
        )
        return 2

    # Locate the repo root and source config directory
    repo_root = _find_repo_root(Path(__file__))
    if repo_root is None:
        err.print(
            "[red]✗[/red] could not locate repo root (pyproject.toml not found from "
            f"{Path(__file__).parent})",
            highlight=False,
        )
        return 2
    config_src = repo_root / _CONFIG_DIR_NAME
    for fname in _REQUIRED_FILES:
        if not (config_src / fname).exists():
            err.print(
                f"[red]✗[/red] {_CONFIG_DIR_NAME}/{fname} not found in repo "
                f"(expected at {config_src / fname})",
                highlight=False,
            )
            return 2

    # Detect Claude Code binary (SIFT 2026 path + PATH fallback)
    if not _SIFT_CLAUDE_PATH.exists() and not shutil.which("claude"):
        err.print(
            "[red]✗[/red] Claude Code not found at /usr/local/bin/claude "
            "(SIFT 2026 pre-installed path) and 'claude' is not on PATH. "
            "Install Claude Code v2.0.61 first.",
            highlight=False,
        )
        return 2

    # Verify source settings.json is well-formed before writing anything to disk
    if not _verify_settings_structure(config_src / "settings.json", err=err):
        return 2

    target_dir = Path.home() / _TARGET_DIR_NAME

    if dry_run:
        out.print("[yellow]--dry-run[/yellow] (no files will be written):", highlight=False)
        for fname in _REQUIRED_FILES:
            out.print(
                f"  would copy {config_src / fname} → {target_dir / fname}",
                highlight=False,
            )
        return 0

    # Install files
    target_dir.mkdir(parents=True, exist_ok=True)
    all_unchanged = True
    for fname in _REQUIRED_FILES:
        src = config_src / fname
        dst = target_dir / fname
        src_hash = _sha256_content(src)

        if dst.exists():
            dst_hash = _sha256_content(dst)
            if src_hash == dst_hash:
                out.print(
                    f"[yellow]⚠[/yellow] {fname} unchanged (already installed)",
                    highlight=False,
                )
                continue
            if not force:
                err.print(
                    f"[red]✗[/red] existing {dst} differs from repo version; "
                    "use --force to overwrite",
                    highlight=False,
                )
                return 1
            ts = int(datetime.now(UTC).timestamp())
            backup = dst.with_name(f"{fname}.bak.{ts}")
            shutil.copy2(dst, backup)
            out.print(f"  backed up {dst.name} → {backup.name}", highlight=False)
            all_unchanged = False
        else:
            all_unchanged = False

        dst.write_bytes(src.read_bytes())
        out.print(f"  installed {fname}", highlight=False)

    if not all_unchanged:
        out.print(
            f"[green]✓[/green] installed to {target_dir}",
            highlight=False,
        )

    # Post-install verification of settings.json
    settings_dst = target_dir / "settings.json"
    if not _verify_settings_structure(settings_dst, err=err):
        return 2

    out.print(
        "\nto use with Claude Code:\n"
        "  1. cd into a SilentWitness case directory: cd cases/<case-id>/\n"
        "  2. launch Claude Code: claude\n"
        "  3. Claude Code will pick up "
        f"{target_dir / 'settings.json'}\n"
        "     and connect to the SilentWitness MCP server automatically.",
        highlight=False,
    )
    return 0
