"""Behavioural tests for src/silentwitness_mcp/verification/normalizer.py.

No mocks. Each rule is exercised in isolation AND in combination so a
reordering regression surfaces immediately. The byte-stability and
idempotency properties are the load-bearing wedge invariants.
"""

from __future__ import annotations

import hashlib

import pytest

from silentwitness_mcp.verification.normalizer import normalize_output

# ---------------------------------------------------------------------------
# Rule (1) — banner strip
# ---------------------------------------------------------------------------


def test_banner_strip_removes_vol3_framework_line() -> None:
    raw = b"Volatility 3 Framework 2.7.0\nPID   PPID  Name\n4     0     System\n"
    out = normalize_output(raw, tool="vol_pslist").decode()
    assert "Volatility 3 Framework" not in out
    assert "System" in out


def test_banner_strip_is_per_tool_no_op_for_unknown_tool() -> None:
    raw = b"Volatility 3 Framework 2.7.0\nbody\n"
    out = normalize_output(raw, tool="any").decode()
    assert "Volatility 3 Framework 2.7.0" in out


def test_banner_strip_matches_at_line_start_only() -> None:
    """A line that mentions the banner phrase mid-line is evidence, not banner."""
    raw = b"# log: contains 'Volatility 3 Framework' string\n"
    out = normalize_output(raw, tool="vol_pslist").decode()
    assert "Volatility 3 Framework" in out


# ---------------------------------------------------------------------------
# Rule (2) — metadata timestamp tokenize
# ---------------------------------------------------------------------------


def test_metadata_timestamp_tokenized_on_evtxecmd_header() -> None:
    raw = b"EvtxECmd version 1.5.0 (started 2026-06-03T14:27:33Z)\n"
    out = normalize_output(raw, tool="parse_evtx").decode()
    assert "<TS>" in out
    assert "2026-06-03T14:27:33Z" not in out


def test_evidence_timestamps_in_csv_rows_preserved() -> None:
    """The wedge: evidence content (EVTX event rows) must NOT be tokenized."""
    raw = (
        b"EvtxECmd version 1.5.0 (started 2026-06-03T14:27:33Z)\n"
        b"4624,2026-06-02T03:14:00Z,Logon,user@workstation\n"
    )
    out = normalize_output(raw, tool="parse_evtx").decode()
    assert "2026-06-02T03:14:00Z" in out  # evidence preserved
    assert "2026-06-03T14:27:33Z" not in out  # metadata stripped


def test_metadata_timestamp_no_op_when_tool_has_no_pattern() -> None:
    raw = b"some output 2026-06-03T14:27:33Z\n"
    out = normalize_output(raw, tool="vol_pslist").decode()
    assert "2026-06-03T14:27:33Z" in out


# ---------------------------------------------------------------------------
# Rule (3) — trailing whitespace collapse
# ---------------------------------------------------------------------------


def test_trailing_whitespace_stripped() -> None:
    raw = b"line one   \nline two\t\t\nline three\n"
    out = normalize_output(raw, tool="any").decode()
    assert out == "line one\nline two\nline three\n"


def test_leading_whitespace_preserved() -> None:
    """Indentation IS data (Vol3 pstree uses indent for parentage)."""
    raw = b"  child  \n    grandchild  \n"
    out = normalize_output(raw, tool="any").decode()
    assert out == "  child\n    grandchild\n"


# ---------------------------------------------------------------------------
# Rule (4) — diagnostic path-separator normalize
# ---------------------------------------------------------------------------


def test_diagnostic_backslashes_normalized() -> None:
    raw = b"Stacking layer C:\\path\\to\\plugin\nPID   Name\n4     System\n"
    out = normalize_output(raw, tool="vol_pslist").decode()
    assert "C:/path/to/plugin" in out
    assert "\\" not in out.split("\n")[0]  # diagnostic line backslash-free


def test_evidence_backslashes_preserved() -> None:
    raw = (
        b"PID  Name             CmdLine\n"
        b"4    notepad.exe      C:\\Program Files\\Notepad\\notepad.exe\n"
    )
    out = normalize_output(raw, tool="vol_pslist").decode()
    assert "C:\\Program Files\\Notepad\\notepad.exe" in out


# ---------------------------------------------------------------------------
# Rule (5) — ANSI strip
# ---------------------------------------------------------------------------


def test_ansi_colour_sequences_stripped() -> None:
    raw = b"\x1b[31mERROR\x1b[0m: missing plugin\n"
    out = normalize_output(raw, tool="any").decode()
    assert out == "ERROR: missing plugin\n"


def test_ansi_erase_sequences_stripped() -> None:
    raw = b"loading\x1b[Kprogress: 50%\n"
    out = normalize_output(raw, tool="any").decode()
    assert "\x1b" not in out


# ---------------------------------------------------------------------------
# Rule (6) — line ending normalize
# ---------------------------------------------------------------------------


def test_crlf_normalized_to_lf() -> None:
    raw = b"line1\r\nline2\r\nline3\r\n"
    out = normalize_output(raw, tool="any").decode()
    assert "\r" not in out
    assert out == "line1\nline2\nline3\n"


def test_lone_cr_normalized_to_lf() -> None:
    raw = b"line1\rline2\rline3\r"
    out = normalize_output(raw, tool="any").decode()
    assert "\r" not in out


def test_crlf_pair_does_not_double_line() -> None:
    """``\\r\\n`` must collapse to ``\\n`` not ``\\n\\n``."""
    raw = b"a\r\nb\r\n"
    out = normalize_output(raw, tool="any").decode()
    assert out == "a\nb\n"


# ---------------------------------------------------------------------------
# Idempotency + byte stability — the wedge invariants
# ---------------------------------------------------------------------------


def test_idempotent_on_vol3_sample() -> None:
    raw = (
        b"Volatility 3 Framework 2.7.0\r\n"
        b"\x1b[31mStacking layer C:\\plugin\x1b[0m\r\n"
        b"PID   PPID  Name             \r\n"
        b"4     0     System           \r\n"
    )
    once = normalize_output(raw, tool="vol_pslist")
    twice = normalize_output(once, tool="vol_pslist")
    assert once == twice


def test_idempotent_on_evtx_sample() -> None:
    raw = (
        b"EvtxECmd version 1.5.0 (started 2026-06-03T14:27:33Z)\n4624,2026-06-02T03:14:00Z,Logon\n"
    )
    once = normalize_output(raw, tool="parse_evtx")
    twice = normalize_output(once, tool="parse_evtx")
    assert once == twice


def test_byte_stability_two_identical_inputs_produce_identical_hashes() -> None:
    raw = b"Volatility 3 Framework 2.7.0\nStacking layer x\nPID  Name\n4 System\n"
    a = hashlib.sha256(normalize_output(raw, tool="vol_pslist")).hexdigest()
    b = hashlib.sha256(normalize_output(raw, tool="vol_pslist")).hexdigest()
    assert a == b


def test_determinism_across_tools_independent_of_input_quirks() -> None:
    """Two byte-identical raw outputs produce byte-identical normalised outputs
    regardless of how the rule pipeline interacts internally."""
    raw_a = b"banner\nStuff\twith trailing  \n"
    raw_b = b"banner\nStuff\twith trailing  \n"
    assert normalize_output(raw_a, "vol_pslist") == normalize_output(raw_b, "vol_pslist")


# ---------------------------------------------------------------------------
# Encoding + edge cases
# ---------------------------------------------------------------------------


def test_invalid_utf8_replaced_deterministically() -> None:
    """Invalid UTF-8 bytes get replaced with U+FFFD — same input, same output."""
    raw = b"valid \xff\xfe invalid\n"
    out_a = normalize_output(raw, tool="any")
    out_b = normalize_output(raw, tool="any")
    assert out_a == out_b


def test_empty_input_returns_empty_bytes() -> None:
    assert normalize_output(b"", tool="any") == b""


def test_unknown_tool_falls_back_to_empty_pattern_set() -> None:
    """Unknown tool ⇒ only universal rules apply (no banner / metadata /
    diagnostic). Verifies the default branch is exercised."""
    raw = b"Volatility 3 Framework 2.7.0\rwith ANSI \x1b[31mERR\x1b[0m  \n"
    out = normalize_output(raw, tool="some-unknown-tool").decode()
    # Banner survives (no per-tool banner pattern)
    assert "Volatility 3 Framework 2.7.0" in out
    # ANSI stripped (universal)
    assert "\x1b" not in out
    # Line endings normalized (universal)
    assert "\r" not in out
    # Trailing whitespace stripped (universal)
    assert "  \n" not in out


# ---------------------------------------------------------------------------
# Output type contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool", ["vol_pslist", "parse_evtx", "any", "unknown"])
def test_return_type_is_bytes(tool: str) -> None:
    """Callers SHA-256 the result directly — must always be bytes."""
    assert isinstance(normalize_output(b"sample\n", tool=tool), bytes)
