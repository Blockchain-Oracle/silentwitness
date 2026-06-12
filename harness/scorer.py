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
from harness.scorer_helpers import (
    build_metrics,
    check_mount_writable,
    get_commit_sha,
    mk_classification,
    safe_findings,
    top_hallucination_examples,
)
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


def verify_artifact_present_in_evidence(
    cited_substring: str, evidence_root: Path
) -> tuple[bool, list[str], int]:
    """Shell `find <root> -iname <basename>` or `grep -r -F` for glob chars.

    Returns (found, argv, hit_count). hit_count == -1 on timeout (indeterminate).
    Rejects basenames starting with '-' (find/grep flag injection per CWE-88) or
    containing NUL, and caps to 512 bytes.
    """
    basename = cited_substring.replace("\\", "/").rsplit("/", 1)[-1]
    if not basename or basename.startswith("-") or "\x00" in basename or len(basename) > 512:
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
        return mk_classification(finding_id, side, "HALLUCINATION", "CITED_ARTIFACT_NOT_PRESENT")

    probes = [verify_artifact_present_in_evidence(cp, evidence_root) for cp in cited_paths]
    any_hit = any(h > 0 for _, _, h in probes)
    any_timeout = any(h == -1 for _, _, h in probes)
    notes: list[str] = []
    if any_timeout:
        timed_out = [cp for cp, (_, _, h) in zip(cited_paths, probes, strict=True) if h == -1]
        notes.append(f"finding {finding_id}: shellout timed out on cited path(s): {timed_out}")

    hit_idx = next((i for i, (_, _, h) in enumerate(probes) if h > 0), None)
    timeout_idx = next((i for i, (_, _, h) in enumerate(probes) if h == -1), None)
    best_idx = hit_idx if hit_idx is not None else (timeout_idx if timeout_idx is not None else 0)
    best_argv = probes[best_idx][1] or None
    best_hits = probes[best_idx][2]
    evidence_kw = {
        "evidence_shellout_argv": best_argv,
        "evidence_shellout_hits": best_hits,
        "notes": notes,
    }

    if not any_hit and not any_timeout:
        return mk_classification(
            finding_id,
            side,
            "HALLUCINATION",
            "CITED_ARTIFACT_NOT_PRESENT",
            evidence_shellout_argv=best_argv,
            evidence_shellout_hits=0,
            notes=notes,
        )

    text = str(finding.get("text", finding.get("title", "")))
    combined = " ".join([text, *cited_paths]).lower()
    for gt in ground_truth:
        for substring in gt.expected_artifact_substrings:
            if substring.lower() in combined:
                return mk_classification(
                    finding_id,
                    side,
                    "TRUE_POSITIVE",
                    "CITED_ARTIFACT_PRESENT_AND_MATCHED",
                    matched_ground_truth_id=gt.id,
                    **evidence_kw,
                )

    return mk_classification(
        finding_id,
        side,
        "FALSE_POSITIVE",
        "CITED_ARTIFACT_PRESENT_BUT_GT_MISS",
        **evidence_kw,
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
        mk_classification(
            f"FN-{gt.id}",
            side,
            "FALSE_NEGATIVE",
            "NO_FINDING_FOR_GT",
            matched_ground_truth_id=gt.id,
            evidence_shellout_hits=None,
        )
        for gt in ground_truth
        if gt.id not in covered
    ]


def score_run(
    baseline_result_path: Path,
    silentwitness_result_path: Path,
    dataset_id: str,
    evidence_root: Path,
) -> ScoringReport:
    """Load both result JSONs, classify findings, compute metrics, return ScoringReport."""
    notes: list[str] = []
    check_mount_writable(evidence_root, notes)

    if dataset_id not in _GT_MODULES:
        raise ValueError(f"unknown dataset_id={dataset_id!r}")

    baseline_result: dict[str, Any] = json.loads(baseline_result_path.read_text())
    sw_result: dict[str, Any] = json.loads(silentwitness_result_path.read_text())

    gt_module = import_module(_GT_MODULES[dataset_id])
    ground_truth: list[GroundTruthFinding] = gt_module.parse()
    if not ground_truth:
        raise ValueError(f"ground truth returned empty for dataset_id={dataset_id!r}")

    b_findings = safe_findings(baseline_result.get("findings", []), notes, "baseline")
    sw_findings = safe_findings(sw_result.get("findings", []), notes, "silentwitness")

    b_classifications = [
        classify_finding(f, ground_truth, evidence_root, "baseline") for f in b_findings
    ]
    sw_classifications = [
        classify_finding(f, ground_truth, evidence_root, "silentwitness") for f in sw_findings
    ]
    b_fn = compute_false_negatives(ground_truth, b_findings, "baseline")
    sw_fn = compute_false_negatives(ground_truth, sw_findings, "silentwitness")

    all_classifications = b_classifications + sw_classifications + b_fn + sw_fn
    for c in all_classifications:
        notes.extend(c.notes)

    b_metrics = build_metrics(
        dataset_id, "baseline", b_classifications, len(b_fn), baseline_result, len(b_findings)
    )
    sw_metrics = build_metrics(
        dataset_id, "silentwitness", sw_classifications, len(sw_fn), sw_result, len(sw_findings)
    )

    hall_examples = top_hallucination_examples(
        b_classifications, "baseline"
    ) + top_hallucination_examples(sw_classifications, "silentwitness")
    hall_examples.sort(key=lambda e: len(e.cited_artifact_path), reverse=True)
    hall_examples = hall_examples[:10]

    return ScoringReport(
        dataset_id=dataset_id,
        commit_sha=get_commit_sha(),
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
    if not args.evidence.exists():
        print(f"missing input: evidence_root {args.evidence} does not exist", file=sys.stderr)
        return 3
    for label, path in [("baseline", args.baseline), ("silentwitness", args.silentwitness)]:
        if not path.exists():
            print(f"missing input file: {label} result not found at {path}", file=sys.stderr)
            return 3

    try:
        report = score_run(args.baseline, args.silentwitness, args.dataset, args.evidence)
    except json.JSONDecodeError as exc:
        print(f"malformed result file: {exc}", file=sys.stderr)
        return 3
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
        except OSError as cleanup_exc:
            print(f"warning: failed to remove temp file {tmp}: {cleanup_exc}", file=sys.stderr)
        return 2

    print(f"scoring report written to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
