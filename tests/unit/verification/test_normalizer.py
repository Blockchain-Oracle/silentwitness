"""Behavioural tests for src/silentwitness_mcp/verification/normalizer.py.

No mocks. Each rule is exercised in isolation AND in combination so a
reordering regression surfaces immediately. The byte-stability and
idempotency properties are the load-bearing wedge invariants.
"""

from __future__ import annotations

import hashlib

import pytest
from hypothesis import given, settings, strategies as st

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
    out = normalize_output(raw, tool="_universal_only").decode()
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
    out = normalize_output(raw, tool="_universal_only").decode()
    assert out == "line one\nline two\nline three\n"


def test_leading_whitespace_preserved() -> None:
    """Indentation IS data (Vol3 pstree uses indent for parentage)."""
    raw = b"  child  \n    grandchild  \n"
    out = normalize_output(raw, tool="_universal_only").decode()
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
    out = normalize_output(raw, tool="_universal_only").decode()
    assert out == "ERROR: missing plugin\n"


def test_ansi_erase_sequences_stripped() -> None:
    raw = b"loading\x1b[Kprogress: 50%\n"
    out = normalize_output(raw, tool="_universal_only").decode()
    assert "\x1b" not in out


# ---------------------------------------------------------------------------
# Rule (6) — line ending normalize
# ---------------------------------------------------------------------------


def test_crlf_normalized_to_lf() -> None:
    raw = b"line1\r\nline2\r\nline3\r\n"
    out = normalize_output(raw, tool="_universal_only").decode()
    assert "\r" not in out
    assert out == "line1\nline2\nline3\n"


def test_lone_cr_normalized_to_lf() -> None:
    raw = b"line1\rline2\rline3\r"
    out = normalize_output(raw, tool="_universal_only").decode()
    assert "\r" not in out


def test_crlf_pair_does_not_double_line() -> None:
    """``\\r\\n`` must collapse to ``\\n`` not ``\\n\\n``."""
    raw = b"a\r\nb\r\n"
    out = normalize_output(raw, tool="_universal_only").decode()
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
    out_a = normalize_output(raw, tool="_universal_only")
    out_b = normalize_output(raw, tool="_universal_only")
    assert out_a == out_b


def test_empty_input_returns_empty_bytes() -> None:
    assert normalize_output(b"", tool="_universal_only") == b""


def test_unknown_tool_raises_loudly() -> None:
    """Round-2 fix (PR-106 silent-failure H1 + code-reviewer F3): a typo'd
    tool string must NOT silently fall back to universal-rules-only. The
    explicit ``"_universal_only"`` sentinel is the way to opt in to that."""
    from silentwitness_mcp.verification.normalizer import UnknownToolError

    with pytest.raises(UnknownToolError, match="not registered"):
        normalize_output(b"sample\n", tool="vol_pslit")  # typo


def test_universal_only_sentinel_applies_only_universal_rules() -> None:
    raw = b"Volatility 3 Framework 2.7.0\rwith ANSI \x1b[31mERR\x1b[0m  \n"
    out = normalize_output(raw, tool="_universal_only").decode()
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


@pytest.mark.parametrize("tool", ["vol_pslist", "parse_evtx", "_universal_only"])
def test_return_type_is_bytes(tool: str) -> None:
    """Callers SHA-256 the result directly — must always be bytes."""
    assert isinstance(normalize_output(b"sample\n", tool=tool), bytes)


# ---------------------------------------------------------------------------
# Round-2 fixes (PR-106 reviewer findings)
# ---------------------------------------------------------------------------


def test_vol3_reading_line_preserves_evidence_backslashes() -> None:
    """Code-reviewer F1 + silent-failure C2: ``Reading from C:\\evidence\\...``
    is evidence content, NOT diagnostic chatter. Removing ``Reading`` from
    the diagnostic discriminator preserves the backslashes."""
    raw = b"Reading from C:\\Users\\victim\\malware.exe (evidence)\n"
    out = normalize_output(raw, tool="vol_pslist").decode()
    assert "C:\\Users\\victim\\malware.exe" in out


def test_vol3_loading_line_preserves_evidence_backslashes() -> None:
    raw = b"Loading symbol file C:\\Symbols\\ntdll.pdb\n"
    out = normalize_output(raw, tool="vol_pslist").decode()
    assert "C:\\Symbols\\ntdll.pdb" in out


def test_vol3_scanning_line_preserves_evidence_backslashes() -> None:
    raw = b"Scanning C:\\Windows\\Temp\\evil.exe\n"
    out = normalize_output(raw, tool="vol_pslist").decode()
    assert "C:\\Windows\\Temp\\evil.exe" in out


def test_evtx_command_line_preserves_embedded_evidence_timestamp() -> None:
    """Silent-failure C1: ``Command line:`` argv often embeds a source file
    path whose name contains an ISO-8601 timestamp. Dropping that prefix
    from the metadata discriminator preserves the timestamp."""
    raw = b"Command line: EvtxECmd --source 2026-06-02T03:14:00Z.evtx --csv out\n"
    out = normalize_output(raw, tool="parse_evtx").decode()
    assert "2026-06-02T03:14:00Z.evtx" in out


def test_evtx_processing_started_only_trailing_timestamp_tokenized() -> None:
    """Silent-failure C1: when a metadata line embeds an evidence timestamp
    earlier and a wrapper timestamp at the end, only the LAST one is
    tokenized."""
    raw = b"Processing started for 2026-06-02T03:14:00Z.evtx at 2026-06-03T15:00:00Z\n"
    out = normalize_output(raw, tool="parse_evtx").decode()
    assert "2026-06-02T03:14:00Z" in out  # earlier (evidence) preserved
    assert "<TS>" in out  # trailing (wrapper) tokenized
    assert out.count("2026-06-03T15:00:00Z") == 0  # wrapper stripped


def test_invalid_utf8_is_injective_via_surrogateescape() -> None:
    """Silent-failure H5: two raw inputs differing only in invalid UTF-8
    bytes must produce DIFFERENT normalised outputs. surrogateescape
    preserves the byte-level distinction; ``errors="replace"`` would have
    collapsed both to U+FFFD."""
    a = normalize_output(b"head\xfftail\n", "_universal_only")
    b = normalize_output(b"head\x80tail\n", "_universal_only")
    assert a != b


def test_ascii_digits_only_in_iso_timestamp_match() -> None:
    """Silent-failure C3: fullwidth/Arabic digits must NOT match
    ``ISO_TIMESTAMP`` (``[0-9]``, not ``\\d``). Cross-Python-version drift
    on Unicode-digit category membership would otherwise break byte
    stability."""
    # Fullwidth digits U+FF10..U+FF19; shouldn't trigger sub via [0-9].
    fw = (
        "\uff12\uff10\uff12\uff16-\uff10\uff16-\uff10\uff13T\uff11\uff14:\uff12\uff17:\uff13\uff13Z"
    )
    raw = f"EvtxECmd version {fw}\n".encode()
    out = normalize_output(raw, tool="parse_evtx").decode()
    assert "<TS>" not in out  # No tokenization on fullwidth digits


def test_ansi_cursor_move_stripped() -> None:
    """Silent-failure C4: broadened ANSI grammar strips cursor-move sequences."""
    raw = b"loading\x1b[2Aprogress: 50%\n"
    out = normalize_output(raw, tool="_universal_only").decode()
    assert "\x1b" not in out


def test_ansi_hide_cursor_stripped() -> None:
    raw = b"\x1b[?25lhidden cursor\x1b[?25h\n"
    out = normalize_output(raw, tool="_universal_only").decode()
    assert "\x1b" not in out


def test_ansi_osc_window_title_stripped() -> None:
    raw = b"\x1b]0;Window Title\x07content\n"
    out = normalize_output(raw, tool="_universal_only").decode()
    assert "\x1b" not in out
    assert "content" in out


def test_extended_rstrip_drops_form_feed_and_nbsp() -> None:
    """Silent-failure H4: form-feed + NBSP at end of line are invisible to
    the analyst but contribute to the hash unless rstripped."""
    raw = b"line one\xc2\xa0\x0c\nline two\n"  # NBSP + FF before newline
    out = normalize_output(raw, tool="_universal_only").decode()
    assert out == "line one\nline two\n"


# ---------------------------------------------------------------------------
# Property tests (PR-106 silent-failure M5 — wedge invariants under fuzz)
# ---------------------------------------------------------------------------


_REGISTERED_TOOLS = ["vol_pslist", "vol_pstree", "parse_evtx", "_universal_only"]


@given(raw=st.binary(min_size=0, max_size=2048), tool=st.sampled_from(_REGISTERED_TOOLS))
@settings(max_examples=50, deadline=None)
def test_normalize_is_idempotent(raw: bytes, tool: str) -> None:
    once = normalize_output(raw, tool=tool)
    twice = normalize_output(once, tool=tool)
    assert once == twice


@given(raw=st.binary(min_size=0, max_size=2048), tool=st.sampled_from(_REGISTERED_TOOLS))
@settings(max_examples=50, deadline=None)
def test_normalize_is_byte_stable(raw: bytes, tool: str) -> None:
    assert normalize_output(raw, tool=tool) == normalize_output(raw, tool=tool)
