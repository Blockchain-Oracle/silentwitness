"""Accuracy scorer: TP/FP/HALLUCINATION/FN per-finding classification + metrics.

HALLUCINATION verdicts use real `find`/`grep` shell-outs against mounted evidence.
time_to_{first_finding,handoff_ready_report}_seconds pass through from runner results.
Exit codes: 0 ok; 2 config/validation; 3 missing input file; 4 empty ground truth.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Any, Literal

from harness.ground_truth.schema import GroundTruthFinding
from harness.scorer_models import (
    FindingClassification,
    HallucinationExample,
    ScoringMetrics,
    ScoringReport,
)

__all__ = [
    "FindingClassification",
    "HallucinationExample",
    "ScoringMetrics",
    "ScoringReport",
    "classify_finding",
    "compute_false_negatives",
    "score_run",
    "verify_artifact_present_in_evidence",
]

_DatasetId = Literal["nitroba", "nist-data-leakage", "nist-hacking-case", "case-trapdoor"]
_GT_MODULES: dict[str, str] = {
    "nitroba": "harness.ground_truth.nitroba_parser",
    "nist-data-leakage": "harness.ground_truth.nist_data_leakage_parser",
    "nist-hacking-case": "harness.ground_truth.nist_hacking_case_parser",
    "case-trapdoor": "harness.ground_truth.case_trapdoor_parser",
}
_RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _get_commit_sha() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(Path(__file__).resolve().parents[1]),
        )
        return r.stdout.strip() if r.returncode == 0 else f"unknown (git exit {r.returncode})"
    except FileNotFoundError:
        return "unknown (git not found on PATH)"
    except subprocess.TimeoutExpired:
        return "unknown (git rev-parse timed out)"


def _check_mount_writable(evidence_root: Path, notes: list[str]) -> None:
    try:
        flags = os.statvfs(str(evidence_root)).f_flag
        if not (flags & os.ST_RDONLY):
            notes.append(
                f"warning: evidence mount at {evidence_root} appears writable "
                "(expected ro,noexec,nosuid per PRD §6 NFR; proceeding)"
            )
    except OSError:
        pass


def verify_artifact_present_in_evidence(
    cited_substring: str, evidence_root: Path
) -> tuple[bool, list[str], int]:
    """Shell `find <root> -iname <basename>` or `grep -r -F` for glob chars.

    Returns (found, argv, hit_count). hit_count == -1 on timeout (indeterminate).
    """
    basename = cited_substring.replace("\\", "/").rsplit("/", 1)[-1]
    if not basename:
        return False, [], 0

    if re.search(r"[*?\[\]]", basename):
        argv: list[str] = [
            "grep",
            "-r",
            "-l",
            "--binary-files=text",
            "-F",
            cited_substring,
            str(evidence_root),
        ]
    else:
        argv = ["find", str(evidence_root), "-iname", basename]

    try:
        result = subprocess.run(  # noqa: S603
            argv, capture_output=True, text=True, timeout=60
        )
        lines = [ln for ln in result.stdout.strip().splitlines() if ln]
        return len(lines) > 0, argv, len(lines)
    except subprocess.TimeoutExpired:
        return False, argv, -1


def classify_finding(
    finding: dict[str, Any],
    ground_truth: list[GroundTruthFinding],
    evidence_root: Path,
    side: str,
) -> FindingClassification:
    """Classify one finding per the HALLUCINATION → TRUE_POSITIVE → FALSE_POSITIVE tree."""
    finding_id = str(finding.get("id", "unknown"))
    cited_paths: list[str] = list(finding.get("cited_artifact_paths", []))

    if not cited_paths:
        return FindingClassification(
            finding_id=finding_id,
            side=side,  # type: ignore[arg-type]
            classification="HALLUCINATION",
            matched_ground_truth_id=None,
            reason="CITED_ARTIFACT_NOT_PRESENT",
            evidence_shellout_argv=None,
            evidence_shellout_hits=0,
        )

    # Step 1: ALL cited paths return 0 hits → HALLUCINATION
    all_zero = True
    last_argv: list[str] | None = None
    last_hits: int | None = None
    for cp in cited_paths:
        _found, argv, hits = verify_artifact_present_in_evidence(cp, evidence_root)
        last_argv = argv or last_argv
        if hits == -1:
            all_zero = False
            last_hits = -1
        else:
            last_hits = hits
            if hits > 0:
                all_zero = False

    if all_zero:
        return FindingClassification(
            finding_id=finding_id,
            side=side,  # type: ignore[arg-type]
            classification="HALLUCINATION",
            matched_ground_truth_id=None,
            reason="CITED_ARTIFACT_NOT_PRESENT",
            evidence_shellout_argv=last_argv,
            evidence_shellout_hits=last_hits or 0,
        )

    # Step 2: GT match via expected_artifact_substrings
    text = str(finding.get("text", finding.get("title", "")))
    combined = " ".join([text, *cited_paths]).lower()
    for gt in ground_truth:
        for substring in gt.expected_artifact_substrings:
            if substring.lower() in combined:
                return FindingClassification(
                    finding_id=finding_id,
                    side=side,  # type: ignore[arg-type]
                    classification="TRUE_POSITIVE",
                    matched_ground_truth_id=gt.id,
                    reason="CITED_ARTIFACT_PRESENT_AND_MATCHED",
                    evidence_shellout_argv=last_argv,
                    evidence_shellout_hits=last_hits,
                )

    # Step 3: artifact present but no GT match → FALSE_POSITIVE
    return FindingClassification(
        finding_id=finding_id,
        side=side,  # type: ignore[arg-type]
        classification="FALSE_POSITIVE",
        matched_ground_truth_id=None,
        reason="CITED_ARTIFACT_PRESENT_BUT_GT_MISS",
        evidence_shellout_argv=last_argv,
        evidence_shellout_hits=last_hits,
    )


def compute_false_negatives(
    ground_truth: list[GroundTruthFinding],
    side_findings: list[dict[str, Any]],
    side: str,
) -> list[FindingClassification]:
    """Emit FALSE_NEGATIVE for each GT finding not covered by any side finding."""
    covered: set[str] = set()
    for finding in side_findings:
        text = str(finding.get("text", finding.get("title", "")))
        cited: list[str] = list(finding.get("cited_artifact_paths", []))
        combined = " ".join([text, *cited]).lower()
        for gt in ground_truth:
            for substring in gt.expected_artifact_substrings:
                if substring.lower() in combined:
                    covered.add(gt.id)

    return [
        FindingClassification(
            finding_id=f"FN-{gt.id}",
            side=side,  # type: ignore[arg-type]
            classification="FALSE_NEGATIVE",
            matched_ground_truth_id=gt.id,
            reason="NO_FINDING_FOR_GT",
            evidence_shellout_argv=None,
            evidence_shellout_hits=None,
        )
        for gt in ground_truth
        if gt.id not in covered
    ]


def _build_metrics(
    dataset_id: str,
    side: str,
    classifications: list[FindingClassification],
    fn_rows: list[FindingClassification],
    result: dict[str, Any],
    total_findings: int,
) -> ScoringMetrics:
    tp = sum(1 for c in classifications if c.classification == "TRUE_POSITIVE")
    fp = sum(1 for c in classifications if c.classification == "FALSE_POSITIVE")
    hall = sum(1 for c in classifications if c.classification == "HALLUCINATION")
    return ScoringMetrics(
        dataset_id=dataset_id,
        side=side,  # type: ignore[arg-type]
        true_positives=tp,
        false_positives=fp,
        hallucinations=hall,
        false_negatives=len(fn_rows),
        time_to_first_finding_seconds=result.get("time_to_first_finding_seconds"),
        time_to_handoff_ready_report_seconds=result.get("time_to_handoff_ready_report_seconds"),
        total_findings_emitted=total_findings,
    )


def _top_hallucination_examples(
    classifications: list[FindingClassification],
    side: str,
) -> list[HallucinationExample]:
    halls = [
        c
        for c in classifications
        if c.classification == "HALLUCINATION" and c.evidence_shellout_argv is not None
    ]
    halls.sort(key=lambda c: len((c.evidence_shellout_argv or [""])[-1]), reverse=True)
    examples = []
    for c in halls[:10]:
        argv = c.evidence_shellout_argv or []
        cited = argv[-1] if argv else ""
        examples.append(
            HallucinationExample(
                side=side,  # type: ignore[arg-type]
                finding_id=c.finding_id,
                cited_artifact_path=cited,
                evidence_shellout_argv=argv,
                evidence_shellout_hits=c.evidence_shellout_hits or 0,
                excerpt=cited[:200],
            )
        )
    return examples


def score_run(
    baseline_result_path: Path,
    silentwitness_result_path: Path,
    dataset_id: str,
    evidence_root: Path,
) -> ScoringReport:
    """Load both result JSONs, classify findings, compute metrics, return ScoringReport."""
    notes: list[str] = []
    _check_mount_writable(evidence_root, notes)

    baseline_result: dict[str, Any] = json.loads(baseline_result_path.read_text())
    sw_result: dict[str, Any] = json.loads(silentwitness_result_path.read_text())

    gt_module = import_module(_GT_MODULES[dataset_id])
    ground_truth: list[GroundTruthFinding] = gt_module.parse()
    if not ground_truth:
        raise ValueError(f"ground truth returned empty for dataset_id={dataset_id!r}")

    b_findings: list[dict[str, Any]] = baseline_result.get("findings", [])
    sw_findings: list[dict[str, Any]] = sw_result.get("findings", [])

    b_classifications = [
        classify_finding(f, ground_truth, evidence_root, "baseline") for f in b_findings
    ]
    sw_classifications = [
        classify_finding(f, ground_truth, evidence_root, "silentwitness") for f in sw_findings
    ]
    b_fn = compute_false_negatives(ground_truth, b_findings, "baseline")
    sw_fn = compute_false_negatives(ground_truth, sw_findings, "silentwitness")

    all_classifications = b_classifications + sw_classifications + b_fn + sw_fn

    b_metrics = _build_metrics(
        dataset_id, "baseline", b_classifications, b_fn, baseline_result, len(b_findings)
    )
    sw_metrics = _build_metrics(
        dataset_id, "silentwitness", sw_classifications, sw_fn, sw_result, len(sw_findings)
    )

    hall_examples = _top_hallucination_examples(
        b_classifications, "baseline"
    ) + _top_hallucination_examples(sw_classifications, "silentwitness")
    hall_examples.sort(key=lambda e: len(e.cited_artifact_path), reverse=True)
    hall_examples = hall_examples[:10]

    return ScoringReport(
        dataset_id=dataset_id,
        commit_sha=_get_commit_sha(),
        scored_at=datetime.now(UTC),
        baseline=b_metrics,
        silentwitness=sw_metrics,
        classifications=all_classifications,
        notes=notes,
        hallucination_examples=hall_examples,
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Score a baseline vs SilentWitness run.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--silentwitness", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.dataset not in _GT_MODULES:
        print(f"config/validation error: unknown dataset {args.dataset!r}", file=sys.stderr)
        return 2
    for label, path in [("baseline", args.baseline), ("silentwitness", args.silentwitness)]:
        if not path.exists():
            print(f"missing input file: {label} result not found at {path}", file=sys.stderr)
            return 3

    try:
        report = score_run(args.baseline, args.silentwitness, args.dataset, args.evidence)
    except ValueError as exc:
        if "ground truth returned empty" in str(exc):
            print(str(exc), file=sys.stderr)
            return 4
        print(f"config/validation error: {exc}", file=sys.stderr)
        return 2

    out_dir = (args.out or _RESULTS_DIR) / args.dataset
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    out_path = out_dir / f"scoring-{ts}.json"
    text = report.model_dump_json(indent=2)
    fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        Path(tmp).replace(out_path)
    except OSError as exc:
        print(f"failed to write result: {exc}", file=sys.stderr)
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return 2

    print(f"scoring report written to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
