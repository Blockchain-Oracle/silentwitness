"""Interval-based critic trigger; idempotent; persists state for restart-resume.

Watches ``case_dir/findings.json`` and signals when ``critique()`` should run
based on two OR-combined thresholds:
  - N new findings staged since the last critic run (default N=5).
  - M minutes elapsed since the last critic run (default M=10).

``should_fire`` is a pure read — idempotent, no disk writes.
``mark_fired`` is the only mutating call, thread-safe, and advances the
watermark monotonically (out-of-order concurrent calls are no-ops).
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

from pydantic import ValidationError

from silentwitness_agent._critic_state import _TriggerState
from silentwitness_agent.critic import StagedFinding
from silentwitness_common.atomic_io import write_text_atomic
from silentwitness_common.types import Confidence

_LOG = logging.getLogger(__name__)

_STATE_FILENAME = "critic_state.json"
_DEFAULT_INTERVAL_FINDINGS = 5
_DEFAULT_INTERVAL_MINUTES = 10.0


def _parse_interval_int(var: str, default: int) -> int:
    raw = os.environ.get(var)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise ValueError(
            f"{var}={raw!r} is not a valid integer; "
            f"set it to a positive integer (e.g. {default}) or unset it."
        ) from None


def _parse_interval_float(var: str, default: float) -> float:
    raw = os.environ.get(var)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise ValueError(
            f"{var}={raw!r} is not a valid number; "
            f"set it to a positive number (e.g. {default}) or unset it."
        ) from None


class CriticTrigger:
    """Interval-based critic trigger; idempotent ``should_fire``; thread-safe ``mark_fired``."""

    def __init__(
        self,
        case_dir: Path,
        examiner: str,  # passed through to critique() by callers; not stored here
        interval_findings: int | None = None,
        interval_minutes: float | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._case_dir = case_dir
        self._clock: Callable[[], datetime] = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()

        _env_n = _parse_interval_int(
            "SILENTWITNESS_CRITIC_INTERVAL_FINDINGS", _DEFAULT_INTERVAL_FINDINGS
        )
        self.interval_findings = interval_findings if interval_findings is not None else _env_n

        _env_m = _parse_interval_float(
            "SILENTWITNESS_CRITIC_INTERVAL_MINUTES", _DEFAULT_INTERVAL_MINUTES
        )
        self.interval_minutes = float(interval_minutes) if interval_minutes is not None else _env_m

        self._state = self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_fire(self, current_finding_count: int) -> bool:
        """Return True if findings-count OR elapsed-time threshold is reached.

        Idempotent and side-effect-free — calling twice returns the same answer
        until ``mark_fired`` advances the persisted watermark.

        Note: ``should_fire`` is not synchronized with ``mark_fired``.
        Callers requiring exactly-once semantics must coordinate externally.
        """
        state = self._state
        findings_delta = current_finding_count - state.last_critic_finding_count
        elapsed = self._clock() - state.last_critic_at
        findings_threshold_hit = findings_delta >= self.interval_findings
        time_threshold_hit = elapsed >= timedelta(minutes=self.interval_minutes)
        return findings_threshold_hit or time_threshold_hit

    def mark_fired(self, current_finding_count: int) -> None:
        """Persist the firing watermark atomically; thread-safe; monotonic-only.

        Out-of-order or duplicate calls (count ≤ current watermark) are
        silently ignored — the watermark only advances, never regresses.
        """
        with self._lock:
            if current_finding_count < self._state.last_critic_finding_count:
                return
            new_state = _TriggerState(
                last_critic_at=self._clock(),
                last_critic_finding_count=current_finding_count,
            )
            try:
                write_text_atomic(
                    self._case_dir / _STATE_FILENAME,
                    new_state.model_dump_json(),
                )
            except OSError:
                _LOG.error(
                    "critic_trigger: failed to persist state path=%s count=%d; "
                    "trigger will re-fire next interval",
                    self._case_dir / _STATE_FILENAME,
                    current_finding_count,
                    exc_info=True,
                )
                raise
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

        Observations without interpretations, or with empty text fields, are
        skipped — they cannot be evaluated by the critic.
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
            obs_text: str = obs.get("text") or ""
            interp_text: str = latest.get("text") or ""
            if not obs_text or not interp_text:
                _LOG.warning(
                    "critic_trigger: skipping observation with empty text observation_id=%s",
                    obs.get("observation_id", "<unknown>"),
                )
                continue
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
                    observation_text=obs_text,
                    interpretation_text=interp_text,
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
        except (ValidationError, OSError, UnicodeDecodeError) as exc:
            _LOG.warning(
                "critic_trigger: cannot load state file path=%s err=%s; "
                "using clock-anchored defaults",
                path,
                exc,
            )
            return _TriggerState(last_critic_at=self._clock())

    @staticmethod
    def _read_findings_json(path: Path) -> list[Any]:
        """Return parsed findings array; empty list if file missing or unreadable."""
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            _LOG.warning("critic_trigger: cannot read findings path=%s err=%s", path, exc)
            return []
        if not isinstance(data, list):
            _LOG.warning("critic_trigger: findings.json is not a list path=%s", path)
            return []
        return data


__all__ = ["CriticTrigger"]
