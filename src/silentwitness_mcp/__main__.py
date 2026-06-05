"""Module entrypoint — ``python -m silentwitness_mcp`` launches the server.

Two transports per architecture §7.3:

* ``stdio`` (default) — the SIFT 2026 Claude Code v2.0.61 subprocess
  pattern. No CLI flags needed.
* ``http`` — Streamable HTTP on ``127.0.0.1:<port>``; requires the
  ``$SILENTWITNESS_GATEWAY_TOKEN`` env var. Port defaults to 4508.

Any banner / startup logging goes to stderr (handled inside
:func:`silentwitness_mcp.server.run_server`) so JSON-RPC framing on
stdout stays clean.
"""

from __future__ import annotations

import argparse
import sys
from typing import Final

from silentwitness_mcp import __version__
from silentwitness_mcp.server import (
    DEFAULT_HTTP_HOST,
    DEFAULT_HTTP_PORT,
    ServerConfigurationError,
    Transport,
    run_server,
)

# BSD sysexits.h codes — operators and supervisors can branch on these
# without parsing the stderr message. `man sysexits.h`.
_EX_IOERR: Final = 74
_EX_CONFIG: Final = 78


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="silentwitness_mcp",
        description=f"SilentWitness MCP server v{__version__}",
    )
    parser.add_argument(
        "--transport",
        type=Transport,
        choices=list(Transport),
        default=Transport.STDIO,
        help="MCP transport (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HTTP_HOST,
        help=(
            f"HTTP bind host (default: {DEFAULT_HTTP_HOST}; loopback-only "
            f"per DNS-rebinding defense)"
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_HTTP_PORT,
        help=f"HTTP bind port (default: {DEFAULT_HTTP_PORT})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"silentwitness_mcp {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        run_server(args.transport, host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("silentwitness: interrupted", file=sys.stderr)
        return 130
    except ServerConfigurationError as exc:
        # Misconfig at startup (missing token, non-loopback host,
        # out-of-range port). Structured exit lets supervisors branch
        # without scraping stderr.
        print(f"silentwitness: configuration error: {exc}", file=sys.stderr)
        return _EX_CONFIG
    except OSError as exc:
        # Port-bind collision, EACCES on bind, etc. Otherwise these would
        # dump a 30-line Python traceback into the JSON-RPC framing seam.
        print(f"silentwitness: bind/IO error: {exc}", file=sys.stderr)
        return _EX_IOERR
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
