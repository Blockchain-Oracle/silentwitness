"""Project-wide typed errors that need to be importable from leaf
modules without taking a dependency on :mod:`server` (which would
create a circular import for the modules :mod:`server` consumes)."""

from __future__ import annotations


class ServerConfigurationError(RuntimeError):
    """Raised when transport / host / port / auth / tool-stub
    configuration is rejected at startup. Fail-closed: HTTP without
    a gateway token, or a tool-stub registry called with a missing
    ``guard_mount`` callback, is an immediate refusal — not a
    downgraded warning. :mod:`__main__` maps this to exit code
    ``_EX_CONFIG = 78`` so operators' supervisors can branch on it."""


__all__ = ["ServerConfigurationError"]
