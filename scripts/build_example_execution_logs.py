#!/usr/bin/env python3
# ruff: noqa: E501
"""Build docs/EXAMPLE_EXECUTION_LOGS/ — synthetic case readable without running the system.

Generates a tiny synthetic case-example-001_EXAMPLE/ tree with hand-crafted JSONL
audit rows, a rendered report.md, evidence registry, HMAC ledger, and an index
README.md. All timestamps and SHA256s are FIXED so re-running this script produces
byte-identical output (verifiable via `git diff --exit-code`).

Filenames are suffixed `_EXAMPLE` so judges cannot mistake this for a real
investigation (vocabulary discipline + no-mock carve-out).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path
from typing import Any

_CASE_DIR_NAME = "case-example-001_EXAMPLE"
_CASE_ID = "case-example-001"
_EXAMINER = "example-sansforensics"
_T0 = "2026-06-13T12:00:00Z"
_T1 = "2026-06-13T12:00:04Z"
_T2 = "2026-06-13T12:00:09Z"
_T3 = "2026-06-13T12:00:14Z"
_T4 = "2026-06-13T12:00:20Z"
_T5 = "2026-06-13T12:00:25Z"

# Synthetic 4-byte evidence file content
_EVIDENCE_BYTES = b"E\xaa\x0f\x00"  # deterministic 4 bytes
_EVIDENCE_SHA256 = hashlib.sha256(_EVIDENCE_BYTES).hexdigest()

# Stable stdout SHA256s — synthetic "tool output" content.
# DETERMINISTIC: editing these byte-strings invalidates the committed tree's
# Appendix-Audit hex prefixes in scripts/_example_templates/report.md. The
# byte-equality test (tests/integration/test_example_execution_logs.py) will
# catch the drift, but update the report template's hex columns to match.
_VOL_STDOUT_SHA256 = hashlib.sha256(
    b"# vol3 windows.pslist\nPID,PPID,Name\n4,0,System\n388,4,smss.exe\n"
).hexdigest()
_MFT_STDOUT_SHA256 = hashlib.sha256(
    b"# MFTECmd output\nEntryNumber,FileName\n42,sample_EXAMPLE.bin\n"
).hexdigest()
_EVTX_STDOUT_SHA256 = hashlib.sha256(
    b"# EvtxECmd output\nEventID,Channel\n4624,Security\n"
).hexdigest()

# HMAC key — literal sentinel; DO NOT replace with a real key, this ledger is
# synthetic. The key string carries its own disclosure substring.
_LEDGER_KEY = b"EXAMPLE-not-a-real-secret-EXAMPLE"  # pragma: allowlist secret

_TPL_DIR = Path(__file__).resolve().parent / "_example_templates"


def _read_tpl(name: str) -> str:
    return (_TPL_DIR / name).read_text(encoding="utf-8")


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _jl(rows: list[dict[str, Any]]) -> str:
    """Render rows as JSONL with sorted keys for byte-determinism."""
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def _build(out: Path) -> None:
    case_dir = out / _CASE_DIR_NAME
    (case_dir / "audit").mkdir(parents=True, exist_ok=True)
    (case_dir / ".silentwitness").mkdir(parents=True, exist_ok=True)

    _write(
        case_dir / ".silentwitness" / "case.toml",
        f'case_id = "{_CASE_ID}"\nexaminer = "{_EXAMINER}"\ncreated_at = "{_T0}"\n',
    )

    _write(
        case_dir / "evidence.json",
        json.dumps(
            {
                "schema_version": 1,
                "records": [
                    {
                        "evidence_id": "ev-example-001",
                        "path": "/evidence/sample_EXAMPLE.bin",
                        "sha256": _EVIDENCE_SHA256,
                        "size_bytes": len(_EVIDENCE_BYTES),
                        "registered_at": _T0,
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    _write(
        case_dir / "audit" / "memory.jsonl",
        _jl(
            [
                {
                    "audit_id": "sift-example-20260613-001",
                    "ts": _T1,
                    "tool_name": "vol_pslist",
                    "backend": "memory",
                    "elapsed_ms": 4200,
                    "status": "OK",
                    "result_sha256": _VOL_STDOUT_SHA256,
                    "stdout_lines": 32,
                }
            ]
        ),
    )
    _write(
        case_dir / "audit" / "disk.jsonl",
        _jl(
            [
                {
                    "audit_id": "sift-example-20260613-002",
                    "ts": _T2,
                    "tool_name": "parse_mft",
                    "backend": "disk",
                    "elapsed_ms": 1800,
                    "status": "OK",
                    "result_sha256": _MFT_STDOUT_SHA256,
                    "stdout_lines": 14,
                }
            ]
        ),
    )
    _write(
        case_dir / "audit" / "log.jsonl",
        _jl(
            [
                {
                    "audit_id": "sift-example-20260613-003",
                    "ts": _T3,
                    "tool_name": "parse_evtx",
                    "backend": "log",
                    "elapsed_ms": 950,
                    "status": "OK",
                    "result_sha256": _EVTX_STDOUT_SHA256,
                    "stdout_lines": 21,
                }
            ]
        ),
    )

    _write(
        case_dir / "audit" / "findings.jsonl",
        _jl(
            [
                {
                    "audit_id": "sift-example-20260613-004",
                    "ts": _T4,
                    "tool_name": "record_observation",
                    "backend": "agent",
                    "status": "APPROVED",
                    "cited_audit_ids": ["sift-example-20260613-001"],
                    "citation_gate": "PASS",
                    "entity_gate_matches": ["smss.exe", "PID 388"],
                    "envelope": {
                        "observation_text": (
                            "smss.exe (PID 388) child of System (PID 4) "
                            "— typical Windows boot chain."
                        ),
                        "interpretation": "process-tree baseline matches expected",
                    },
                }
            ]
        ),
    )

    _write(
        case_dir / "audit" / "hypothesis.jsonl",
        _jl(
            [
                {
                    "ts": _T1,
                    "hypothesis_id": "H-001",
                    "transition": "form",
                    "text": "if memory tells the story, then pslist will show a child without a parent",
                },
                {
                    "ts": _T1,
                    "hypothesis_id": "H-001",
                    "transition": "dispatch",
                    "specialist": "memory",
                },
                {
                    "ts": _T2,
                    "hypothesis_id": "H-001",
                    "transition": "confirm",
                    "via_audit_id": "sift-example-20260613-001",
                },
                {
                    "ts": _T3,
                    "hypothesis_id": "H-001",
                    "transition": "pivot",
                    "reason": "vol3 symbol-table mismatch; rebuilt",
                },
                {
                    "ts": _T4,
                    "hypothesis_id": "H-001",
                    "transition": "confirm",
                    "via_audit_id": "sift-example-20260613-001",
                },
            ]
        ),
    )

    _write(
        case_dir / "audit" / "critic.jsonl",
        _jl(
            [
                {
                    "ts": _T4,
                    "verdict": "CHALLENGE",
                    "finding_id": "F-example-001",
                    "reason": "interpretation requires intercepted-traffic evidence",
                },
                {
                    "ts": _T5,
                    "verdict": "APPROVED",
                    "finding_id": "F-example-001",
                    "reason": "corroborated via parse_evtx 4624 logon trail",
                },
            ]
        ),
    )

    _write(
        case_dir / "findings.json",
        json.dumps(
            {
                "schema_version": 1,
                "findings": [
                    {
                        "finding_id": "F-example-001",
                        "status": "APPROVED",
                        "title": "smss.exe spawned under System — boot baseline",
                        "observation_text": "smss.exe (PID 388) child of System (PID 4).",
                        "interpretation": "Process tree matches expected Windows boot chain.",
                        "caveats": ["Synthetic example; not a real investigation."],
                        "mitre_attack_tag": "T1543.003",
                        "cited_audit_ids": ["sift-example-20260613-001"],
                        "approved_at": _T5,
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )

    # HMAC ledger
    payload = f"F-example-001|APPROVED|sift-example-20260613-001|{_T5}".encode()
    ledger_hmac = hmac.new(_LEDGER_KEY, payload, hashlib.sha256).hexdigest()
    _write(
        case_dir / "ledger.jsonl",
        _jl(
            [
                {
                    "ledger_id": "L-example-001",
                    "finding_id": "F-example-001",
                    "ts": _T5,
                    "pbkdf2_iter": 600000,
                    "hmac_sha256": ledger_hmac,
                    "signed_at": _T5,
                    "notes": "HMAC key is the literal string EXAMPLE-not-a-real-secret-EXAMPLE; "
                    "documented in docs/EXAMPLE_EXECUTION_LOGS/README.md.",
                },
            ]
        ),
    )

    # Rendered report.md
    _write(case_dir / "report.md", _read_tpl("report.md"))

    # Index README
    _write(out / "README.md", _read_tpl("index_README.md"))
    _check_referential_integrity(out / _CASE_DIR_NAME)


def _check_referential_integrity(case_dir: Path) -> None:
    """Assert every cited_audit_id resolves to an existing audit row.

    Catches the regression class where the script (or a maintainer) writes a
    finding citing an audit_id that was never logged — the report's verify-link
    would dangle, defeating the whole point of the example tree.
    """
    audit_ids: set[str] = set()
    for jsonl in (case_dir / "audit").glob("*.jsonl"):
        for line in jsonl.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                if "audit_id" in row:
                    audit_ids.add(str(row["audit_id"]))
    findings = json.loads((case_dir / "findings.json").read_text())
    for f in findings.get("findings", []):
        for cited in f.get("cited_audit_ids", []):
            if cited not in audit_ids:
                raise ValueError(f"referential integrity: {cited!r} not in audit/*.jsonl")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build EXAMPLE_EXECUTION_LOGS tree.")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    _build(args.out)
    print(f"wrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
