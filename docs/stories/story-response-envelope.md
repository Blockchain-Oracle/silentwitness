# Story — Response envelope (Pydantic-typed tool response shape)

**ID:** story-response-envelope
**Epic:** Epic 4 — MCP server skeleton + finding-state tools
**Depends on:** story-common-types, story-audit-logger
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** consumer of any SilentWitness MCP tool (the reference agent, a third-party MCP client, the critic, the report renderer)
**I want to** receive a uniform `ToolResponse` envelope on every tool call carrying success, data, audit_id, examiner, caveats, advisories, corroboration, discipline_reminder, and data_provenance
**So that** downstream consumers can compose tool calls into hypothesis-driven workflows with a single deserialization path — and judges can read the audit trail without per-tool documentation

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/envelope.py` — NEW — `ToolResponse[TPayload]` generic Pydantic model + `DataProvenance` + `Confidence` enums; the exact shape from architecture.md §4.3 (≤180 LOC)
- `src/silentwitness_common/types.py` — UPDATE — re-export the envelope types so agents importing from common get a stable surface (≤20 LOC delta)
- `tests/unit/test_envelope.py` — NEW — ≥12 BDD test cases covering: success path, failure path, JSON round-trip, generic payload binding, default field values, discriminator behavior

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given a successful tool call producing a typed payload P
When  ToolResponse[P](success=True, data=payload, audit_id="sift-aj-20260613-001", examiner="aj", data_provenance=<DP>) is constructed
Then  the envelope validates without error
And   .model_dump_json() round-trips through .model_validate_json() identically

Given a failed tool call
When  ToolResponse(success=False, data=None, audit_id=<id>, examiner=<name>, advisories=["MOUNT_NOT_RO_NOEXEC_NOSUID"], data_provenance=<DP>) is constructed
Then  the envelope validates
And   data is None
And   advisories is non-empty

Given a ToolResponse with caveats=["Shimcache proves PRESENCE not EXECUTION"]
When  the envelope is rendered
Then  caveats appears as a list field in the JSON output
And   the field is preserved through serialization round-trip

Given a ToolResponse with data_provenance carrying tool="vol_pslist", stdout_path=/cases/.../blobs/sift-aj-20260613-007.txt, result_sha256=<64hex>, elapsed_ms=234.5, cmd_argv=["/opt/volatility3/bin/vol", "-f", "/evidence/mem.raw", "windows.pslist.PsList"]
When  the envelope is validated
Then  data_provenance.tool == "vol_pslist"
And   data_provenance.result_sha256 matches ^[a-f0-9]{64}$
And   data_provenance.stdout_path resolves to a Path object
And   data_provenance.elapsed_ms is float

Given a ToolResponse missing required fields (audit_id, examiner, or data_provenance)
When  construction is attempted
Then  pydantic.ValidationError is raised

Given a ToolResponse with confidence=Confidence.HIGH (LOW | MEDIUM | HIGH enum)
When  the envelope is serialized
Then  the confidence renders as the string "HIGH"
And   round-trip parses back to the enum

Given a ToolResponse with discipline_reminder="cross-check pstree before claiming malice"
When  rendered
Then  the field is preserved
And   it is documented in the model as supplementary / prompt-layer hint (NOT load-bearing)

Given a generic-parameterized ToolResponse[VolPslistOutput]
When  mypy --strict checks the file
Then  no errors are raised
And   the bound type is preserved at runtime via __orig_class__

Given the envelope test module is run with coverage
When  uv run coverage run -m pytest tests/unit/test_envelope.py
Then  line coverage on src/silentwitness_mcp/envelope.py is ≥95%
```

---

## Shell verification

```bash
# Tests pass with ≥12 cases
uv run pytest tests/unit/test_envelope.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥12

# Coverage ≥95% on the file
uv run coverage run -m pytest tests/unit/test_envelope.py
uv run coverage report --include="src/silentwitness_mcp/envelope.py" --fail-under=95

# Lint + strict types
uv run ruff check src/silentwitness_mcp/envelope.py
uv run mypy --strict src/silentwitness_mcp/envelope.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/envelope.py)" -le 400 ]

# All §4.3 fields present in the model definition
for field in success data audit_id examiner caveats advisories corroboration discipline_reminder data_provenance; do
  grep -q "$field" src/silentwitness_mcp/envelope.py || { echo "missing field $field"; exit 1; }
done

# DataProvenance has architecture-mandated fields
for field in tool stdout_path result_sha256 elapsed_ms cmd_argv; do
  grep -q "$field" src/silentwitness_mcp/envelope.py || { echo "missing DataProvenance field $field"; exit 1; }
done
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.3 (response envelope — Pydantic model with verbatim field list); §4.4 (audit log + audit_id format); §5.2 framing reference from brief — note architecture.md uses §4.3 numbering for the envelope.
- The model verbatim from architecture.md §4.3:
  ```python
  class ToolResponse(BaseModel, Generic[TPayload]):
      success: bool
      data: TPayload | None
      audit_id: str                          # sift-<examiner>-<YYYYMMDD>-<NNN>
      examiner: str
      caveats: list[str] = Field(default_factory=list)
      advisories: list[str] = Field(default_factory=list)
      corroboration: list[str] = Field(default_factory=list)
      discipline_reminder: str | None = None
      data_provenance: DataProvenance
  ```
- `DataProvenance` fields (architecture.md §4.3 paragraph 2): `tool: str`, `stdout_path: Path`, `result_sha256: str`, `elapsed_ms: float`, `cmd_argv: list[str]`. These five enable the citation gate (story-citation-gate) to verify cited spans.
- `Confidence` enum: `LOW | MEDIUM | HIGH`. Used by `record_interpretation` (story-record-interpretation-tool).
- Field semantics (architecture.md §4.3 paragraph 3, verbatim framing):
  - `caveats`: per-tool methodology notes ("Shimcache proves PRESENCE not EXECUTION" — Valhuntir's pattern).
  - `advisories`: runtime concerns ("output truncated at 50K rows; consider narrower query").
  - `corroboration`: cross-artifact hints ("if pstree shows abnormal parent, also check `vol_handles` for the child").
  - `discipline_reminder`: optional prompt-layer hint — DOCUMENT in the field docstring that this is supplementary, not load-bearing (architecture.md §4.3 paragraph 3 final sentence).
- Generic over `TPayload: BaseModel`. Use `pydantic.BaseModel`'s generic support: `class ToolResponse(BaseModel, Generic[TPayload])`. Pydantic v2 native generics work; do NOT use `pydantic.generics.GenericModel` (deprecated).
- The audit_id format `sift-<examiner_short>-<YYYYMMDD>-<NNN>` is enforced by a Pydantic `field_validator`. Reject malformed IDs at construction time.
- JSON round-trip: every envelope must survive `model_dump_json()` → `model_validate_json()` unchanged. This is what allows the audit log writer to persist and the report renderer to consume.
- The envelope is a single source of truth for all 27 MCP tools (architecture.md §4.2). Per-tool output types parameterize the `TPayload` generic. Coding agents in Epic 5–7 will import this model.
- The audit log writer (story-audit-logger) consumes `ToolResponse` and emits one JSONL line per call. The envelope's fields map 1:1 to the audit JSONL schema (architecture.md §4.4) — keep the names identical for serialization symmetry.
- Context7 hints: `mcp__plugin_context7_context7__resolve-library-id libraryName="pydantic"`, then query topic "generic models v2 Generic TPayload". The Pydantic v2 generic syntax differs from v1.
- Vocabulary: never "court-admissible." Envelope is "the audit-trail unit of work."
- Known pitfalls: (1) Pydantic v2 generics require Python 3.12+ syntax — we are on 3.12 per `PRD` §6; (2) `Path` fields serialize to strings in JSON — round-trip yields `PosixPath` even on Windows-origin paths (fine; we run on Ubuntu); (3) `field_validator` for `audit_id` must run BEFORE `model_validator(mode="before")` if you also need to coerce — order matters in Pydantic v2.
