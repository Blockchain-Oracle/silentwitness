"""Tool-wrapper package for SilentWitness MCP server.

Each submodule groups the wrappers for one investigative family
(memory, disk, log, network, registry). Wrappers share infrastructure
from :mod:`silentwitness_mcp.tools._vol_common` (for Volatility3) and
its siblings, keeping the per-tool body small (≤35 LOC after the
skeleton story per CICD_SPEC §6.1)."""
