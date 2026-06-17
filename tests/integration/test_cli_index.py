"""Integration tests for the `silentwitness index` command surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from silentwitness_agent.cli import app
from silentwitness_agent.cli_commands import index_case

runner = CliRunner()


def _case_root(tmp_path: Path, case_id: str = "rocba") -> Path:
    case_dir = tmp_path / "cases" / case_id
    (case_dir / ".silentwitness").mkdir(parents=True)
    (case_dir / ".silentwitness" / "case.toml").write_text(
        f'case_id = "{case_id}"\nexaminer = "tester"\n',
        encoding="utf-8",
    )
    return case_dir


def test_index_defaults_to_standard_memory_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _case_root(tmp_path)
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    calls: list[dict[str, Any]] = []

    def fake_run(*_args: object, **kwargs: object) -> int:
        calls.append(dict(kwargs))
        return 0

    monkeypatch.setattr(index_case, "run", fake_run)

    result = runner.invoke(app, ["index", "rocba"], catch_exceptions=False)

    assert result.exit_code == 0
    assert calls[0]["memory_profile"] == "standard"


def test_index_accepts_deep_memory_profile(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _case_root(tmp_path)
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    calls: list[dict[str, Any]] = []

    def fake_run(*_args: object, **kwargs: object) -> int:
        calls.append(dict(kwargs))
        return 0

    monkeypatch.setattr(index_case, "run", fake_run)

    result = runner.invoke(
        app,
        ["index", "rocba", "--memory-profile", "deep"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert calls[0]["memory_profile"] == "deep"


def test_index_accepts_targeted_memory_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _case_root(tmp_path)
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))
    calls: list[dict[str, Any]] = []

    def fake_run(*_args: object, **kwargs: object) -> int:
        calls.append(dict(kwargs))
        return 0

    monkeypatch.setattr(index_case, "run", fake_run)

    result = runner.invoke(
        app,
        ["index", "rocba", "--memory-profile", "targeted"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert calls[0]["memory_profile"] == "targeted"


def test_index_rejects_unknown_memory_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _case_root(tmp_path)
    monkeypatch.setenv("SILENTWITNESS_CASES_DIR", str(tmp_path))

    result = runner.invoke(
        app,
        ["index", "rocba", "--memory-profile", "turbo"],
        catch_exceptions=False,
    )

    assert result.exit_code == 2
    assert "--memory-profile must be 'standard', 'targeted', or 'deep'" in result.output
