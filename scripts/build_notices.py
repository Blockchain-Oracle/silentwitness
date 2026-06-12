#!/usr/bin/env python3
"""Build NOTICES.md — aggregated third-party license attribution (story-third-party-notices).

Walks a pinned catalog of components (Python deps + install.sh binaries + datasets),
renders each as a Markdown section with name | version | SPDX | URL | copyright,
and emits verbatim license-grant snippets for GPL/AGPL components.

Exit 0 on success; 1 on `UNKNOWN_LICENSE:<name>`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_SUPPORTED_SPDX = frozenset(
    {
        "MIT",
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "GPL-2.0-only",
        "GPL-3.0-only",
        "AGPL-3.0-only",
        "MPL-2.0",
        "ISC",
        "OSL-3.0",
        "CC-BY-SA-4.0",
    }
)

_GPL3_GRANT = (
    "This program is free software: you can redistribute it and/or modify "
    "it under the terms of the GNU General Public License as published by "
    "the Free Software Foundation, either version 3 of the License, or "
    "(at your option) any later version. See <https://www.gnu.org/licenses/gpl-3.0.html>."
)
_GPL2_GRANT = (
    "This program is free software; you can redistribute it and/or modify "
    "it under the terms of the GNU General Public License as published by "
    "the Free Software Foundation; either version 2 of the License, or "
    "(at your option) any later version. See <https://www.gnu.org/licenses/gpl-2.0.html>."
)
_AGPL3_GRANT = (
    "This program is free software: you can redistribute it and/or modify "
    "it under the terms of the GNU Affero General Public License as published by "
    "the Free Software Foundation, either version 3 of the License, or "
    "(at your option) any later version. See <https://www.gnu.org/licenses/agpl-3.0.html>."
)


@dataclass(frozen=True)
class Component:
    name: str
    version: str
    spdx: str
    url: str
    copyright: str


# Pinned catalog — alphabetically sorted at emit time, not declaration time.
# Versions reflect docs/architecture.md §2 + install.sh pins.
_CATALOG: tuple[Component, ...] = (
    Component(
        "Chainsaw",
        "2.10.x",
        "GPL-3.0-only",
        "https://github.com/WithSecureLabs/chainsaw",
        "Copyright (c) WithSecure Labs",
    ),
    Component(
        "FastMCP",
        "via mcp>=1.23",
        "MIT",
        "https://github.com/modelcontextprotocol/python-sdk",
        "Copyright (c) Anthropic, PBC",
    ),
    Component(
        "Hayabusa",
        "3.x",
        "GPL-3.0-only",
        "https://github.com/Yamato-Security/hayabusa",
        "Copyright (c) Yamato Security",
    ),
    Component(
        "Jinja2",
        "via weasyprint",
        "BSD-3-Clause",
        "https://github.com/pallets/jinja",
        "Copyright (c) Pallets Project",
    ),
    Component(
        "MCP",
        ">=1.23.0,<2.0",
        "MIT",
        "https://github.com/modelcontextprotocol/python-sdk",
        "Copyright (c) Anthropic, PBC",
    ),
    Component(
        "MFTECmd",
        "EZ Tools (latest)",
        "MIT",
        "https://github.com/EricZimmerman/MFTECmd",
        "Copyright (c) Eric Zimmerman",
    ),
    Component(
        "Mistune",
        ">=3.2.1",
        "BSD-3-Clause",
        "https://github.com/lepture/mistune",
        "Copyright (c) Hsiaoming Yang",
    ),
    Component(
        "Pydantic",
        ">=2.9",
        "MIT",
        "https://github.com/pydantic/pydantic",
        "Copyright (c) Pydantic Services Inc.",
    ),
    Component(
        "Pydantic AI",
        ">=1.105.0,<2.0.0",
        "MIT",
        "https://github.com/pydantic/pydantic-ai",
        "Copyright (c) Pydantic Services Inc.",
    ),
    Component(
        "Rich",
        ">=14.1,<16",
        "MIT",
        "https://github.com/Textualize/rich",
        "Copyright (c) Will McGugan / Textualize",
    ),
    Component(
        "Suricata",
        "7.x",
        "GPL-2.0-only",
        "https://github.com/OISF/suricata",
        "Copyright (c) Open Information Security Foundation",
    ),
    Component(
        "Typer",
        ">=0.15",
        "MIT",
        "https://github.com/tiangolo/typer",
        "Copyright (c) Sebastián Ramírez",
    ),
    Component(
        "Velociraptor",
        "0.7.x",
        "AGPL-3.0-only",
        "https://github.com/Velocidex/velociraptor",
        "Copyright (c) Velocidex Enterprises",
    ),
    Component(
        "Volatility 3",
        "2.27.0",
        "OSL-3.0",
        "https://github.com/volatilityfoundation/volatility3",
        "Copyright (c) Volatility Foundation",
    ),
    Component(
        "WeasyPrint",
        ">=68.1,<70.0",
        "BSD-3-Clause",
        "https://github.com/Kozea/WeasyPrint",
        "Copyright (c) Kozea / Simon Sapin and contributors",
    ),
    Component(
        "Zeek",
        "6.x",
        "BSD-3-Clause",
        "https://github.com/zeek/zeek",
        "Copyright (c) The Zeek Project",
    ),
    Component(
        "en_core_web_lg",
        "spaCy model 3.8",
        "CC-BY-SA-4.0",
        "https://spacy.io/models/en#en_core_web_lg",
        "Copyright (c) Explosion AI",
    ),
    Component(
        "httpx",
        ">=0.27",
        "BSD-3-Clause",
        "https://github.com/encode/httpx",
        "Copyright (c) Encode OSS Ltd.",
    ),
    Component(
        "matplotlib",
        ">=3.10,<3.11",
        "BSD-3-Clause",
        "https://github.com/matplotlib/matplotlib",
        "Copyright (c) Matplotlib Development Team",
    ),
    Component(
        "spaCy",
        ">=3.8.10,<3.9",
        "MIT",
        "https://github.com/explosion/spaCy",
        "Copyright (c) ExplosionAI GmbH",
    ),
    Component(
        "uv",
        "0.11.18",
        "Apache-2.0",
        "https://github.com/astral-sh/uv",
        "Copyright (c) Astral Software Inc.",
    ),
)


def _grant_for(spdx: str) -> str | None:
    return {
        "GPL-3.0-only": _GPL3_GRANT,
        "GPL-2.0-only": _GPL2_GRANT,
        "AGPL-3.0-only": _AGPL3_GRANT,
    }.get(spdx)


def _render_component(c: Component) -> str:
    lines = [
        f"## {c.name}",
        "",
        f"- Version: {c.version}",
        f"- SPDX: {c.spdx}",
        f"- Source: <{c.url}>",
        f"- Copyright: {c.copyright}",
    ]
    grant = _grant_for(c.spdx)
    if grant:
        lines += ["", f"License-grant ({c.spdx}):", "", f"> {grant}"]
    return "\n".join(lines) + "\n"


def _render(components: tuple[Component, ...]) -> str:
    head = [
        "# NOTICES",
        "",
        "SilentWitness is licensed under MIT (see [LICENSE](./LICENSE)).",
        "",
        "This NOTICES file aggregates third-party attributions per their respective licenses.",
        "Generated by `scripts/build_notices.py`; do not edit by hand.",
        "",
        "## About this file",
        "",
        "Each entry below names a third-party component bundled, installed, or "
        "subprocess-invoked by SilentWitness, with its version pin, SPDX license "
        "identifier, canonical source URL, and copyright holder.",
        "",
    ]
    sorted_components = sorted(components, key=lambda c: c.name.lower())
    body = [_render_component(c) for c in sorted_components]
    return "\n".join(head) + "\n".join(body)


def build(catalog: tuple[Component, ...]) -> str:
    """Validate SPDX + render NOTICES.md text. Raises ValueError on UNKNOWN_LICENSE."""
    for c in catalog:
        if c.spdx not in _SUPPORTED_SPDX:
            raise ValueError(f"UNKNOWN_LICENSE: {c.name} ({c.spdx!r})")
    return _render(catalog)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build NOTICES.md.")
    parser.add_argument("--out", type=Path, default=Path("NOTICES.md"))
    parser.add_argument(
        "--inject-unknown",
        default=None,
        help="Inject a component with an unknown SPDX id (testing exit-1 path).",
    )
    args = parser.parse_args(argv)

    catalog = _CATALOG
    if args.inject_unknown:
        catalog = (
            *catalog,
            Component(
                args.inject_unknown,
                "0.0",
                "Mystery-License-9000",
                "https://example.invalid",
                "Copyright (c) ?",
            ),
        )
    try:
        text = build(catalog)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
