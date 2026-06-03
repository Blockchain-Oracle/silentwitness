"""Hypothesis property tests for atomic_io round-trip invariants.

These pin the strongest contract atomic_io provides: bytes you write are
exactly the bytes you read back, and JSONL appends preserve input order.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given, settings, strategies as st

from silentwitness_common.atomic_io import append_jsonl_line, write_bytes_atomic


@given(payload=st.binary(min_size=0, max_size=1 << 20))
@settings(max_examples=50, deadline=None)
def test_write_bytes_atomic_round_trips_any_payload(payload: bytes) -> None:
    """For any binary payload up to 1 MiB, write→read is identity."""
    with tempfile.TemporaryDirectory() as raw:
        target = Path(raw) / "blob.bin"
        write_bytes_atomic(target, payload)
        assert target.read_bytes() == payload


# Realistic JSONL lines: printable Unicode + spaces, no control chars (which
# include LF, CR, the legacy line/record separators 0x1C-0x1E, etc.). This
# matches what AuditEntry.model_dump_json() actually emits.
_jsonl_line_chars = st.characters(
    blacklist_categories=("Cc", "Cs", "Zl", "Zp"),
)


@given(
    lines=st.lists(
        st.text(alphabet=_jsonl_line_chars, min_size=0, max_size=80),
        min_size=0,
        max_size=20,
    )
)
@settings(max_examples=30, deadline=None)
def test_append_jsonl_line_preserves_order_and_count(lines: list[str]) -> None:
    """For any sequence of newline-free strings, sequential appends produce
    exactly those strings in order, terminated by ``\\n``."""
    with tempfile.TemporaryDirectory() as raw:
        target = Path(raw) / "audit.jsonl"
        for line in lines:
            append_jsonl_line(target, line)
        if not lines:
            assert not target.exists() or target.read_text(encoding="utf-8") == ""
            return
        # Split on `\n` only, NOT splitlines() (which also splits on \x1e etc.).
        content = target.read_text(encoding="utf-8")
        assert content.endswith("\n")
        read_back = content[:-1].split("\n")
        assert read_back == lines
