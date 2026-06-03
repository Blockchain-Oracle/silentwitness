# Story — Third-Party License NOTICES File

**ID:** story-third-party-notices
**Epic:** Epic 16 — Documentation polish + submission
**Depends on:** story-readme-polish
**Estimate:** ~1h
**Status:** PENDING

---

## User story

**As a** SilentWitness submission packager
**I want to** ship a NOTICES file aggregating all third-party license attributions
**So that** the MIT-licensed SilentWitness submission cleanly attributes every GPL/AGPL/Apache/BSD-licensed tool, library, and dataset we subprocess-invoke or depend on, satisfying judging-criterion Usability + protecting the submission from license-compliance challenges.

---

## File modification map

- `NOTICES.md` — NEW — ≤400 LOC. Aggregates license + attribution + version for every third-party component.
- `scripts/build_notices.py` — NEW — ≤200 LOC. Auto-builds NOTICES.md by walking pyproject.toml + install.sh + tool catalog. Stable ordering (alphabetic). Includes license SPDX + canonical URL + copyright holder + version pinned.
- `tests/unit/test_build_notices.py` — NEW — ≥6 BDD scenarios.

The coding agent must NOT modify files outside this map without re-checking CLAUDE.md.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given the SilentWitness repo at HEAD with pyproject.toml + install.sh populated
When `uv run python scripts/build_notices.py` runs
Then NOTICES.md is created at repo root
And it contains entries for every Python dep in pyproject.toml (sorted alphabetically)
And it contains entries for every binary installed by install.sh (Hayabusa, Chainsaw, Velociraptor, Zeek, Suricata, Vol3, EZ Tools)
And every entry has: name | version | SPDX license | source URL | copyright holder

Given a third-party component with an unknown SPDX license
When build_notices.py is called
Then exit 1 with reason "UNKNOWN_LICENSE: <component>"

Given the SilentWitness binary itself
When NOTICES.md is rendered
Then the header includes "SilentWitness is licensed under MIT" + "This NOTICES file aggregates third-party attributions per their respective licenses"

Given a GPL-3.0 or AGPL-3.0 component is included
When build_notices.py runs
Then NOTICES.md includes the verbatim license-grant clause for that component (sourced from spdx.org/licenses)
```

---

## Shell verification

```bash
uv run python scripts/build_notices.py
test -f NOTICES.md
grep -E "^## (Hayabusa|Chainsaw|Velociraptor|Zeek|Suricata|Volatility 3|MFTECmd|Pydantic AI|MCP)" NOTICES.md | wc -l
# Must show ≥ 9

uv run pytest tests/unit/test_build_notices.py -v
# Must show ≥ 6 passing tests

uv run ruff check scripts/build_notices.py
uv run mypy --strict scripts/build_notices.py
# Both exit 0
```

---

## Notes for coding agent

- This story satisfies a soft hackathon-rule requirement (judges look for clean license attribution under the Usability criterion).
- SPDX license IDs to support: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, GPL-2.0-only, GPL-3.0-only, AGPL-3.0-only, MPL-2.0, ISC.
- For AGPL components (Velociraptor): we subprocess-invoke; no conveyance trigger; include verbatim grant clause.
- For Vol3: Vol3 is OSL-3.0; flag specially.
- Pydantic AI, MCP, FastMCP: MIT.
- WeasyPrint: BSD-3-Clause.
- spaCy + en_core_web_lg: MIT + CC BY-SA 4.0 (the model has separate license).
- EZ Tools: MIT (per EricZimmerman repos).
- Hayabusa: GPL-3.0.
- Chainsaw: GPL-3.0.
- Suricata: GPL-2.0.
- Reference: `docs/CICD_SPEC.md` §10 SBOM gate ties into this; cyclonedx-py output should include the same license metadata.
- Vocab discipline: no "court-admissible", no "Ralph Wiggum Loop".
