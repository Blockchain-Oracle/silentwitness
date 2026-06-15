"""Unit tests for findings/_wrap.py — the shared sanitizer-envelope helper."""

from __future__ import annotations

import pytest

from silentwitness_mcp.findings._wrap import (
    _WRAP_BEGIN,
    _WRAP_END,
    StripError,
    content_after_wrap,
)


def test_fully_wrapped_payload_returns_inner_text() -> None:
    wrapped = f"{_WRAP_BEGIN}the inner content{_WRAP_END}"
    assert content_after_wrap(wrapped) == "the inner content"


def test_legacy_unwrapped_payload_returns_verbatim() -> None:
    """No markers at all is the legacy-record case (pre-sanitizer findings.json
    entries, or any non-sanitized string) — return as-is, never raise."""
    assert content_after_wrap("plain text") == "plain text"
    assert content_after_wrap("") == ""


def test_half_wrap_begin_only_raises_strip_error() -> None:
    payload = f"{_WRAP_BEGIN}content with no END marker"
    with pytest.raises(StripError):
        content_after_wrap(payload)


def test_half_wrap_end_only_raises_strip_error() -> None:
    payload = f"content with no BEGIN marker{_WRAP_END}"
    with pytest.raises(StripError):
        content_after_wrap(payload)


def test_empty_wrap_returns_empty_string() -> None:
    """Edge case: sanitizer wrapped an empty string. The strip should yield ''.
    Upstream empty-content checks catch this case at MISSING_REQUIRED_FIELD."""
    wrapped = f"{_WRAP_BEGIN}{_WRAP_END}"
    assert content_after_wrap(wrapped) == ""


def test_idempotent_on_already_clean_text() -> None:
    """`compose._unwrap_evidence` calls this at report-render time. Repeated calls
    on already-clean text must not throw, must not modify."""
    cleaned = content_after_wrap("clean")
    assert content_after_wrap(cleaned) == "clean"
