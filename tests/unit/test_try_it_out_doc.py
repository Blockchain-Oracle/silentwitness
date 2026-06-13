"""Tests for docs/TRY_IT_OUT.md + scripts/check_try_it_out.py (story-try-it-out-doc)."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_DOC = _REPO / "docs" / "TRY_IT_OUT.md"
_GATE = _REPO / "scripts" / "check_try_it_out.py"


def _run_gate(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_GATE), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


def test_committed_doc_passes_gate() -> None:
    r = _run_gate()
    assert r.returncode == 0, r.stderr


def test_doc_under_400_lines() -> None:
    assert len(_DOC.read_text().splitlines()) <= 400


def test_doc_has_h1() -> None:
    assert _DOC.read_text().startswith("# Try SilentWitness")


def test_sift_install_one_liner_present() -> None:
    text = _DOC.read_text()
    assert "curl --proto '=https' --tlsv1.2 -sSf" in text
    assert "install.sh | bash" in text


def test_docker_compose_path_present() -> None:
    text = _DOC.read_text()
    assert "docker compose up -d" in text
    assert "docker compose exec silentwitness" in text


def test_nitroba_smoke_case_id_present() -> None:
    assert "nitroba-smoke-001" in _DOC.read_text()


def test_four_provider_model_strings_present() -> None:
    text = _DOC.read_text()
    for prefix in ("anthropic:", "openai:", "google-gla:", "ollama:"):
        assert prefix in text, f"missing model provider {prefix!r}"


def test_troubleshooting_has_six_or_more_entries() -> None:
    text = _DOC.read_text()
    idx = text.index("## Troubleshooting")
    next_h2 = text.find("\n## ", idx + 1)
    section = text[idx : next_h2 if next_h2 > 0 else len(text)]
    qa = sum(1 for ln in section.splitlines() if ln.startswith('- "') or ln.startswith("- **"))
    assert qa >= 6, f"need >=6 Q&A entries, found {qa}"


def test_no_banned_vocab() -> None:
    text = _DOC.read_text().lower()
    for phrase in (
        "court-admissible",
        "autonomous soc",
        "ralph wiggum",
        "replaces l1",
        "eliminates hallucinations",
    ):
        assert phrase not in text, f"banned phrase {phrase!r} present"


def _ok_doc() -> str:
    return (
        "# Try SilentWitness\n\n## Before you start — prerequisites\n\n"
        "## Path A — SIFT 2026 native (3 commands)\n\n"
        "curl --proto '=https' --tlsv1.2 -sSf https://x/install.sh | bash\n\n"
        "## Path B — Docker Compose (2 commands)\n\n"
        "docker compose up -d\ndocker compose exec silentwitness investigate\n\n"
        "## Step-by-step\n\nsilentwitness investigate nitroba-smoke-001\n\n"
        "## Model selection\n\n"
        "anthropic:claude-opus\nopenai:gpt-5\ngoogle-gla:gemini-2.5\nollama:llama4\n\n"
        "## Troubleshooting\n\n"
        "- **q1**: a\n- **q2**: a\n- **q3**: a\n- **q4**: a\n- **q5**: a\n- **q6**: a\n\n"
        "## License\n"
    )


_MUTATIONS: list[tuple[Callable[[str], str], str]] = [
    (lambda t: t.replace("# Try SilentWitness", "# Wrong"), "h1"),
    (lambda t: t.replace("curl --proto", "REMOVED"), "sift_install"),
    (lambda t: t.replace("docker compose up -d", "REMOVED"), "docker_up"),
    (lambda t: t.replace("docker compose exec silentwitness", "REMOVED"), "docker_exec"),
    (lambda t: t.replace("nitroba-smoke-001", "REMOVED"), "nitroba_command"),
    (lambda t: t.replace("anthropic:", "REMOVED:"), "model_strings"),
    (lambda t: t.replace("- **q1**: a\n- **q2**: a\n", ""), "troubleshooting_entries"),
    (lambda t: t + "\ncourt-admissible content\n", "banned_vocab"),
    (lambda t: "\n".join(["pad"] * 401) + "\n" + t, "max_lines"),
]


def test_ok_doc_self_passes_gate(tmp_path: Path) -> None:
    """Synthetic happy-path stub must satisfy every rule (fires before mutations)."""
    good = tmp_path / "TRY_IT_OUT.md"
    good.write_text(_ok_doc())
    r = _run_gate("--doc", str(good))
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize(
    "mutation,rule",
    _MUTATIONS,
    ids=[m[1] for m in _MUTATIONS],
)
def test_gate_rule_fires_on_mutation(
    tmp_path: Path,
    mutation: Callable[[str], str],
    rule: str,
) -> None:
    bad = tmp_path / "TRY_IT_OUT.md"
    bad.write_text(mutation(_ok_doc()))
    r = _run_gate("--doc", str(bad))
    assert r.returncode == 1, r.stderr
    assert rule in r.stderr


def test_doc_missing_exits_1(tmp_path: Path) -> None:
    r = _run_gate("--doc", str(tmp_path / "DOES_NOT_EXIST.md"))
    assert r.returncode == 1
    assert "doc_exists" in r.stderr
