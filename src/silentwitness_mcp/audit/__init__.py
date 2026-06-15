"""JSONL audit logger for MCP tool calls.

Every MCP tool call emits one append-only line to ``cases/<case>/audit/<backend>.jsonl``.
The ``audit_id`` is the load-bearing primitive that joins the audit log with the
HMAC ledger, the report's inline verify links, and the citation gate.

See ``docs/architecture.md`` §4.4 for the JSONL schema and sequence-resume
semantics, and ``docs/internal/BRAINSTORM.md`` §4 for the entry-shape spec.
"""
