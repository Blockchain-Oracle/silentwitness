"""Regression checks for install.sh runtime wiring."""

from __future__ import annotations

from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_INSTALL_SH = _REPO / "install.sh"


def test_spacy_model_installs_into_silentwitness_tool_env() -> None:
    text = _INSTALL_SH.read_text()
    start = text.index("install_spacy_model()")
    end = text.index(
        "# ---------------------------------------------------------------------------", start + 1
    )
    block = text[start:end]

    assert "$HOME/.local/share/uv/tools/silentwitness/bin/python" in block
    assert "uv run python -m spacy download en_core_web_lg" not in block
    assert 'uv pip install --python "$tool_python" "$model_wheel"' in block
    assert "en_core_web_lg-3.8.0-py3-none-any.whl" in block


def test_global_cli_installs_after_native_forensic_deps() -> None:
    text = _INSTALL_SH.read_text()

    assert text.index("\ninstall_evidence_access\n") < text.index("\ninstall_silentwitness_cli\n")
    assert text.index("\ninstall_silentwitness_cli\n") < text.index("\ninstall_spacy_model\n")


def test_install_verifies_forensic_tool_environment_after_model_install() -> None:
    text = _INSTALL_SH.read_text()
    start = text.index("verify_tool_environment()")
    end = text.index(
        "# ---------------------------------------------------------------------------", start + 1
    )
    block = text[start:end]

    assert '"Evtx", "regipy", "pyscca", "dfvfs", "plaso", "spacy"' in block
    assert '"silentwitness", "log2timeline", "psort"' in block
    assert text.index("\ninstall_spacy_model\n") < text.index("\nverify_tool_environment\n")
