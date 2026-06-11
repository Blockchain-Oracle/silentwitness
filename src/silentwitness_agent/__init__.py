"""SilentWitness reference agent — Pydantic AI investigator + specialists.

Reference implementation showing how to drive the silentwitness_mcp server
through a model-agnostic hypothesis-pivot loop. See ``docs/architecture.md``
§5 for the deep spec.
"""

from silentwitness_common.version import __version__ as __version__

__all__ = ["__version__"]
