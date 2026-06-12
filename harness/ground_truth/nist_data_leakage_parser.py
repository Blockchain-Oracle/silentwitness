"""NIST CFReDS Data Leakage answer-key PDF parser.

Downloads leakage-answers.pdf on first run (cached at
~/.cache/silentwitness/ground_truth/), verifies SHA256 against the committed
pin, then extracts each numbered question-answer pair as a GroundTruthFinding.

Strategy: pypdf.PdfReader extracts text page-by-page; section 6 (Q&A) starts
around page 16. A simple numbered-question regex captures each Q&A block.

Exit codes (CLI): 0 = success, 1 = SHA256 mismatch, 2 = fetch or parse failure.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Literal

# Allow direct execution without installing the harness package.
_REPO_ROOT = str(Path(__file__).resolve().parents[2])
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from harness.ground_truth.schema import GroundTruthFinding, SHA256MismatchError  # noqa: E402

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

import pypdf  # noqa: E402

_CACHE_DIR = Path.home() / ".cache" / "silentwitness" / "ground_truth"
_PDF_PATH = _CACHE_DIR / "leakage-answers.pdf"
_PDF_URL = "https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf"
_SHA256_FILE = Path(__file__).resolve().parent / "nist-data-leakage.answer-key-sha256.txt"

ANSWER_KEY_SHA256 = (
    "218165427fcb2f490b44eccf7fbc9bf3700b938ea976004051a067e79e0da62b"  # pragma: allowlist secret
)

_DATASET_ID: Literal["nist-data-leakage"] = "nist-data-leakage"
_SOURCE_URL = "https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf"

# Sections before Q&A (covers pages 1-15, approximately)
_QA_START_MARKER = "6. QUESTIONS AND ANSWERS"
_CHUNK = 8192


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK):
            h.update(chunk)
    return h.hexdigest()


def _fetch_pdf() -> None:
    """Download leakage-answers.pdf to cache if absent or hash-mismatched."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if _PDF_PATH.exists() and _sha256_path(_PDF_PATH) == ANSWER_KEY_SHA256:
        return
    if httpx is None:
        raise RuntimeError(
            "httpx is required to fetch the answer key; install it or pre-cache the PDF"
        )
    response = httpx.get(_PDF_URL, follow_redirects=True, timeout=60.0)
    response.raise_for_status()
    _PDF_PATH.write_bytes(response.content)


def _verify_pdf() -> None:
    actual = _sha256_path(_PDF_PATH)
    if actual != ANSWER_KEY_SHA256:
        raise SHA256MismatchError(
            f"leakage-answers.pdf SHA256 mismatch: got {actual!r}, "
            f"expected {ANSWER_KEY_SHA256!r}. "
            f"Re-fetch or update answer-key-sha256.txt to resolve."
        )


def _extract_qa_text() -> str:
    reader = pypdf.PdfReader(str(_PDF_PATH))
    pages_text: list[str] = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages_text)
    # The TOC also contains the section header; use the LAST occurrence (actual section body).
    last_idx = full_text.rfind(_QA_START_MARKER)
    if last_idx < 0:
        return full_text  # fallback: parse whole document
    return full_text[last_idx:]


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


def _infer_category(question: str, answer: str) -> _Category:
    text = (question + " " + answer).lower()
    if any(w in text for w in ["hash", "md5", "sha", "acquisition"]):
        return "other"
    if any(w in text for w in ["username", "user name", "owner", "account", "logged", "logon"]):
        return "user_profile"
    if any(w in text for w in ["installed", "software", "application", "program", "tool"]):
        return "installed_tool"
    if any(w in text for w in ["password", "credential", "email address", "smtp"]):
        return "credential"
    if any(w in text for w in ["ip address", "mac address", "network", "tcp", "dns"]):
        return "network_indicator"
    if any(w in text for w in ["timestamp", "time", "date", "timezone"]):
        return "timestamp"
    if any(w in text for w in ["file", "folder", "path", "directory", "usb", "thumb", "removable"]):
        return "file_artifact"
    if any(w in text for w in ["copy", "exfil", "transfer", "leak", "upload", "download"]):
        return "exfiltration"
    return "other"


def _extract_substrings(answer: str) -> list[str]:
    """Extract verbatim artifact-level substrings from an answer block."""
    substrings: list[str] = []
    # Registry hive paths
    substrings += re.findall(r"HKLM\\[A-Z\\a-z0-9_#]+", answer)
    # File paths (Windows-style)
    substrings += re.findall(r"[A-Z]:\\[\\A-Za-z0-9 ._\-()%]+", answer)
    # Hash values (MD5 = 32 hex, SHA1 = 40 hex)
    substrings += re.findall(r"\b[0-9A-Fa-f]{32}\b", answer)
    substrings += re.findall(r"\b[0-9A-Fa-f]{40}\b", answer)
    # "Possible Answer" lines — extract the first token after "Possible Answer"
    for line in answer.splitlines():
        line = line.strip()
        if line.startswith("Possible Answer"):
            rest = line[len("Possible Answer") :].strip()
            if rest and len(rest) <= 100:
                substrings.append(rest)
    # Fallback: use the first non-empty, non-header line of the answer block
    if not substrings:
        for line in answer.splitlines():
            line = line.strip()
            if (
                line
                and not line.startswith("Possible")
                and not line.startswith("Consider")
                and len(line) <= 100
            ):
                substrings.append(line)
                break
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for s in substrings:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result or [answer[:100].strip()]


def parse() -> list[GroundTruthFinding]:
    """Parse leakage-answers.pdf and return ≥20 GroundTruthFinding objects."""
    _fetch_pdf()
    _verify_pdf()

    qa_text = _extract_qa_text()

    # Match numbered questions: "N) Question text\n...answer block..."
    pattern = re.compile(r"(\d+)\)\s+(.+?)(?=\n\d+\)\s|\Z)", re.DOTALL)
    matches = pattern.findall(qa_text)

    findings: list[GroundTruthFinding] = []
    for num, body in matches:
        lines = [ln.strip() for ln in body.strip().splitlines() if ln.strip()]
        if not lines:
            continue
        question = lines[0]
        answer_block = "\n".join(lines[1:]) if len(lines) > 1 else question

        substrings = _extract_substrings(answer_block)
        category = _infer_category(question, answer_block)
        excerpt = (question + " " + answer_block)[:500].strip()

        findings.append(
            GroundTruthFinding(
                id=f"GT-NDL-{int(num):03d}",
                dataset_id=_DATASET_ID,
                category=category,
                summary=question[:200],
                expected_artifact_substrings=substrings,
                expected_path_globs=[],
                supporting_question_id=str(num),
                source="nist_pdf",
                source_url=_SOURCE_URL,  # type: ignore[arg-type]
                source_excerpt=excerpt,
            )
        )

    return findings
