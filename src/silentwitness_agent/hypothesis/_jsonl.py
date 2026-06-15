"""Hypothesis event JSONL emission — atomic append to audit/hypothesis.jsonl."""

from __future__ import annotations

from pathlib import Path

from silentwitness_agent.hypothesis.types import HypothesisEvent
from silentwitness_mcp.audit.chain import append_chained_jsonl_line


def emit_hypothesis_event(case_dir: Path, event: HypothesisEvent) -> None:
    """Append one HypothesisEvent line to ``<case_dir>/audit/hypothesis.jsonl``.

    Uses the same fsync-after-append discipline as the MCP audit logger
    (via ``append_jsonl_line``) so the JSONL file survives a process crash
    mid-write without corruption.
    """
    log_path = case_dir / "audit" / "hypothesis.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    append_chained_jsonl_line(log_path, event.model_dump_json())


__all__ = ["emit_hypothesis_event"]
