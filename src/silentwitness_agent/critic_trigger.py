"""Interval-based critic trigger; idempotent; persists state for restart-resume.

Watches ``case_dir/findings.json`` and signals when ``critique()`` should run
based on two OR-combined thresholds:
  - N new findings staged since the last critic run (default N=5).
  - M minutes elapsed since the last critic run (default M=10).

``should_fire`` is a pure read — idempotent, no disk writes.
``mark_fired`` is the only mutating call and is thread-safe.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from silentwitness_agent._critic_state import _TriggerState
from silentwitness_agent.critic import StagedFinding
from silentwitness_common.atomic_io import write_text_atomic
from silentwitness_common.types import Confidence

_LOG = logging.getLogger(__name__)

_STATE_FILENAME = "critic_state.json"
_FINDINGS_FILENAME = "findings.json"
_DEFAULT_INTERVAL_FINDINGS = 5
_DEFAULT_INTERVAL_MINUTES = 10.0


class CriticTrigger:
    """Interval-based critic trigger; idempotent ``should_fire``; thread-safe ``mark_fired``."""

    def __init__(
        self,
        case_dir: Path,
        examiner: str,
        interval_findings: int | None = None,
        interval_minutes: float | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._case_dir = case_dir
        self._examiner = examiner
        self._clock: Callable[[], datetime] = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()

        if interval_findings is not None:
            self.interval_findings = interval_findings
        else:
            env = os.environ.get("SILENTWITNESS_CRITIC_INTERVAL_FINDINGS")
            self.interval_findings = int(env) if env else _DEFAULT_INTERVAL_FINDINGS

        if interval_minutes is not None:
            self.interval_minutes = float(interval_minutes)
        else:
            env_m = os.environ.get("SILENTWITNESS_CRITIC_INTERVAL_MINUTES")
            self.interval_minutes = float(env_m) if env_m else _DEFAULT_INTERVAL_MINUTES

        self._state = self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_fire(self, current_finding_count: int) -> bool:
        """Return True if findings-count OR elapsed-time threshold is reached.

        Idempotent and side-effect-free — calling twice returns the same answer
        until ``mark_fired`` advances the persisted watermark.
        """
        state = self._state
        findings_delta = current_finding_count - state.last_critic_finding_count
        elapsed = self._clock() - state.last_critic_at
        findings_threshold_hit = findings_delta >= self.interval_findings
        time_threshold_hit = elapsed >= timedelta(minutes=self.interval_minutes)
        return findings_threshold_hit or time_threshold_hit

    def mark_fired(self, current_finding_count: int) -> None:
        """Persist the firing watermark atomically; thread-safe."""
        with self._lock:
            new_state = _TriggerState(
                last_critic_at=self._clock(),
                last_critic_finding_count=current_finding_count,
            )
            write_text_atomic(
                self._case_dir / _STATE_FILENAME,
                new_state.model_dump_json(),
            )
            self._state = new_state
            _LOG.info(
                "critic_trigger: fired case_dir=%s count=%d",
                self._case_dir,
                current_finding_count,
            )

    def staged_findings_for_review(self, findings_json_path: Path) -> list[StagedFinding]:
        """Return findings staged after the last critic run as StagedFinding objects.

        Reads ``findings_json_path`` (the case ``findings.json``), slices to
        entries with index ≥ ``last_critic_finding_count``, and attaches
        ``cited_blob_paths`` pointing at ``case_dir/audit/blobs/<audit_id>.txt``
        for every ``audit_id`` cited by the observation.

        Observations without any interpretations are skipped — they cannot be
        evaluated by the critic without an interpretation to assess.
        """
        raw = self._read_findings_json(findings_json_path)
        start = self._state.last_critic_finding_count
        pending = raw[start:]

        blobs_dir = self._case_dir / "audit" / "blobs"
        results: list[StagedFinding] = []
        for obs in pending:
            if not isinstance(obs, dict):
                continue
            interpretations: list[dict[str, Any]] = obs.get("interpretations") or []
            if not interpretations:
                continue
            latest = interpretations[-1]
            confidence_raw: str = latest.get("confidence", "LOW")
            try:
                confidence = Confidence(confidence_raw)
            except ValueError:
                confidence = Confidence.LOW
            audit_ids: list[str] = obs.get("audit_ids") or []
            blob_paths = [blobs_dir / f"{aid}.txt" for aid in audit_ids]
            results.append(
                StagedFinding(
                    finding_id=obs.get("observation_id", f"unknown-{len(results)}"),
                    observation_text=obs.get("text", ""),
                    interpretation_text=latest.get("text", ""),
                    confidence=confidence,
                    cited_audit_ids=audit_ids,
                    cited_blob_paths=blob_paths,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_state(self) -> _TriggerState:
        """Read critic_state.json; return clock-anchored defaults if missing or corrupt.

        Using ``clock()`` (not epoch) as the default ``last_critic_at`` so a
        brand-new case does not immediately satisfy the time threshold.
        """
        path = self._case_dir / _STATE_FILENAME
        if not path.exists():
            return _TriggerState(last_critic_at=self._clock())
        try:
            return _TriggerState.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            _LOG.warning("critic_trigger: corrupt state file path=%s; using defaults", path)
            return _TriggerState(last_critic_at=self._clock())

    @staticmethod
    def _read_findings_json(path: Path) -> list[Any]:
        """Return parsed findings array; empty list if file missing or unreadable."""
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _LOG.warning("critic_trigger: cannot read findings path=%s err=%s", path, exc)
            return []
        if not isinstance(data, list):
            _LOG.warning("critic_trigger: findings.json is not a list path=%s", path)
            return []
        return data


__all__ = ["CriticTrigger"]
