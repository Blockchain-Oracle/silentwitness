"""Package version — single source of truth for __version__ at runtime.

python-semantic-release bumps pyproject.toml:project.version on merge to main;
importlib.metadata reflects that value at runtime without a separate assignment.
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__: str = _pkg_version("silentwitness")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]
