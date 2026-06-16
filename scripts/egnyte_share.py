"""Compatibility wrapper for the packaged Egnyte public-share client."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from silentwitness_agent.datasets import egnyte_share as _impl  # noqa: E402

CHUNK_BYTES = _impl.CHUNK_BYTES
PAGE_LIMIT = _impl.PAGE_LIMIT
ROOT_PATH = _impl.ROOT_PATH
SHARE_TOKEN = _impl.SHARE_TOKEN
ChecksumMismatchError = _impl.ChecksumMismatchError
Entry = _impl.Entry
ProtocolError = _impl.ProtocolError
human_size = _impl.human_size
list_contents = _impl.list_contents
open_session = _impl.open_session
request_with_retry = _impl.request_with_retry
resolve_case_root = _impl.resolve_case_root
stream_file = _impl.stream_file
verify_sidecar = _impl.verify_sidecar
walk = _impl.walk

__all__ = [
    "CHUNK_BYTES",
    "PAGE_LIMIT",
    "ROOT_PATH",
    "SHARE_TOKEN",
    "ChecksumMismatchError",
    "Entry",
    "ProtocolError",
    "human_size",
    "list_contents",
    "open_session",
    "request_with_retry",
    "resolve_case_root",
    "stream_file",
    "verify_sidecar",
    "walk",
]
