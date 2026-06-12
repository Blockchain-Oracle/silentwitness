"""Pinned third-party catalog for scripts/build_notices.py (split for LOC budget)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    name: str
    version: str
    spdx: str
    url: str
    copyright: str


# SPDX IDs we accept. Non-obvious entries explained inline:
# - `OSL-3.0` historically used here (we now use the SPDX LicenseRef form below).
# - `CC-BY-SA-4.0` covers some spaCy non-English model data licenses — kept for
#   forward compat even though en_core_web_lg itself is MIT.
# - `AGPL-3.0-only` (Velociraptor) — subprocess invocation, no network conveyance.
# - `LicenseRef-Volatility-VSL-1.0` (Volatility 3) — VSL is BSD-style but has no
#   SPDX ID; use the SPDX LicenseRef-* form to express it precisely.
SUPPORTED_SPDX = frozenset(
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
        "LicenseRef-Volatility-VSL-1.0",
    }
)


# To add a component: append a Component(...) to CATALOG; SPDX must appear above.
# Ordering at emit time is alphabetic by name; declaration order is free.
# Versions reflect docs/architecture.md §2 + install.sh pins. Binary-tool versions
# marked "x" (e.g. "3.x") are install.sh-anticipated until install.sh ships exact pins.
CATALOG: tuple[Component, ...] = (
    Component(
        "Chainsaw",
        "2.10.x",
        "GPL-3.0-only",
        "https://github.com/WithSecureLabs/chainsaw",
        "Copyright (c) WithSecure Labs",
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
        "LicenseRef-Volatility-VSL-1.0",
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
        "MIT",
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
