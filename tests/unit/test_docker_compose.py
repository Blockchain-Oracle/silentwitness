"""Behavioural tests for docker-compose.yml — story-docker-baseline.

YAML-parsing assertions only; the actual ``docker build`` / ``docker run``
checks live in the story's Shell verification block (they need a Docker
daemon, which the unit suite doesn't assume). Each test maps to a BDD
criterion in story-docker-baseline.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMPOSE_PATH = _REPO_ROOT / "docker-compose.yml"


def _compose() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(_COMPOSE_PATH.read_text(encoding="utf-8")))


def _silentwitness_service() -> dict[str, Any]:
    return cast(dict[str, Any], _compose()["services"]["silentwitness"])


def test_compose_file_parses_as_yaml() -> None:
    """Compose file is valid YAML and declares a top-level `services` map."""
    payload = _compose()
    assert isinstance(payload, dict)
    assert "services" in payload, "compose file must declare a `services` block"


def test_silentwitness_service_is_declared() -> None:
    """Single service named `silentwitness` exists; build context is the repo root."""
    payload = _compose()
    assert "silentwitness" in payload["services"]
    svc = _silentwitness_service()
    build = svc.get("build")
    assert isinstance(build, dict), "build block must be a mapping (long-form)"
    assert build.get("context") == ".", f"build.context must be '.' (got {build.get('context')!r})"
    assert build.get("dockerfile") == "Dockerfile"


def test_evidence_mount_carries_security_flags() -> None:
    """`/evidence` is mounted with `ro,noexec,nosuid` per PRD §6 NFR."""
    svc = _silentwitness_service()
    volumes = svc.get("volumes", [])
    evidence_mounts = [v for v in volumes if isinstance(v, str) and v.startswith("/evidence:")]
    assert evidence_mounts, "no /evidence mount declared"
    flags = evidence_mounts[0].split(":")[-1]
    for required in ("ro", "noexec", "nosuid"):
        assert required in flags, f"/evidence mount missing {required}: {evidence_mounts[0]!r}"


def test_ledger_named_volume_is_mapped() -> None:
    """The HMAC ledger uses a named volume mapped to /var/lib/silentwitness."""
    payload = _compose()
    svc = payload["services"]["silentwitness"]
    volumes = svc.get("volumes", [])
    ledger = [
        v
        for v in volumes
        if isinstance(v, str) and "silentwitness-ledger" in v and "/var/lib/silentwitness" in v
    ]
    assert ledger, f"ledger named-volume mount not declared in volumes: {volumes!r}"
    # And the top-level volumes block declares the named volume.
    top_volumes = payload.get("volumes") or {}
    assert (
        "silentwitness-ledger" in top_volumes
    ), "top-level `volumes:` block must declare `silentwitness-ledger`"


def test_healthcheck_imports_silentwitness_mcp() -> None:
    """Healthcheck exercises the package import — the lightest possible liveness probe."""
    svc = _silentwitness_service()
    healthcheck = svc.get("healthcheck")
    assert isinstance(healthcheck, dict), "healthcheck must be declared"
    test_cmd = healthcheck.get("test")
    assert isinstance(test_cmd, list), f"healthcheck.test must be a list (got {type(test_cmd)})"
    joined = " ".join(str(t) for t in test_cmd)
    assert (
        "import silentwitness_mcp" in joined
    ), f"healthcheck command must import silentwitness_mcp: {joined!r}"


_DOCKERIGNORE_PATH = _REPO_ROOT / ".dockerignore"


def test_dockerignore_excludes_runtime_paths() -> None:
    """``.dockerignore`` must exclude every runtime-only path + caches + VCS.

    A regression dropping ``cases/`` here would leak evidence into the image
    build context — the highest-stakes silent regression in this PR.
    """
    patterns = {
        ln.strip()
        for ln in _DOCKERIGNORE_PATH.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    }
    required = {
        "cases/",
        "evidence/",
        "var/lib/silentwitness/",
        ".venv/",
        ".git/",
        "tests/",
        "docs/",
        ".pytest_cache/",
        "htmlcov/",
    }
    missing = required - patterns
    assert not missing, f".dockerignore missing required exclusions: {sorted(missing)}"


def test_compose_declares_security_opt_no_new_privileges() -> None:
    """Defence-in-depth: `security_opt: ["no-new-privileges:true"]` prevents setuid escalation."""
    svc = _silentwitness_service()
    security_opt = svc.get("security_opt", [])
    assert isinstance(security_opt, list), f"security_opt must be a list (got {type(security_opt)})"
    assert (
        "no-new-privileges:true" in security_opt
    ), f"security_opt must include no-new-privileges:true: {security_opt!r}"
