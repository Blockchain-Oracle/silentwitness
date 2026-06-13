"""Server lifespan — startup checks + shutdown flushers (architecture §4.1, §4.11).

Three responsibilities:

* ``check_mount`` — runs ``findmnt -n -o OPTIONS --target /evidence/`` per
  architecture §4.11 and returns ``(ok, advisories)``. Fails closed (returns
  ``ok=False`` when the mount is missing ``ro,noexec,nosuid``) but skips
  cleanly on dev/test environments where the mount or ``findmnt`` is absent
  so the FastMCP server can still boot for unit/integration tests.
* ``warm_injection_patterns`` — triggers the singleton YAML load in
  :mod:`silentwitness_mcp.verification._injection_loader` so the first tool
  call doesn't pay the load cost (architecture §4.8 — sanitizer hot path).
* ``lifespan`` — the ``@asynccontextmanager`` plugged into
  :class:`mcp.server.fastmcp.FastMCP(lifespan=...)`. Startup runs the two
  checks above and surfaces advisories on stderr; shutdown is a no-op for
  v1 since FastMCP itself owns transport teardown and the per-case
  :class:`~silentwitness_mcp.audit.logger.AuditLogger` flushes on its own
  ``__exit__``.

The :class:`AppContext` dataclass is what tools see via
``ctx.request_context.lifespan_context`` — the typed handle the
``record_observation`` / ``register_evidence`` stories in this epic will
read state from.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final

from silentwitness_mcp._case_env import read_case_env
from silentwitness_mcp.audit.logger import AuditLogger
from silentwitness_mcp.evidence.registry import EvidenceRegistry
from silentwitness_mcp.verification._injection_loader import get_patterns

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

REQUIRED_MOUNT_OPTS: Final[frozenset[str]] = frozenset({"ro", "noexec", "nosuid"})
DEFAULT_EVIDENCE_ROOT: Final = Path("/evidence")


@dataclass(slots=True)
class MountCheckResult:
    """Outcome of :func:`check_mount`. ``ok=True`` is the only state in
    which evidence-bound tools are allowed to operate. ``advisories``
    carries human-readable diagnostics the agent will surface in its
    ``ToolResponse`` envelope when ``ok`` is False."""

    ok: bool
    advisories: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AppContext:
    """Lifespan-shared context passed to every tool via
    ``ctx.request_context.lifespan_context``.

    The first three fields are always populated. The case-binding fields
    (``case_dir`` / ``evidence_registry`` / ``audit_logger`` / ``model_used``)
    are populated only when the server is spawned with a case env (see
    :mod:`silentwitness_mcp._case_env`); they stay ``None`` for bare boots and
    test harnesses, in which case evidence-bound tools refuse with a typed
    misconfiguration error rather than dereferencing ``None``."""

    mount: MountCheckResult
    evidence_root: Path
    injection_pattern_count: int
    case_dir: Path | None = None
    evidence_registry: EvidenceRegistry | None = None
    audit_logger: AuditLogger | None = None
    model_used: str | None = None


def check_mount(target: Path = DEFAULT_EVIDENCE_ROOT) -> MountCheckResult:
    """Verify ``target`` is mounted with ``ro,noexec,nosuid`` per
    architecture §4.11.

    Returns ``MountCheckResult(ok=True, advisories=[...note...])`` and
    skips the actual check when:

    * ``target`` does not exist on disk (dev environment; no
      ``/evidence`` mount yet)
    * ``findmnt`` is not on PATH (macOS / non-Linux dev / tests)

    These soft-skips let the FastMCP server boot in test environments
    without simulating the production mount. The production CI image
    has ``findmnt`` and the mount, so the hard check fires there.
    """
    if not target.exists():
        return MountCheckResult(
            ok=True,
            advisories=[
                f"evidence mount {target} does not exist (dev/test environment; "
                f"hard mount check skipped)"
            ],
        )
    findmnt = shutil.which("findmnt")
    if findmnt is None:
        # Fail-closed: production-shaped path exists but we can't
        # validate it (stripped util-linux, container init manipulated
        # PATH, botched ansible run). A SIFT image hardening step that
        # silently dropped findmnt would otherwise leave the mount
        # validator a no-op even on a writable, exec-allowed /evidence.
        return MountCheckResult(
            ok=False,
            advisories=[
                f"findmnt absent on PATH but {target} exists; "
                f"cannot verify ro,noexec,nosuid — refusing to proceed"
            ],
        )
    try:
        result = subprocess.run(  # noqa: S603  # validated args, fixed binary
            [findmnt, "-n", "-o", "OPTIONS", "--target", str(target)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return MountCheckResult(
            ok=False,
            advisories=[f"findmnt execution failed: {exc}"],
        )
    if result.returncode != 0:
        return MountCheckResult(
            ok=False,
            advisories=[
                f"findmnt returncode={result.returncode}: {result.stderr.strip() or '(no stderr)'}"
            ],
        )
    opts: set[str] = set(result.stdout.strip().split(","))
    missing = REQUIRED_MOUNT_OPTS - opts
    if missing:
        return MountCheckResult(
            ok=False,
            advisories=[f"evidence mount {target} missing required options: {sorted(missing)}"],
        )
    return MountCheckResult(ok=True)


def warm_injection_patterns() -> int:
    """Load the injection-patterns YAML at startup so the first sanitizer
    call doesn't pay the cost. Returns pattern count for visibility."""
    return len(get_patterns())


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """FastMCP lifespan context — runs startup checks once at server
    boot and surfaces an :class:`AppContext` to every tool.

    Architecture §4.1 — the lifespan is the single boot/teardown seam.
    Per Pydantic-AI MCP SDK 1.105 + the FastMCP construction pattern,
    this is the right hook (NOT the deprecated ``@app.on_event``).
    """
    mount = check_mount()
    if mount.ok:
        logger.info("evidence mount check: OK")
    else:
        # Stderr-visible per architecture §4.11 — MCP host sees the line.
        for note in mount.advisories:
            logger.error("evidence mount check failed: %s", note)
    for note in mount.advisories:
        if mount.ok:
            logger.info("mount: %s", note)
    pattern_count = warm_injection_patterns()
    logger.info("injection-pattern catalog loaded: %d patterns", pattern_count)

    # Case binding: when spawned by the investigator the server receives the
    # case via env (see _case_env). Construct exactly one registry + one logger
    # here — the run serves one case for the server's whole lifetime. Absent env
    # (tests / bare boot) leaves these None and evidence-bound tools refuse.
    case = read_case_env()
    case_dir: Path | None = None
    evidence_registry: EvidenceRegistry | None = None
    audit_logger: AuditLogger | None = None
    model_used: str | None = None
    if case is not None:
        case_dir = case.case_dir
        evidence_registry = EvidenceRegistry(case.case_dir)
        audit_logger = AuditLogger(case.case_dir, case.examiner)
        model_used = case.model_used
        logger.info("case bound: %s (examiner=%s, model=%s)", case_dir, case.examiner, model_used)
    else:
        logger.info("no case env — server booting without case binding (test/bare mode)")

    ctx = AppContext(
        mount=mount,
        evidence_root=DEFAULT_EVIDENCE_ROOT,
        injection_pattern_count=pattern_count,
        case_dir=case_dir,
        evidence_registry=evidence_registry,
        audit_logger=audit_logger,
        model_used=model_used,
    )
    try:
        yield ctx
    finally:
        # Release the AuditLogger's per-case fcntl lock so a follow-up run on the
        # same case (e.g. --resume) can re-acquire it. The spaCy model cache is
        # process-global and CPython drops it on interpreter shutdown.
        if audit_logger is not None:
            audit_logger.close()
        logger.info("silentwitness server shutdown complete")
