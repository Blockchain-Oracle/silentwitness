"""Case-context bridge across the MCP stdio boundary (architecture §4.1/§4.10).

The investigator runs the MCP server as a *separate subprocess*
(``MCPServerStdio("python", ["-m", "silentwitness_mcp"], ...)``). Pydantic-AI
does NOT forward the parent environment to that subprocess by default, so the
server has no idea which case it is serving — and forensic tools need
``case_dir`` / ``examiner`` / ``model_used`` to construct their
:class:`~silentwitness_mcp.evidence.registry.EvidenceRegistry` and
:class:`~silentwitness_mcp.audit.logger.AuditLogger`.

This module is the single source of truth for that contract: the CLI side calls
:func:`build_server_env` when spawning the server, and the server's lifespan
calls :func:`read_case_env` at startup. Both import the same constants so the
two ends can never drift to different env-var names.

A run serves exactly one case, so the binding is process-wide and immutable for
the server's lifetime — no per-call case routing is needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ENV_CASE_DIR: Final = "SILENTWITNESS_CASE_DIR"
ENV_EXAMINER: Final = "SILENTWITNESS_EXAMINER"
ENV_MODEL_USED: Final = "SILENTWITNESS_MODEL_USED"

# Parent-process vars the server genuinely needs but which MCPServerStdio drops
# by default: ANTHROPIC_API_KEY for MCP sampling, PATH so shutil.which() resolves
# vol/zeek/chainsaw, HOME for tools that read ~/.config, and the gateway token
# for the (unused-on-stdio but harmless) HTTP auth path.
PASSTHROUGH_ENV: Final[tuple[str, ...]] = (
    "PATH",
    "HOME",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "GOOGLE_API_KEY",
    "SILENTWITNESS_GATEWAY_TOKEN",
    "SILENTWITNESS_MODEL",
)


@dataclass(slots=True, frozen=True)
class CaseEnv:
    """The case binding read from the environment by the server subprocess."""

    case_dir: Path
    examiner: str
    model_used: str


def build_server_env(case_dir: Path, examiner: str, model_used: str) -> dict[str, str]:
    """Construct the env dict for ``MCPServerStdio(env=...)``.

    Carries the three case vars plus a curated passthrough of parent-process
    vars the server depends on. We pass an explicit dict rather than
    ``os.environ`` so the subprocess surface stays minimal and auditable.
    """
    env: dict[str, str] = {
        ENV_CASE_DIR: str(case_dir),
        ENV_EXAMINER: examiner,
        ENV_MODEL_USED: model_used,
    }
    for key in PASSTHROUGH_ENV:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    return env


def read_case_env() -> CaseEnv | None:
    """Read the case binding inside the server subprocess.

    Returns ``None`` when the case vars are absent — the legitimate state for
    unit/integration tests and bare ``python -m silentwitness_mcp`` boots, where
    the server must still start (tools then refuse with a typed
    misconfiguration error rather than crashing at import).
    """
    case_dir = os.environ.get(ENV_CASE_DIR)
    examiner = os.environ.get(ENV_EXAMINER)
    model_used = os.environ.get(ENV_MODEL_USED)
    if not case_dir or not examiner or not model_used:
        return None
    return CaseEnv(case_dir=Path(case_dir), examiner=examiner, model_used=model_used)


__all__ = [
    "ENV_CASE_DIR",
    "ENV_EXAMINER",
    "ENV_MODEL_USED",
    "PASSTHROUGH_ENV",
    "CaseEnv",
    "build_server_env",
    "read_case_env",
]
