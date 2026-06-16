"""Integration tests for `silentwitness starter-cases`."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from silentwitness_agent.cli import app
from silentwitness_agent.cli_commands import starter_cases as starter_case_cmd
from silentwitness_agent.starter_cases.egnyte_share import Entry

runner = CliRunner()


class _FakeClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _folder(name: str) -> Entry:
    return Entry(
        path=f"/HACKATHON-2026/{name}",
        name=name,
        type="folder",
        size=None,
        last_modified=None,
        entry_id=None,
    )


def _file(path: str, size: int = 4) -> Entry:
    return Entry(
        path=path,
        name=Path(path).name,
        type="file",
        size=size,
        last_modified=None,
        entry_id=f"entry-{Path(path).name}",
    )


def test_starter_cases_help_exposes_catalog_and_download() -> None:
    result = runner.invoke(app, ["starter-cases", "--help"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "catalog" in result.output
    assert "download" in result.output


def test_starter_cases_catalog_summarizes_official_cases(monkeypatch) -> None:
    fake = _FakeClient()
    monkeypatch.setattr(starter_case_cmd, "open_session", lambda: fake)
    monkeypatch.setattr(
        starter_case_cmd, "resolve_case_root", lambda _client, _case: "/HACKATHON-2026"
    )
    monkeypatch.setattr(
        starter_case_cmd,
        "list_contents",
        lambda _client, _root: iter([_folder("Standard Forensic Case"), _folder("APT Case")]),
    )

    def _walk(_client: object, root: str):
        if root.endswith("Standard Forensic Case"):
            return iter([_file(f"{root}/disk.E01", 1024), _file(f"{root}/memory.raw", 2048)])
        return iter([_file(f"{root}/trace.pcap", 512)])

    monkeypatch.setattr(starter_case_cmd, "walk", _walk)

    result = runner.invoke(app, ["starter-cases", "catalog"], catch_exceptions=False)

    assert result.exit_code == 0
    assert "Official Find Evil 2026 starter cases" in result.output
    assert "Standard Forensic Case" in result.output
    assert "APT Case" in result.output
    assert "2" in result.output
    assert fake.closed is True


def test_starter_cases_catalog_case_prints_files(monkeypatch) -> None:
    monkeypatch.setattr(starter_case_cmd, "open_session", _FakeClient)
    monkeypatch.setattr(
        starter_case_cmd,
        "resolve_case_root",
        lambda _client, _case: "/HACKATHON-2026/Standard Forensic Case",
    )
    monkeypatch.setattr(
        starter_case_cmd,
        "walk",
        lambda _client, root: iter([_file(f"{root}/disk.E01", 1024)]),
    )

    result = runner.invoke(
        app,
        ["starter-cases", "catalog", "Standard Forensic Case"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "/HACKATHON-2026/Standard Forensic Case/disk.E01" in result.output
    assert "Total: 1 files" in result.output


def test_starter_cases_download_dry_run_uses_default_evidence_target(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(starter_case_cmd, "open_session", _FakeClient)
    monkeypatch.setattr(
        starter_case_cmd,
        "resolve_case_root",
        lambda _client, _case: "/HACKATHON-2026/Standard Forensic Case",
    )
    monkeypatch.setattr(
        starter_case_cmd,
        "walk",
        lambda _client, root: iter([_file(f"{root}/disk.E01", 1024)]),
    )

    result = runner.invoke(
        app,
        ["starter-cases", "download", "Standard Forensic Case", "--dry-run"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "DRY" in result.output
    assert "evidence/standard-forensic-case/disk.E01" in result.output.replace("\n", "")


def test_starter_cases_download_streams_files_to_target(monkeypatch, tmp_path: Path) -> None:
    streamed: list[Path] = []
    monkeypatch.setattr(starter_case_cmd, "open_session", _FakeClient)
    monkeypatch.setattr(
        starter_case_cmd,
        "resolve_case_root",
        lambda _client, _case: "/HACKATHON-2026/Standard Forensic Case",
    )
    monkeypatch.setattr(
        starter_case_cmd,
        "walk",
        lambda _client, root: iter([_file(f"{root}/disk.E01", 4)]),
    )

    def _stream(_client: object, _entry: Entry, target: Path) -> str:
        streamed.append(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"data")
        return "a" * 64

    monkeypatch.setattr(starter_case_cmd, "stream_file", _stream)

    result = runner.invoke(
        app,
        ["starter-cases", "download", "Standard Forensic Case", str(tmp_path / "rocba")],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert streamed == [tmp_path / "rocba" / "disk.E01"]
    assert "OK" in result.output
    assert "Done: 1 files" in result.output


def test_datasets_alias_is_hidden_but_still_works() -> None:
    root_help = runner.invoke(app, ["--help"], catch_exceptions=False)
    assert root_help.exit_code == 0
    assert "starter-cases" in root_help.output
    assert "datasets" not in root_help.output

    alias_help = runner.invoke(app, ["datasets", "--help"], catch_exceptions=False)
    assert alias_help.exit_code == 0
    assert "Deprecated" in alias_help.output or "deprecated" in alias_help.output
    assert "catalog" in alias_help.output
