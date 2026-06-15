"""Enforced investigative-coverage gate over the 5 Key Questions.

A data-theft investigation must answer five questions: which accounts/projects were
accessed, what was taken, where it was moved, how the actor got in, and when. A capable
model left to itself converges on the loudest signal (on ROCBA: 540k brute-force
detections) and concludes after one hypothesis — the other questions go unanswered even
though the evidence is indexed. This module makes breadth *structural*: a deterministic
tracker maps recorded observations to questions, and the investigator's output validator
refuses to finalize while any question has zero support (raising ``ModelRetry`` that names
the gap + the artifact types that bear on it).

The question signals are GENERIC DFIR concepts (any cloud provider, any remote-access
method, any document type) — not tied to a specific case's filenames — so the gate
generalises across Windows data-theft cases, not just the one image it was tuned on.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# An ISO-ish date anywhere in an observation satisfies the "when" question.
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


@dataclass(frozen=True)
class KeyQuestion:
    """One investigative question + the generic signals that indicate it was addressed."""

    qid: str
    label: str
    keywords: tuple[str, ...]
    artifact_hint: str  # named artifact types to query when this question is unanswered


# Generic data-theft investigative dimensions (case-agnostic signals).
KEY_QUESTIONS: tuple[KeyQuestion, ...] = (
    KeyQuestion(
        "Q1",
        "which accounts / projects were accessed",
        (
            "logon",
            "account",
            "username",
            "mailbox",
            "profile",
            "4624",
            "4672",
            "sign-in",
            "session",
            "userassist",
            "user ",
        ),
        "Security 4624/4672 logons, registry UserAssist/NTUSER, mailbox identity",
    ),
    KeyQuestion(
        "Q2",
        "what data was taken",
        (
            "document",
            "project",
            "research",
            "source code",
            "recent",
            "opened",
            ".docx",
            ".xlsx",
            ".pdf",
            ".zip",
            ".doc",
            ".pptx",
            "jumplist",
            "shortcut",
        ),
        "LNK / jumplist (Recent files), $MFT, shellbags — the files the user opened",
    ),
    KeyQuestion(
        "Q3",
        "where the data was transferred",
        (
            "onedrive",
            "dropbox",
            "google drive",
            "gdrive",
            "box.com",
            "sharepoint",
            "outlook",
            "office365",
            "o365",
            "email",
            "rclone",
            "mega",
            "ftp",
            "upload",
            "bytes_sent",
            "cloud",
            "sync",
            "webdav",
        ),
        "LNK/jumplist cloud paths, SRUM network_usage, PowerShell transcripts (upload cmds)",
    ),
    KeyQuestion(
        "Q4",
        "how the actor obtained access",
        (
            "rdp",
            "remote desktop",
            "mstsc",
            "vpn",
            "ssh",
            "winrm",
            "psexec",
            "powershell",
            "3389",
            "logontype",
            "remote interactive",
            "default.rdp",
            "lateral",
            "brute",
            "4625",
            "credential",
        ),
        "Security 4624 LogonType 10 (RDP) / 4625, Default.rdp, Sigma detections",
    ),
    KeyQuestion(
        "Q5",
        "when the activity occurred",
        (
            "timeline",
            "timestamp",
            "intrusion window",
            "first observed",
            "last observed",
            "occurred at",
            "between ",
        ),
        "timeline() over the index; event/prefetch/MFT timestamps",
    ),
)


@dataclass(frozen=True)
class CoverageReport:
    """Per-question coverage; ``uncovered`` drives the finalization gate."""

    covered: frozenset[str]
    uncovered: tuple[KeyQuestion, ...]

    @property
    def is_complete(self) -> bool:
        return not self.uncovered


def _observation_blobs(case_dir: Path) -> list[str]:
    """Lowercased text of every recorded observation (justifications + cited span text).

    Reads ``findings.json`` defensively — a missing/!malformed file yields no blobs (the
    gate then treats every question as unanswered, which is the safe default early in a
    run)."""
    path = case_dir / "findings.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    blobs: list[str] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        parts: list[str] = [str(item.get("title", ""))]
        spans = item.get("cited_spans") or item.get("cited_span") or []
        parts += [str(s.get("span_text", "")) for s in spans if isinstance(s, dict)]
        interps = item.get("interpretations") or []
        parts += [str(i.get("justification", "")) for i in interps if isinstance(i, dict)]
        blob = " ".join(parts).strip()
        if blob:
            blobs.append(blob.lower())
    return blobs


def _question_covered(question: KeyQuestion, blobs: list[str]) -> bool:
    for blob in blobs:
        if any(kw in blob for kw in question.keywords):
            return True
        if question.qid == "Q5" and _DATE_RE.search(blob):
            return True
    return False


def analyze_coverage(case_dir: Path) -> CoverageReport:
    """Determine which Key Questions the recorded observations already support."""
    blobs = _observation_blobs(case_dir)
    covered = {q.qid for q in KEY_QUESTIONS if _question_covered(q, blobs)}
    uncovered = tuple(q for q in KEY_QUESTIONS if q.qid not in covered)
    return CoverageReport(covered=frozenset(covered), uncovered=uncovered)


def coverage_gap_message(report: CoverageReport) -> str | None:
    """The ModelRetry message naming unanswered questions + artifact hints, or None if done."""
    if report.is_complete:
        return None
    lines = [
        "Investigation incomplete — you have not yet recorded an observation addressing "
        "these Key Questions. Do NOT finalize; query the index for them first:",
    ]
    for q in report.uncovered:
        lines.append(f"  - {q.qid} ({q.label}): try {q.artifact_hint}")
    lines.append(
        "Record at least one cited observation per open question, then conclude. "
        "If after genuine search the evidence is absent, record that negative finding "
        "explicitly so the question is addressed."
    )
    return "\n".join(lines)


__all__ = [
    "KEY_QUESTIONS",
    "CoverageReport",
    "KeyQuestion",
    "analyze_coverage",
    "coverage_gap_message",
]
