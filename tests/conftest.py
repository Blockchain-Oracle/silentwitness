"""Hypothesis profile registration + audit-chain cache reset for the test suite.

Three Hypothesis profiles per CICD_SPEC §4.1 + story-gates-property-tests:

* ``dev`` (50 examples) — fast feedback during local edits.
* ``ci`` (500 examples) — the CI ``property-tests`` job floor.
* ``slow`` (5000 examples) — overnight / pre-release exhaustive runs.

The profile is selected by ``HYPOTHESIS_PROFILE`` env var; default is
``dev`` so a developer who runs ``uv run pytest`` doesn't pay the 500-
example cost without asking.

The autouse ``_reset_audit_chain_cache`` fixture below clears
``silentwitness_mcp.audit.chain._LAST_HASH_CACHE`` between every test so
process-scoped chain state never leaks across cases. Without it, a test
that writes a chained row leaves the cache populated, and a sibling test
that reuses the same ``tmp_path`` shape (or writes to a different file
with the same resolved path under a chdir'd cwd) can see a stale head
and write a chain that passes verify locally but breaks in production
where the cache starts cold.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from hypothesis import settings

from silentwitness_mcp.audit.chain import _reset_chain_cache

settings.register_profile("dev", max_examples=50, deadline=None)
settings.register_profile("ci", max_examples=500, deadline=None)
settings.register_profile("slow", max_examples=5000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


@pytest.fixture(autouse=True)
def _reset_audit_chain_cache() -> Iterator[None]:
    """Clear the chain helper's process-scoped state before AND after every
    test. Both sides matter: before guards against cache leakage from a
    test that crashed before its own cleanup; after guards against the
    same leakage going forward."""
    _reset_chain_cache()
    yield
    _reset_chain_cache()
