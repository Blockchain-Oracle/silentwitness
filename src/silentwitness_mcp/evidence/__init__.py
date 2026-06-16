"""Evidence registry — refuse-on-unregistered structural defense.

The registry (architecture.md §4.10) is one of the architectural
boundaries that make finding-path fabrication mechanically impossible:
every tool wrapper calls
:meth:`~silentwitness_mcp.evidence.registry.EvidenceRegistry.assert_registered`
before invoking the underlying forensic CLI, so a hallucinated evidence path
fails closed before any artefact is touched.
"""
