"""Integration tests for `silentwitness install --claude-code` command (≥10 BDD scenarios)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app

_runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _invoke(*args: str) -> object:
    return _runner.invoke(app, list(args), catch_exceptions=False)


def _has_claude(tmp_path: Path) -> Path:
    """Create a fake claude binary and return its path."""
    claude = tmp_path / "claude"
    claude.write_text("#!/bin/sh\nexec true\n")
    claude.chmod(0o755)
    return claude


def _patch_claude_found() -> object:
    """Patch binary detection so tests don't depend on /usr/local/bin/claude."""
    return patch(
        "silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH",
        new_callable=lambda: property(lambda _: Path("/usr/local/bin/claude")),
    )


# ---------------------------------------------------------------------------
# 1. Happy-path install: files copied to $HOME/.claude/silentwitness/
# ---------------------------------------------------------------------------


def test_happy_path_installs_both_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path: both CLAUDE.md and settings.json are copied to the target dir."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        result = _invoke("install", "--claude-code")
    target = tmp_path / ".claude" / "silentwitness"
    assert (target / "CLAUDE.md").exists(), "CLAUDE.md not installed"
    assert (target / "settings.json").exists(), "settings.json not installed"
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# 2. Missing Claude binary exits 2 with SIFT path quoted in stderr
# ---------------------------------------------------------------------------


def test_missing_claude_binary_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with (
        patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "no-claude"),
        patch("silentwitness_agent.cli_commands.install.shutil.which", return_value=None),
    ):
        result = _invoke("install", "--claude-code")
    assert result.exit_code == 2
    assert "/usr/local/bin/claude" in result.stderr or "/usr/local/bin/claude" in result.output


# ---------------------------------------------------------------------------
# 3. Idempotent install — same content does not re-write
# ---------------------------------------------------------------------------


def test_idempotent_install_same_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Installing twice with identical content is a no-op (no error, no write)."""
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / ".claude" / "silentwitness"
    target.mkdir(parents=True)
    with patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        _invoke("install", "--claude-code")
        mtime_md = (target / "CLAUDE.md").stat().st_mtime_ns
        result = _invoke("install", "--claude-code")
    assert result.exit_code == 0
    assert (target / "CLAUDE.md").stat().st_mtime_ns == mtime_md, "file was re-written"
    assert "unchanged" in result.output


# ---------------------------------------------------------------------------
# 4. Existing file with different content + no --force exits 1
# ---------------------------------------------------------------------------


def test_existing_different_content_no_force_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / ".claude" / "silentwitness"
    target.mkdir(parents=True)
    (target / "CLAUDE.md").write_text("old content")
    with patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        result = _invoke("install", "--claude-code")
    assert result.exit_code == 1
    combined = result.stderr + result.output
    assert "differs" in combined or "--force" in combined
    assert (target / "CLAUDE.md").read_text() == "old content"


# ---------------------------------------------------------------------------
# 5. --force overwrites existing file and creates backup
# ---------------------------------------------------------------------------


def test_force_overwrites_and_creates_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    target = tmp_path / ".claude" / "silentwitness"
    target.mkdir(parents=True)
    (target / "CLAUDE.md").write_text("old content")
    (target / "settings.json").write_text("old content")
    with patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        result = _invoke("install", "--claude-code", "--force")
    assert result.exit_code == 0
    backups = list(target.glob("CLAUDE.md.bak.*"))
    assert len(backups) >= 1, "no backup created"
    assert (target / "CLAUDE.md").read_text() != "old content"


# ---------------------------------------------------------------------------
# 6. --dry-run does not create target dir or any files
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        result = _invoke("install", "--claude-code", "--dry-run")
    assert result.exit_code == 0
    assert not (tmp_path / ".claude" / "silentwitness").exists()
    assert "would copy" in result.output


# ---------------------------------------------------------------------------
# 7. Copied settings.json parses as JSON (after JSONC stripping)
# ---------------------------------------------------------------------------


def test_settings_json_is_valid_json_after_comment_strip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        _invoke("install", "--claude-code")
    settings_path = tmp_path / ".claude" / "silentwitness" / "settings.json"
    raw = settings_path.read_text(encoding="utf-8")
    stripped = re.sub(r"//[^\n]*", "", raw)
    parsed = json.loads(stripped)
    assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# 8. Copied settings.json contains required mcpServers.silentwitness block
# ---------------------------------------------------------------------------


def test_settings_json_contains_mcp_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        _invoke("install", "--claude-code")
    settings_path = tmp_path / ".claude" / "silentwitness" / "settings.json"
    raw = settings_path.read_text(encoding="utf-8")
    parsed = json.loads(re.sub(r"//[^\n]*", "", raw))
    mcp = parsed["mcpServers"]["silentwitness"]
    assert mcp["type"] == "stdio"
    assert mcp["command"] == "python"
    assert mcp["args"] == ["-m", "silentwitness_mcp"]


# ---------------------------------------------------------------------------
# 9. Deny list contains required entries (architecture §6.2)
# ---------------------------------------------------------------------------


def test_settings_json_deny_list_contains_required_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        _invoke("install", "--claude-code")
    settings_path = tmp_path / ".claude" / "silentwitness" / "settings.json"
    raw = settings_path.read_text(encoding="utf-8")
    parsed = json.loads(re.sub(r"//[^\n]*", "", raw))
    deny = set(parsed["permissions"]["deny"])
    assert "Bash(silentwitness approve*)" in deny
    assert "Edit(cases/*/audit/*.jsonl)" in deny
    assert "Edit(cases/*/evidence.json)" in deny
    assert "Edit(/var/lib/silentwitness/**)" in deny


# ---------------------------------------------------------------------------
# 10. --cursor / --continue are no-ops (exit 0, warning printed)
# ---------------------------------------------------------------------------


def test_cursor_flag_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke("install", "--cursor")
    assert result.exit_code == 0
    assert "not yet implemented" in result.output or "Claude Code only" in result.output


def test_continue_flag_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _invoke("install", "--continue")
    assert result.exit_code == 0
    assert "not yet implemented" in result.output or "Claude Code only" in result.output


# ---------------------------------------------------------------------------
# 11. Missing source config file exits 2 with path quoted in stderr
# ---------------------------------------------------------------------------


def test_missing_source_config_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with (
        patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "claude"),
        patch(
            "silentwitness_agent.cli_commands.install._find_repo_root",
            return_value=tmp_path,
        ),
    ):
        (tmp_path / "claude").write_text("#!/bin/sh\n")
        # Repo root has no claude-code-config/CLAUDE.md
        result = _invoke("install", "--claude-code")
    assert result.exit_code == 2
    combined = result.stderr + result.output
    assert "CLAUDE.md" in combined


# ---------------------------------------------------------------------------
# 12. SIFT 2026 path /usr/local/bin/claude is cited verbatim in error wording
# ---------------------------------------------------------------------------


def test_sift_claude_path_quoted_verbatim_in_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    with (
        patch("silentwitness_agent.cli_commands.install._SIFT_CLAUDE_PATH", tmp_path / "no-claude"),
        patch("silentwitness_agent.cli_commands.install.shutil.which", return_value=None),
    ):
        result = _invoke("install", "--claude-code")
    assert result.exit_code == 2
    assert "/usr/local/bin/claude" in (result.stderr + result.output)
