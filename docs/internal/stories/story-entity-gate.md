# Story — Entity gate (NER + regex catalog + cited-span substring check)

**ID:** story-entity-gate
**Epic:** Epic 3 — Verification gates
**Depends on:** story-output-normalizer, story-citation-gate
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness MCP server processing a `record_observation` call
**I want to** extract every DFIR-relevant entity from the observation text (file paths, IPs, hashes, registry keys, accounts, mutexes, URLs, ports, emails, process names) and require each one to appear in at least one cited span
**So that** an agent cannot fabricate an IOC, path, or hash that was never in the evidence — making extrinsic / gap-filling hallucination architecturally impossible

---

## File modification map

Exact files the coding agent creates or modifies:

- `src/silentwitness_mcp/verification/entity_gate.py` — NEW — `verify_entities(observation_text, cited_spans) -> EntityResult`; runs spaCy NER + regex catalog + substring check (≤350 LOC, split into helper if approaching ceiling; architecture.md §4.7)
- `src/silentwitness_mcp/verification/_entity_patterns.py` — NEW — versioned regex catalog (IPv4, IPv6, MD5, SHA1, SHA256, registry keys, Windows paths, POSIX paths, account names, mutex names, port numbers with context tag, emails, URLs) (≤200 LOC)
- `tests/unit/verification/test_entity_gate.py` — NEW — ≥20 BDD test cases covering each entity type + valid/invalid + hallucination rejection

The coding agent must NOT modify files outside this map.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given observation_text "svchost.exe at PID 1208 has parent cmd.exe at PID 4172"
And   a cited_span whose span_text contains the same process names and PIDs verbatim
When  verify_entities(observation_text, [cited_span]) is called
Then  the result is EntityResult(success=True, extracted=["svchost.exe", "cmd.exe", "1208", "4172"], hallucinated=[])

Given observation_text "Ethereal.exe was installed at C:\\Tools\\Ethereal\\"
And   a cited_span whose span_text contains "Ethereal.exe at C:\\Program Files\\Ethereal\\" (different path)
When  verify_entities(observation_text, [cited_span]) is called
Then  the result is EntityResult(success=False, reason="HALLUCINATED_ENTITIES", hallucinated=["C:\\Tools\\Ethereal\\"])

Given observation_text containing the IPv4 "192.168.4.7" not present in any cited span
When  verify_entities is called
Then  the hallucinated list contains "192.168.4.7"
And   success is False

Given observation_text containing the SHA256 "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" present in the cited span  <!-- pragma: allowlist secret  -- well-known SHA-256 of the empty string, not a credential -->
When  verify_entities is called
Then  the SHA256 is in extracted entities
And   success is True

Given observation_text containing a registry key HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Run present in the cited span verbatim
When  verify_entities is called
Then  the registry key is in extracted entities
And   success is True

Given observation_text containing an account name DOMAIN\\Administrator not present in any cited span
When  verify_entities is called
Then  hallucinated contains "DOMAIN\\Administrator"
And   success is False

Given observation_text containing the literal phrase "port 4444" present in the cited span "outbound connection to port 4444"
When  verify_entities is called
Then  "4444" is in extracted entities
And   success is True

Given observation_text "the malicious URL was https://evil.example/c2.php" matched against a cited_span containing the same URL
When  verify_entities is called
Then  "https://evil.example/c2.php" is in extracted entities
And   success is True

Given observation_text with mixed-case path "c:\\program files\\ethereal\\" and cited span with "C:\\Program Files\\Ethereal\\"
When  verify_entities is called (case-insensitive, path-normalized)
Then  the path is matched and success is True

Given the entity gate test module is run with coverage
When  uv run coverage run -m pytest tests/unit/verification/test_entity_gate.py
Then  line coverage on src/silentwitness_mcp/verification/entity_gate.py is ≥95%
```

---

## Shell verification

```bash
# spaCy model must be installed
uv run python -c "import spacy; spacy.load('en_core_web_lg')"

# Tests pass with ≥20 behavioral test cases
uv run pytest tests/unit/verification/test_entity_gate.py -v 2>&1 | grep -E "PASSED|FAILED" | wc -l
# Must output ≥20

# Coverage floor 95% (per CICD_SPEC §8)
uv run coverage run -m pytest tests/unit/verification/test_entity_gate.py
uv run coverage report --include="src/silentwitness_mcp/verification/entity_gate.py" --fail-under=95

# Each entity type has at least one test
for kind in ipv4 ipv6 md5 sha1 sha256 registry_key windows_path posix_path account mutex port email url; do
  grep -qi "$kind" tests/unit/verification/test_entity_gate.py || { echo "missing test for $kind"; exit 1; }
done

# Lint + types
uv run ruff check src/silentwitness_mcp/verification/entity_gate.py
uv run mypy --strict src/silentwitness_mcp/verification/entity_gate.py

# File-size guard
[ "$(wc -l < src/silentwitness_mcp/verification/entity_gate.py)" -le 400 ]
[ "$(wc -l < src/silentwitness_mcp/verification/_entity_patterns.py)" -le 400 ]
```

---

## Notes for coding agent

- Source of truth: architecture.md §4.7 (entity gate algorithm — 5 steps, regex catalog listed verbatim); ADR-006 (rationale for spaCy + regex over LLM-as-extractor).
- The function signature: `def verify_entities(observation_text: str, cited_spans: Sequence[CitedSpan]) -> EntityResult`.
- spaCy load is expensive (~750MB model, ~3s first load). Lazy-load the model at first call and cache at module level: `_nlp: spacy.Language | None = None`; `def _get_nlp() -> spacy.Language`. Mark this module as not safe for fork-multiprocessing without re-initialization.
- spaCy NER pulled types per architecture.md §4.7: `PERSON`, `ORG`, `GPE`, `PRODUCT`, `WORK_OF_ART`. The regex catalog covers DFIR-specific entities NER misses.
- Regex catalog patterns (verbatim from architecture.md §4.7):
  - IPv4: `\b(?:\d{1,3}\.){3}\d{1,3}\b`
  - IPv6: standard RFC-5952 (vendor a tested pattern; do NOT write a naive one — comment-cite the source)
  - MD5: `\b[a-fA-F0-9]{32}\b`
  - SHA1: `\b[a-fA-F0-9]{40}\b`
  - SHA256: `\b[a-fA-F0-9]{64}\b`
  - Registry keys: `HK(LM|CU|U|CR|CC)\\[^\s"']+`
  - Windows paths: `[A-Za-z]:\\(?:[^\\<>:"|?*\r\n]+\\?)+`
  - POSIX paths: `/(?:[^/\s]+/?)+` (with prose-punctuation guard)
  - Account names: `[A-Za-z][A-Za-z0-9_-]+\\[A-Za-z][A-Za-z0-9_.$-]+`
  - Mutex names: `(?:Global|Local)\\[A-Za-z0-9_\-.{}]+`
  - Port numbers: extract `\d{1,5}` only when `port` is the immediately adjacent context word
  - Emails: simplified RFC-5322 (vendor a tested pattern)
  - URLs: `https?://[^\s)<>"']+`
- Substring check is case-insensitive AND path-normalized (using the same normalization as `verification/normalizer.py` path-separator step). This catches the demo case: cited span "C:\Program Files\..." vs observation "c:/program files/...".
- Hash overlap: SHA1 regex (40 hex) is a prefix of SHA256 regex (64 hex). Apply SHA256 first, then SHA1 on the residual. Add an explicit test case.
- `EntityResult` shape (Pydantic v2 tagged union):
  - `EntityResult(success=True, extracted=list[ExtractedEntity], hallucinated=[])`
  - `EntityResult(success=False, reason=Literal["HALLUCINATED_ENTITIES"], extracted=list[ExtractedEntity], hallucinated=list[ExtractedEntity])`
- `ExtractedEntity` carries: `text: str`, `kind: EntityKind`, `source: Literal["spacy", "regex"]`.
- Performance: ~30s for the gate test suite is acceptable per ADR-006. Use `pytest -x --hypothesis-profile dev` in tight loops.
- Context7 hints: `mcp__plugin_context7_context7__resolve-library-id libraryName="spacy"`, then query topic "named entity recognition en_core_web_lg patterns".
- Vocabulary: never "court-admissible." The entity gate is a structural rejection, not a marketing claim.
- Known pitfalls: (1) spaCy NER on short fragments is noisy; we accept that and let the substring check filter; (2) the port regex is contextual — do NOT extract bare numbers; (3) Windows path regex must accept trailing backslash for directories.
