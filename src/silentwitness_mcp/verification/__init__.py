"""Verification gates — citation gate, entity gate, sanitizer, output normalizer.

The wedge's hot path. Every tool wrapper passes its raw stdout through
:func:`silentwitness_mcp.verification.normalizer.normalize_output` before
hashing; the citation gate (architecture §4.5) re-hashes the same byte
range later and refuses observations whose ``content_sha256`` no longer
matches. Drift between "what the model saw" and "what the gate verifies"
is the silent-failure surface this package closes.
"""

from silentwitness_mcp.verification.normalizer import normalize_output

__all__ = ["normalize_output"]
