"""Unit tests for the Zeek PCAP feeder."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from silentwitness_mcp.index._feeder_util import FeederStats
from silentwitness_mcp.index.feeders_pcap import PcapFeederError, _parse_zeek_log, pcap_records


def test_parse_zeek_log_maps_rows_to_index_records(tmp_path: Path) -> None:
    log = tmp_path / "conn.log"
    log.write_text(
        "\n".join(
            [
                "#separator \\x09",
                "#fields\tts\tuid\tid.orig_h\tid.resp_h\tid.resp_p\tproto\tservice",
                "#types\ttime\tstring\taddr\taddr\tport\tenum\tstring",
                "1284123456.1\tC1\t10.0.0.5\t192.0.2.10\t25\ttcp\tsmtp",
                "#close 2026-06-16-19-00-00",
            ]
        ),
        encoding="utf-8",
    )
    rows = list(
        _parse_zeek_log(
            log,
            log_name="conn",
            audit_id="a1",
            host="nitroba",
            artifact_path="nitroba.pcap/conn.log",
            stats=FeederStats(),
        )
    )
    assert len(rows) == 1
    assert rows[0].source_tool == "zeek:conn"
    assert rows[0].artifact_path == "nitroba.pcap/conn.log"
    assert rows[0].host == "nitroba"
    assert "id.orig_h=10.0.0.5" in rows[0].text
    assert "service=smtp" in rows[0].text


def test_parse_zeek_log_counts_malformed_rows(tmp_path: Path) -> None:
    log = tmp_path / "dns.log"
    log.write_text("#fields\tts\tquery\nbad\ttoo\tmany\n", encoding="utf-8")
    stats = FeederStats()
    rows = list(
        _parse_zeek_log(
            log,
            log_name="dns",
            audit_id="a1",
            host="",
            artifact_path="nitroba.pcap/dns.log",
            stats=stats,
        )
    )
    assert rows == []
    assert stats.skipped == {"zeek_field_count_mismatch": 1}


def test_pcap_records_runs_zeek_and_reads_selected_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pcap = tmp_path / "capture.pcap"
    pcap.write_bytes(b"pcap")

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert cmd[:3] == ["/usr/bin/zeek", "-C", "-r"]
        cwd = Path(kwargs["cwd"])
        (cwd / "dns.log").write_text(
            "#fields\tts\tuid\tquery\tanswers\n1.0\tD1\texample.test\t192.0.2.10\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(
        "silentwitness_mcp.index.feeders_pcap.shutil.which", lambda _: "/usr/bin/zeek"
    )
    monkeypatch.setattr("silentwitness_mcp.index.feeders_pcap.subprocess.run", fake_run)

    rows = list(pcap_records(pcap, audit_id="a1", host="h", source_path="capture.pcap"))
    assert len(rows) == 1
    assert rows[0].source_tool == "zeek:dns"
    assert "query=example.test" in rows[0].text


def test_pcap_records_requires_zeek(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("silentwitness_mcp.index.feeders_pcap.shutil.which", lambda _: None)
    with pytest.raises(PcapFeederError, match="zeek executable not found"):
        list(pcap_records(tmp_path / "capture.pcap", audit_id="a1"))
