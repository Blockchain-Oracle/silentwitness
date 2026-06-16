"""Unit tests for `scripts/egnyte_share.py` — the Egnyte public-share client.

Pins the silent-failure regressions surfaced by PR #238 review:
- `entry_id` is the `entryId` field, NOT `id` (PR #237 round-1 bug).
- Pagination terminates on `offset >= total` AND on empty results.
- `_list_contents` raises ProtocolError on non-JSON, missing envelope,
  missing results list, or duplicate entries across pages.
- `resolve_case_root` raises SystemExit on unknown case.
- `verify_sidecar` returns True iff sidecar matches actual SHA.
- `stream_file` rejects folder entries (no entry_id).
- `stream_file` writes target + sidecar atomically and verifies size.

Egnyte API is mocked via httpx.MockTransport. No network. CI offline-safe.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import httpx
import pytest

# Load `scripts/egnyte_share.py` as a module without making scripts/ a package.
_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "egnyte_share.py"
_spec = importlib.util.spec_from_file_location("egnyte_share", _SCRIPT_PATH)
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
sys.modules["egnyte_share"] = _module
_spec.loader.exec_module(_module)

Entry = _module.Entry
ProtocolError = _module.ProtocolError
ChecksumMismatchError = _module.ChecksumMismatchError
list_contents = _module.list_contents
resolve_case_root = _module.resolve_case_root
verify_sidecar = _module.verify_sidecar
stream_file = _module.stream_file


def _client(transport: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(
        transport=transport,
        base_url="https://sansorg.egnyte.com",
        headers={"User-Agent": "test", "Accept": "application/json, text/plain, */*"},
    )


def _file_entry(name: str, *, with_entry_id: bool = True) -> dict:
    e: dict = {
        "path": f"/x/{name}",
        "name": name,
        "type": "file",
        "id": f"perm-{name}",
        "size": 1,
    }
    if with_entry_id:
        e["entryId"] = f"share-{name}"
    return e


def _listing(results: list[dict], *, total: int | None = None) -> dict:
    return {
        "contents": {
            "totalFileCount": total if total is not None else len(results),
            "totalFolderCount": 0,
            "results": results,
        }
    }


# ---------------------------------------------------------------------------
# entry_id extraction — pins PR #237 round-1 bug shut
# ---------------------------------------------------------------------------


def test_file_entry_uses_share_scoped_entry_id_not_permanent_id() -> None:
    """Yield `entry_id = entryId` (share-scoped UUID). The permanent `id`
    produces 404 on download — that bug cost a review round."""
    raw = {
        "path": "/x/f.bin",
        "name": "f.bin",
        "type": "file",
        "id": "perm-id-AAA",
        "entryId": "share-id-BBB",
        "size": 100,
    }
    client = _client(httpx.MockTransport(lambda _r: httpx.Response(200, json=_listing([raw]))))
    entries = list(list_contents(client, "/x"))
    assert entries[0].entry_id == "share-id-BBB"  # NOT "perm-id-AAA"


def test_file_missing_entry_id_raises_protocol_error() -> None:
    """Fail loudly instead of silently falling back to `id` and producing 404s."""
    raw = _file_entry("f.bin", with_entry_id=False)
    client = _client(httpx.MockTransport(lambda _r: httpx.Response(200, json=_listing([raw]))))
    with pytest.raises(ProtocolError, match="missing `entryId`"):
        list(list_contents(client, "/x"))


def test_folder_without_entry_id_is_ok() -> None:
    """Folders carry only `id`; never passed to stream_file so the absence
    is fine. `entry_id` ends up None on the Entry."""
    folder = {"path": "/x/sub", "name": "sub", "type": "folder", "id": "f"}
    client = _client(
        httpx.MockTransport(
            lambda _r: httpx.Response(
                200,
                json={
                    "contents": {
                        "totalFileCount": 0,
                        "totalFolderCount": 1,
                        "results": [folder],
                    }
                },
            )
        )
    )
    entries = list(list_contents(client, "/x"))
    assert entries[0].entry_id is None


# ---------------------------------------------------------------------------
# Pagination termination
# ---------------------------------------------------------------------------


def test_pagination_terminates_on_total_reached() -> None:
    """Two pages, total=53. POST exactly twice, yield 53 entries — no loop."""
    n_calls = 0
    pages = [
        [_file_entry(f"f{i}.bin") for i in range(48)],
        [_file_entry(f"f{i}.bin") for i in range(48, 53)],
    ]

    def handler(_r: httpx.Request) -> httpx.Response:
        nonlocal n_calls
        n_calls += 1
        return httpx.Response(200, json=_listing(pages[n_calls - 1], total=53))

    client = _client(httpx.MockTransport(handler))
    entries = list(list_contents(client, "/x"))
    assert len(entries) == 53
    assert n_calls == 2


def test_pagination_empty_results_terminates() -> None:
    """A page with no results terminates immediately (regardless of total)."""
    n_calls = 0

    def handler(_r: httpx.Request) -> httpx.Response:
        nonlocal n_calls
        n_calls += 1
        return httpx.Response(200, json=_listing([], total=999))

    client = _client(httpx.MockTransport(handler))
    assert list(list_contents(client, "/x")) == []
    assert n_calls == 1


def test_pagination_duplicate_entry_raises() -> None:
    """Server-bug duplicates trigger ProtocolError — otherwise we re-download."""
    dup = _file_entry("same.bin")
    client = _client(
        httpx.MockTransport(lambda _r: httpx.Response(200, json=_listing([dup], total=999)))
    )
    with pytest.raises(ProtocolError, match="duplicate entry"):
        list(list_contents(client, "/x"))


# ---------------------------------------------------------------------------
# Captive-portal / schema-drift detection
# ---------------------------------------------------------------------------


def test_non_json_response_raises() -> None:
    """Egnyte returns 200+HTML when rate-limited; without this guard we'd
    parse `{}` and report 0 files silently."""
    client = _client(
        httpx.MockTransport(
            lambda _r: httpx.Response(
                200, text="<html>rate</html>", headers={"Content-Type": "text/html"}
            )
        )
    )
    with pytest.raises(ProtocolError, match="non-JSON"):
        list(list_contents(client, "/x"))


def test_missing_contents_envelope_raises() -> None:
    """API schema drift — fail loudly."""
    client = _client(
        httpx.MockTransport(lambda _r: httpx.Response(200, json={"data": {"results": []}}))
    )
    with pytest.raises(ProtocolError, match="`contents` envelope"):
        list(list_contents(client, "/x"))


def test_missing_results_list_raises() -> None:
    """Partial schema drift — `contents` present but `results` absent."""
    client = _client(
        httpx.MockTransport(
            lambda _r: httpx.Response(200, json={"contents": {"totalFileCount": 0}})
        )
    )
    with pytest.raises(ProtocolError, match=r"missing `contents\.results`"):
        list(list_contents(client, "/x"))


# ---------------------------------------------------------------------------
# resolve_case_root
# ---------------------------------------------------------------------------


def test_resolve_case_root_none_returns_share_root() -> None:
    client = _client(httpx.MockTransport(lambda _r: httpx.Response(500)))
    assert resolve_case_root(client, None) == "/HACKATHON-2026"


def test_resolve_case_root_unknown_raises_systemexit() -> None:
    folder = {"path": "/HACKATHON-2026/Real", "name": "Real", "type": "folder", "id": "f"}
    client = _client(
        httpx.MockTransport(
            lambda _r: httpx.Response(
                200,
                json={
                    "contents": {
                        "totalFileCount": 0,
                        "totalFolderCount": 1,
                        "results": [folder],
                    }
                },
            )
        )
    )
    with pytest.raises(SystemExit, match="not found at share root"):
        resolve_case_root(client, "Bogus")


# ---------------------------------------------------------------------------
# verify_sidecar
# ---------------------------------------------------------------------------


def test_verify_sidecar_matches(tmp_path: Path) -> None:
    target = tmp_path / "f.bin"
    target.write_bytes(b"hello world")
    (tmp_path / "f.bin.sha256").write_text(f"{hashlib.sha256(b'hello world').hexdigest()}  f.bin\n")
    assert verify_sidecar(target) is True


def test_verify_sidecar_mismatch(tmp_path: Path) -> None:
    target = tmp_path / "f.bin"
    target.write_bytes(b"hello world")
    (tmp_path / "f.bin.sha256").write_text("0" * 64 + "  f.bin\n")
    assert verify_sidecar(target) is False


def test_verify_sidecar_missing_sidecar(tmp_path: Path) -> None:
    target = tmp_path / "f.bin"
    target.write_bytes(b"hello world")
    assert verify_sidecar(target) is False


# ---------------------------------------------------------------------------
# stream_file
# ---------------------------------------------------------------------------


def test_stream_file_rejects_folder_entry(tmp_path: Path) -> None:
    folder = Entry(
        path="/x/sub", name="sub", type="folder", size=None, last_modified=None, entry_id=None
    )
    client = _client(httpx.MockTransport(lambda _r: httpx.Response(500)))
    with pytest.raises(ProtocolError, match="folder"):
        stream_file(client, folder, tmp_path / "x")


def test_stream_file_writes_target_and_sidecar(tmp_path: Path) -> None:
    body = b"hello world " * 100
    expected_sha = hashlib.sha256(body).hexdigest()
    client = _client(httpx.MockTransport(lambda _r: httpx.Response(200, content=body)))
    entry = Entry(
        path="/x/f.bin",
        name="f.bin",
        type="file",
        size=len(body),
        last_modified=None,
        entry_id="abc-def",
    )
    target = tmp_path / "f.bin"
    digest = stream_file(client, entry, target)
    assert digest == expected_sha
    assert target.read_bytes() == body
    sidecar = tmp_path / "f.bin.sha256"
    assert sidecar.read_text(encoding="utf-8").startswith(expected_sha)


def test_stream_file_uses_streaming_not_buffered_request(monkeypatch, tmp_path: Path) -> None:
    """Large downloads must not use `client.request`, which buffers the body."""

    body = b"x" * (2 * 1024 * 1024)
    client = _client(httpx.MockTransport(lambda _r: httpx.Response(200, content=body)))
    entry = Entry(
        path="/x/big.bin",
        name="big.bin",
        type="file",
        size=len(body),
        last_modified=None,
        entry_id="abc-def",
    )

    def _fail_buffered_path(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("stream_file must use client.stream, not request_with_retry")

    monkeypatch.setattr(_module._impl, "request_with_retry", _fail_buffered_path)

    target = tmp_path / "big.bin"
    assert stream_file(client, entry, target) == hashlib.sha256(body).hexdigest()
    assert target.stat().st_size == len(body)


def test_stream_file_size_mismatch_raises(tmp_path: Path) -> None:
    client = _client(
        httpx.MockTransport(lambda _r: httpx.Response(200, content=b"only 24 bytes here long.."))
    )
    entry = Entry(
        path="/x/f.bin",
        name="f.bin",
        type="file",
        size=9999,  # lying
        last_modified=None,
        entry_id="abc",
    )
    with pytest.raises(ChecksumMismatchError, match="size mismatch"):
        stream_file(client, entry, tmp_path / "f.bin")
