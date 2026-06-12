"""NIST CFReDS Hacking Case (Greg Schardt / Mr. Evil) ground-truth parser.

Parses two committed HTML writeup snapshots:
  harness/ground_truth/snapshots/intrinsicode-net-hacking-case.html
  harness/ground_truth/snapshots/zarat-hatenablog-com-hacking-case.html

Merges parsed findings with supplemental hand-crafted findings from
nist-hacking-case.supplemental.json for canonical answers not present
verbatim in the snapshots (e.g., wireless adapter MAC 00:02:B3:DD:00:A2).

No live HTTP at parse time — snapshots are committed for offline CI.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Literal

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from harness.ground_truth.schema import GroundTruthFinding  # noqa: E402

try:
    from bs4 import BeautifulSoup
except ImportError as exc:
    raise ImportError("beautifulsoup4 required: uv add beautifulsoup4") from exc

_SNAPSHOTS_DIR = Path(__file__).resolve().parent / "snapshots"
_INTRINSICODE = _SNAPSHOTS_DIR / "intrinsicode-net-hacking-case.html"
_ZARAT = _SNAPSHOTS_DIR / "zarat-hatenablog-com-hacking-case.html"
_SUPPLEMENTAL = Path(__file__).resolve().parent / "nist-hacking-case.supplemental.json"
_DATASET_ID: Literal["nist-hacking-case"] = "nist-hacking-case"

_INTRINSICODE_URL = "https://web.archive.org/web/20240101/https://intrinsicode.net/2021/05/19/cfreds-hacking-case-report/"
_ZARAT_URL = (
    "https://web.archive.org/web/20230101/https://zarat.hatenablog.com/entry/2021/12/19/223735"
)


def _parse_intrinsicode() -> list[GroundTruthFinding]:
    html = _INTRINSICODE.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    findings: list[GroundTruthFinding] = []

    # Extract the FINDINGS section lines (e.g. "Finding 1  System configuration...")
    finding_blocks = re.findall(r"Finding\s+(\d+)\s+(.+?)(?=Finding\s+\d+|\Z)", text, re.DOTALL)
    for num, body in finding_blocks:
        body = body.strip()
        if not body:
            continue
        summary = re.sub(r"\s+", " ", body)[:200]
        substrings = _substrings_from_text(body)
        findings.append(
            GroundTruthFinding(
                id=f"GT-NHC-IC-{int(num):03d}",
                dataset_id=_DATASET_ID,
                category=_infer_category(body),
                summary=summary,
                expected_artifact_substrings=substrings,
                expected_path_globs=[],
                supporting_question_id=None,
                source="community_writeup",
                source_url=_INTRINSICODE_URL,  # type: ignore[arg-type]
                source_excerpt=body[:500],
            )
        )

    # Also extract the hostname if present
    hostname_match = re.search(r"N-1A9ODN6ZXK4LQ", text)
    already_present = any("N-1A9ODN6ZXK4LQ" in f.expected_artifact_substrings for f in findings)
    if hostname_match and not already_present:
        excerpt = text[max(0, hostname_match.start() - 80) : hostname_match.start() + 160]
        findings.append(
            GroundTruthFinding(
                id="GT-NHC-IC-HOST",
                dataset_id=_DATASET_ID,
                category="network_indicator",
                summary="Laptop hostname: N-1A9ODN6ZXK4LQ (from LANHOST/LANDOMAIN reference)",
                expected_artifact_substrings=["N-1A9ODN6ZXK4LQ"],
                expected_path_globs=[],
                supporting_question_id=None,
                source="community_writeup",
                source_url=_INTRINSICODE_URL,  # type: ignore[arg-type]
                source_excerpt=excerpt[:500],
            )
        )

    return findings


def _parse_zarat() -> list[GroundTruthFinding]:
    html = _ZARAT.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    findings: list[GroundTruthFinding] = []

    # Zarat writeup has numbered Q&A: "N. <question> ... Answer: <answer>"
    qa_blocks = re.findall(r"(\d+)\.\s+(.+?)(?=\d+\.\s+[A-Z一-鿿]|\Z)", text, re.DOTALL)
    for num, body in qa_blocks[:35]:  # cap at 35 questions
        body = re.sub(r"\s+", " ", body).strip()
        if not body or len(body) < 10:
            continue
        answer_match = re.search(r"Answer[s]?\s*[:：]\s*(.+)", body, re.IGNORECASE)  # noqa: RUF001
        answer_text = answer_match.group(1)[:400] if answer_match else body[:400]
        summary = body[:200]
        substrings = _substrings_from_text(answer_text)
        findings.append(
            GroundTruthFinding(
                id=f"GT-NHC-ZA-{int(num):03d}",
                dataset_id=_DATASET_ID,
                category=_infer_category(body),
                summary=summary,
                expected_artifact_substrings=substrings,
                expected_path_globs=[],
                supporting_question_id=str(num),
                source="community_writeup",
                source_url=_ZARAT_URL,  # type: ignore[arg-type]
                source_excerpt=body[:500],
            )
        )

    return findings


def _load_supplemental() -> list[GroundTruthFinding]:
    raw = json.loads(_SUPPLEMENTAL.read_text(encoding="utf-8"))
    return [GroundTruthFinding.model_validate(item) for item in raw]


def _substrings_from_text(text: str) -> list[str]:
    substrings: list[str] = []
    substrings += re.findall(r"[A-Z]:\\[\\A-Za-z0-9 ._\-()%]+", text)
    substrings += re.findall(r"\b[0-9a-f]{32}\b", text, re.IGNORECASE)
    substrings += re.findall(r"[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}", text)
    substrings += re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    substrings += re.findall(r"\w[\w. -]{0,30}\.exe", text)
    substrings += re.findall(r"\w[\w. -]{0,30}\.ini", text)
    # Deduplicate
    seen: set[str] = set()
    result: list[str] = []
    for s in substrings:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result or [text[:80].strip()]


_Category = Literal[
    "user_profile",
    "installed_tool",
    "credential",
    "network_indicator",
    "timestamp",
    "file_artifact",
    "persistence",
    "exfiltration",
    "communication",
    "other",
]


def _infer_category(text: str) -> _Category:
    lower = text.lower()
    if any(w in lower for w in ["mac address", "ip address", "hostname", "network", "wireless"]):
        return "network_indicator"
    if any(w in lower for w in ["email", "smtp", "password", "credential"]):
        return "credential"
    if any(w in lower for w in ["installed", "software", "ethereal", "anonymizer", "cain", "tool"]):
        return "installed_tool"
    if any(w in lower for w in ["owner", "user", "schardt", "mr. evil", "alias", "account"]):
        return "user_profile"
    if any(w in lower for w in ["hash", "md5", "sha"]):
        return "other"
    if any(w in lower for w in ["file", "folder", "path", "directory"]):
        return "file_artifact"
    if any(w in lower for w in ["time", "date", "timestamp"]):
        return "timestamp"
    return "other"


def _dedup(findings: list[GroundTruthFinding]) -> list[GroundTruthFinding]:
    """Drop supplemental findings whose id already appears (parsed takes precedence)."""
    seen_ids: set[str] = set()
    result: list[GroundTruthFinding] = []
    for f in findings:
        if f.id not in seen_ids:
            seen_ids.add(f.id)
            result.append(f)
    return result


def parse() -> list[GroundTruthFinding]:
    """Return ≥15 GroundTruthFinding objects for the NIST Hacking Case."""
    supplemental = _load_supplemental()
    intrinsicode = _parse_intrinsicode()
    zarat = _parse_zarat()
    # Supplemental first so their canonical IDs aren't shadowed
    return _dedup(supplemental + intrinsicode + zarat)
