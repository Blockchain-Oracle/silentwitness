"""Hypothesis profile registration for the property-test suite.

Three profiles per CICD_SPEC §4.1 + story-gates-property-tests:

* ``dev`` (50 examples) — fast feedback during local edits.
* ``ci`` (500 examples) — the CI ``property-tests`` job floor.
* ``slow`` (5000 examples) — overnight / pre-release exhaustive runs.

The profile is selected by ``HYPOTHESIS_PROFILE`` env var; default is
``dev`` so a developer who runs ``uv run pytest`` doesn't pay the 500-
example cost without asking.
"""

from __future__ import annotations

import os

from hypothesis import settings

settings.register_profile("dev", max_examples=50, deadline=None)
settings.register_profile("ci", max_examples=500, deadline=None)
settings.register_profile("slow", max_examples=5000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))
