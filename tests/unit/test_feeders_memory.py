"""Unit tests for the pure per-plugin vol3 mappers (no subprocess)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from silentwitness_mcp.index import feeders_memory as fm

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "vol3"


def _load(name: str) -> list[dict[str, Any]]:
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# pslist
# ---------------------------------------------------------------------------


def test_pslist_real_fixture_produces_rows_with_create_time_as_ts() -> None:
    rows = list(
        fm._pslist_to_records(
            _load("pslist.json"),
            artifact_path="memory/Rocba.raw",
            audit_id="A1",
            host="DESKTOP",
            sha256="abc",
        )
    )
    assert len(rows) == 5
    first = rows[0]
    assert first.source_tool == "vol:pslist"
    assert first.artifact_path == "memory/Rocba.raw#vol:pslist"
    assert first.text.startswith("Process pid=4 ppid=0 name=System")
    assert first.ts.startswith("2020-")  # CreateTime preserved


def test_pslist_skips_none_columns_in_text() -> None:
    rows = list(
        fm._pslist_to_records(
            [{"PID": 100, "PPID": None, "ImageFileName": "x.exe", "Threads": 1}],
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert "ppid=" not in rows[0].text
    assert "pid=100" in rows[0].text


# ---------------------------------------------------------------------------
# cmdline
# ---------------------------------------------------------------------------


def test_cmdline_skips_rows_without_args_keeps_rest() -> None:
    fixture = _load("cmdline.json")
    rows = list(
        fm._cmdline_to_records(
            fixture,
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    expected = sum(1 for r in fixture if r.get("Args"))
    assert len(rows) == expected
    assert all("args=" in r.text for r in rows)
    assert all(r.source_tool == "vol:cmdline" for r in rows)


def test_cmdline_emits_row_with_args() -> None:
    rows = list(
        fm._cmdline_to_records(
            [{"PID": 1234, "Process": "powershell.exe", "Args": "-EncodedCommand AAA"}],
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert len(rows) == 1
    assert rows[0].source_tool == "vol:cmdline"
    assert rows[0].ts == ""
    assert "EncodedCommand" in rows[0].text


# ---------------------------------------------------------------------------
# netscan / malfind / psscan
# ---------------------------------------------------------------------------


def test_netscan_formats_local_and_foreign_endpoints() -> None:
    rows = list(
        fm._netscan_to_records(
            [
                {
                    "Proto": "TCPv4",
                    "LocalAddr": "10.0.0.5",
                    "LocalPort": 49152,
                    "ForeignAddr": "1.2.3.4",
                    "ForeignPort": 443,
                    "State": "ESTABLISHED",
                    "PID": 4444,
                    "Owner": "chrome.exe",
                    "Created": "2020-11-15T20:00:00+00:00",
                }
            ],
            artifact_path="m.raw",
            audit_id="A",
            host="H",
            sha256="s",
        )
    )
    assert rows[0].text == (
        "NetConn proto=TCPv4 local=10.0.0.5:49152 foreign=1.2.3.4:443 "
        "state=ESTABLISHED pid=4444 owner=chrome.exe"
    )
    assert rows[0].ts == "2020-11-15T20:00:00+00:00"


def test_malfind_emits_one_row_per_hit() -> None:
    rows = list(
        fm._malfind_to_records(
            [
                {
                    "PID": 9999,
                    "Process": "explorer.exe",
                    "Start VPN": "0x1000000",
                    "End VPN": "0x100ffff",
                    "Tag": "VadS",
                    "Protection": "PAGE_EXECUTE_READWRITE",
                }
            ],
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert rows[0].source_tool == "vol:malfind"
    assert "PAGE_EXECUTE_READWRITE" in rows[0].text


def test_psscan_separate_from_pslist() -> None:
    rows = list(
        fm._psscan_to_records(
            [{"PID": 50, "PPID": 4, "ImageFileName": "ghost.exe"}],
            artifact_path="m.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert rows[0].source_tool == "vol:psscan"
    assert rows[0].text.startswith("ProcessScan")


def test_mappers_and_plugins_stay_in_sync() -> None:
    """Drift check beyond the import-time assert — keeps the registry honest."""
    assert set(fm.MAPPERS.keys()) == set(fm.PLUGINS)


def test_make_record_truncates_at_max_text() -> None:
    from silentwitness_mcp.index._feeder_util import MAX_TEXT

    huge = "x" * 20_000
    rows = list(
        fm._malfind_to_records(
            [{"PID": 1, "Process": "p", "Protection": huge}],
            artifact_path="m",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert len(rows[0].text) == MAX_TEXT


def test_artifact_path_carries_plugin_fragment() -> None:
    rows = list(
        fm._pslist_to_records(
            [{"PID": 4, "PPID": 0, "ImageFileName": "x"}],
            artifact_path="memory/Rocba.raw",
            audit_id="A",
            host="",
            sha256="s",
        )
    )
    assert rows[0].artifact_path == "memory/Rocba.raw#vol:pslist"
