# Story — GitHub Actions CI workflows

**ID:** story-ci-workflows
**Epic:** Epic 1 — Project scaffolding + CI/CD on commit 1
**Depends on:** story-scaffold-uv-pyproject
**Estimate:** ~2h
**Status:** PENDING

---

## User story

**As a** SilentWitness coding agent
**I want to** wire up `.github/workflows/ci.yml`, `release.yml`, and `dependency-review.yml` per CICD_SPEC §4
**So that** every PR + push to main is gated by lint / typing / tests / property tests / file-size / SBOM / license-check / dependency-review and main merges produce a GHCR image (PRD §10 deliverables 1+7; CICD_SPEC §1.2 contributes to Constraint Implementation + Audit Trail + Usability).

---

## File modification map

- `.github/workflows/ci.yml` — NEW — verbatim from CICD_SPEC §4.1: jobs `lint`, `test (matrix 3.12+3.13)`, `property-tests`, `file-size-guard`, `dataset-hash-verify`, `sbom`, `license-check`, `docker-build` (~210 LOC).
- `.github/workflows/release.yml` — NEW — verbatim from CICD_SPEC §4.2: `semantic-release` job + versioned GHCR push (~55 LOC).
- `.github/workflows/dependency-review.yml` — NEW — verbatim from CICD_SPEC §4.3: action call with `fail-on-severity: high` and AGPL/GPL-3 deny list (~25 LOC).
- `.github/dependabot.yml` — NEW — CICD_SPEC §12 verbatim: weekly pip + github-actions + docker schedules with `python-dev` / `python-prod` groups (~70 LOC).
- `scripts/license_gate.py` — NEW — parses `licenses.json` from `pip-licenses` and exits non-zero on AGPL / GPL-3.0 / Proprietary; called by the `license-check` job (~60 LOC).
- `scripts/coverage_gate.py` — NEW — parses `coverage.xml`, enforces per-module floors: `verification/` 95%, `audit/` 90%, other `src/` 85%; called by the `test` job (~80 LOC).
- `harness/datasets/verify_manifest.py` — NEW (stub) — `--stub-only` flag returns 0 with no manifests present; future stories under E14 implement the real check (~25 LOC).
- `tests/unit/test_ci_scripts.py` — NEW — 6 behavioral tests: license_gate accepts MIT/Apache/BSD, rejects AGPL-3.0, rejects GPL-3.0, accepts LGPL-3.0; coverage_gate enforces 95% floor on `verification/`, 90% floor on `audit/`.

---

## Acceptance criteria (BDD — machine-verifiable)

```
Given .github/workflows/ci.yml exists
When  `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` runs
Then  exit code is 0 (valid YAML)

Given the workflow declares the jobs from CICD_SPEC §4.1
When  `grep -E '^\s{2}(lint|test|property-tests|file-size-guard|dataset-hash-verify|sbom|license-check|docker-build):' .github/workflows/ci.yml | wc -l` runs
Then  output is 8

Given scripts/license_gate.py exists
When  `echo '[{"License":"AGPL-3.0"}]' | uv run python scripts/license_gate.py /dev/stdin` runs
Then  exit code is 1
And   stderr contains "AGPL"

Given scripts/license_gate.py exists
When  `echo '[{"License":"MIT"},{"License":"Apache-2.0"},{"License":"BSD-3-Clause"}]' > /tmp/lic.json && uv run python scripts/license_gate.py /tmp/lic.json` runs
Then  exit code is 0

Given scripts/coverage_gate.py exists
When  `uv run pytest tests/unit/test_ci_scripts.py -v` runs
Then  exit code is 0
And   6 tests pass

Given a coverage.xml fixture with verification/ at 94%
When  scripts/coverage_gate.py is invoked
Then  exit code is 1
And   stderr names `verification` and the floor 95

Given .github/workflows/release.yml exists
When  `grep -E 'semantic-release version' .github/workflows/release.yml` runs
Then  the line is present (release pipeline wired)

Given .github/workflows/dependency-review.yml exists
When  `grep -E 'deny-licenses:.*AGPL-3.0' .github/workflows/dependency-review.yml` runs
Then  the line is present (copyleft block wired)

Given .github/dependabot.yml exists
When  `grep -c 'package-ecosystem' .github/dependabot.yml` runs
Then  output is 3 (pip + github-actions + docker)
```

---

## Shell verification

```bash
# YAML validity for all three workflows + dependabot
for f in .github/workflows/ci.yml .github/workflows/release.yml .github/workflows/dependency-review.yml .github/dependabot.yml; do
  uv run python -c "import yaml,sys; yaml.safe_load(open('$f'))" || exit 1
done

# Job list parity with CICD_SPEC §4.1
test "$(grep -cE '^  (lint|test|property-tests|file-size-guard|dataset-hash-verify|sbom|license-check|docker-build):' .github/workflows/ci.yml)" -eq 8

# license_gate.py behavior
echo '[{"License":"MIT"}]' > /tmp/lic-ok.json
uv run python scripts/license_gate.py /tmp/lic-ok.json
test $? -eq 0
echo '[{"License":"AGPL-3.0"}]' > /tmp/lic-bad.json
uv run python scripts/license_gate.py /tmp/lic-bad.json
test $? -eq 1

# Unit tests
uv run pytest tests/unit/test_ci_scripts.py -v
# Must show 6 passing

# §14 no-mocks check
git diff main...HEAD -- 'src/**' | grep -E "^\+" | grep -iE "(mock|fake|dummy|hardcoded)" | grep -v "test\|spec"
# Must output nothing

# Lint + type clean
uv run ruff check scripts/ harness/
uv run mypy --strict scripts/ harness/
```

---

## Notes for coding agent

- Reference: CICD_SPEC.md §4 (workflow YAML verbatim), §8 (coverage policy), §10 (SBOM + supply chain), §12 (dependabot YAML verbatim).
- Reference: PRD.md §10 (deliverables 1 + 6 + 7 — repo + accuracy report + setup instructions all rely on CI artifacts).
- Reference: architecture.md §14 (CI gates the architecture relies on).
- Copy the YAML from CICD_SPEC §4.1 / §4.2 / §4.3 / §12 character-for-character. Do NOT improvise. The job names must match the branch-protection required-status-checks list in CICD_SPEC §5.1.
- `license_gate.py` and `coverage_gate.py` are referenced from CICD_SPEC §4.1 + §8.2 but no implementation is given there — write them fresh. Keep each ≤80 LOC.
- `harness/datasets/verify_manifest.py` is a stub here because Epic 14 owns the dataset manifests. The `--stub-only` flag should return 0 with a printed "no manifests present (E14 not yet merged)" log. Do not implement real hash verification in this story.
- The `docker-build` job has `needs:` on all earlier jobs and `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` — it does NOT run on PRs. The Dockerfile and `docker-compose.yml` are written in story-docker-baseline; this story only wires the workflow.
- Do NOT enable auto-merge for Dependabot PRs (CICD_SPEC §12.1 defers post-hackathon).
- Library docs to consult via Context7 BEFORE writing the workflows:
  - `astral-sh/setup-uv@v4` topic `python install` (the `uv python install` invocation pattern).
  - `actions/dependency-review-action@v4` topic `fail-on-severity deny-licenses` (the verbatim arg names).
- The branch-protection apply step (CICD_SPEC §5.2) is NOT in this story — it runs once by the repo owner after the first green CI run.
