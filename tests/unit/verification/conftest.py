"""Per-test isolation for the verification module's process-global caches.

The entity-gate spaCy model and the injection-pattern catalog are both
loaded once at module level (intentionally — production wants the
amortised cost). Tests that monkeypatch the underlying load mechanism
(``spacy.load``, ``_injection_loader._PATTERNS_PATH``) would otherwise
poison sibling tests via the leftover cached state.

Tracked as PR-110 round-2 fix (entity gate) and PR-114 round-2 fix
(sanitizer injection-pattern cache).
"""

from __future__ import annotations

from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def reset_verification_module_caches() -> Generator[None, None, None]:
    """Snapshot + restore module-level caches around each test."""
    from silentwitness_mcp.verification import _injection_loader, entity_gate

    nlp_snapshot = entity_gate._nlp_cache
    catalog_snapshot = _injection_loader._patterns_cache
    yield
    entity_gate._nlp_cache = nlp_snapshot
    _injection_loader._patterns_cache = catalog_snapshot
