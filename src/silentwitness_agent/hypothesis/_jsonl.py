"""Hypothesis event JSONL emission — atomic append to audit/hypothesis.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

from silentwitness_agent.hypothesis.types import HypothesisEvent
from silentwitness_mcp.audit.chained_jsonl import append_chained_jsonl


def emit_hypothesis_event(case_dir: Path, event: HypothesisEvent) -> None:
    """Append one HypothesisEvent line to ``<case_dir>/audit/hypothesis.jsonl``.

    Uses the same hash-chain discipline as the MCP audit logger without taking
    the logger's per-case singleton lock.
    """
    log_path = case_dir / "audit" / "hypothesis.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    append_chained_jsonl(log_path, json.loads(event.model_dump_json()))


__all__ = ["emit_hypothesis_event"]
