"""Behavioural tests for src/silentwitness_common/atomic_io.py.

Real filesystem (tmp_path), no mocks — per architecture §14. The
crash-mid-write scenario is exercised via os.replace monkey-patched to raise,
which is a legitimate test fixture (we're injecting a controlled failure to
verify the rollback path), not a production-code mock.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from silentwitness_common.atomic_io import (
    append_jsonl_line,
    atomic_writer,
    write_bytes_atomic,
    write_json_atomic,
    write_text_atomic,
)


def test_write_bytes_atomic_creates_file_with_data(tmp_path: Path) -> None:
    target = tmp_path / "foo.bin"
    payload = b"\x00\x01\x02hello\xff"
    write_bytes_atomic(target, payload)
    assert target.read_bytes() == payload


def test_write_bytes_atomic_leaves_no_tmp_artefact(tmp_path: Path) -> None:
    """The .tmp.<pid>.<rand> sibling must not survive a successful write."""
    target = tmp_path / "foo.bin"
    write_bytes_atomic(target, b"x")
    leftovers = [p.name for p in tmp_path.iterdir() if ".tmp." in p.name]
    assert leftovers == [], f"temp artefact survived successful write: {leftovers}"


def test_write_text_atomic_preserves_utf8(tmp_path: Path) -> None:
    """Round-trip must preserve non-ASCII bytes exactly (emoji + Han + BOM)."""
    target = tmp_path / "utf8.txt"
    text = "﻿ Café 北京 😀"
    write_text_atomic(target, text)
    assert target.read_text(encoding="utf-8") == text


def test_write_json_atomic_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "data.json"
    payload = {"a": 1, "b": [1, 2, 3], "c": "Café 北京 😀"}
    write_json_atomic(target, payload)
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_write_json_atomic_indent_pretty_prints(tmp_path: Path) -> None:
    """indent=2 must produce a multi-line JSON document."""
    target = tmp_path / "pretty.json"
    write_json_atomic(target, {"a": 1, "b": 2}, indent=2)
    text = target.read_text(encoding="utf-8")
    assert "\n" in text
    assert text.startswith("{\n")


def test_write_bytes_atomic_honours_mode(tmp_path: Path) -> None:
    target = tmp_path / "secret.txt"
    write_bytes_atomic(target, b"shh", mode=0o600)
    assert target.stat().st_mode & 0o777 == 0o600


def test_append_jsonl_line_creates_file_on_first_call(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    append_jsonl_line(target, '{"k":1}')
    assert target.read_text(encoding="utf-8") == '{"k":1}\n'


def test_append_jsonl_line_preserves_prior_lines(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    for i in range(5):
        append_jsonl_line(target, json.dumps({"k": i}))
    assert target.read_text(encoding="utf-8") == "\n".join(f'{{"k": {i}}}' for i in range(5)) + "\n"


def test_append_jsonl_line_rejects_embedded_newline(tmp_path: Path) -> None:
    target = tmp_path / "audit.jsonl"
    with pytest.raises(ValueError, match="newline"):
        append_jsonl_line(target, '{"k":1}\nINJECTED')


def test_append_jsonl_line_thread_safety(tmp_path: Path) -> None:
    """10 threads x 10 appends = 100 well-formed lines, no interleaving."""
    target = tmp_path / "audit.jsonl"

    def worker(thread_id: int) -> None:
        for j in range(10):
            append_jsonl_line(target, json.dumps({"t": thread_id, "j": j}))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    lines = target.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 100
    for line in lines:
        payload = json.loads(line)
        assert {"t", "j"} == payload.keys()


def test_atomic_writer_commits_on_clean_exit(tmp_path: Path) -> None:
    target = tmp_path / "stream.bin"
    with atomic_writer(target) as fh:
        fh.write(b"hello")
        fh.write(b" world")
    assert target.read_bytes() == b"hello world"
    # No tmp artefact.
    leftovers = [p.name for p in tmp_path.iterdir() if ".tmp." in p.name]
    assert leftovers == []


def test_atomic_writer_rolls_back_on_exception(tmp_path: Path) -> None:
    """If the `with` body raises, the target file is untouched and tmp is gone."""
    target = tmp_path / "stream.bin"
    # Pre-populate so we can detect that it remains unchanged.
    target.write_bytes(b"PRIOR")
    with pytest.raises(RuntimeError, match="boom"):
        with atomic_writer(target) as fh:
            fh.write(b"new content that must NOT land")
            raise RuntimeError("boom")
    assert target.read_bytes() == b"PRIOR"
    leftovers = [p.name for p in tmp_path.iterdir() if ".tmp." in p.name]
    assert leftovers == [], f"tmp artefact survived rollback: {leftovers}"


def test_write_bytes_atomic_rolls_back_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If os.replace fails (e.g. cross-fs rename), the prior file content stands
    and the tmp file is cleaned up. Monkeypatching os.replace is a legitimate
    test fixture for injecting a controlled rename failure — not a mock of
    business logic."""
    target = tmp_path / "important.json"
    target.write_bytes(b"PRIOR")

    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated cross-fs rename failure")

    monkeypatch.setattr("silentwitness_common.atomic_io.os.replace", boom)
    with pytest.raises(OSError, match="simulated"):
        write_bytes_atomic(target, b"new content")

    assert target.read_bytes() == b"PRIOR"
    leftovers = [p.name for p in tmp_path.iterdir() if ".tmp." in p.name]
    assert leftovers == [], f"tmp artefact survived failed write: {leftovers}"


def test_write_bytes_atomic_creates_parent_dir(tmp_path: Path) -> None:
    """Caller doesn't have to mkdir — the helper does."""
    target = tmp_path / "nested" / "dirs" / "file.bin"
    assert not target.parent.exists()
    write_bytes_atomic(target, b"ok")
    assert target.read_bytes() == b"ok"
