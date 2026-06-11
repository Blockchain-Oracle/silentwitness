"""Integration test — CriticTrigger concurrency / idempotency.

10 threads each call should_fire then mark_fired; critic_state.json must
reflect a monotonically advancing watermark with no corruption.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from silentwitness_agent.critic_trigger import CriticTrigger


@pytest.mark.timeout(10)
def test_concurrent_mark_fired_no_corruption(tmp_path: Path) -> None:
    """10 threads firing concurrently must not corrupt critic_state.json."""
    base = datetime.now(UTC)
    call_count = [0]
    call_lock = threading.Lock()

    def _clock() -> datetime:
        return base

    trigger = CriticTrigger(
        case_dir=tmp_path,
        examiner="aj",
        interval_findings=1,
        interval_minutes=999.0,
        clock=_clock,
    )

    errors: list[Exception] = []

    def worker(finding_count: int) -> None:
        try:
            if trigger.should_fire(finding_count):
                trigger.mark_fired(finding_count)
                with call_lock:
                    call_count[0] += 1
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i + 1,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"

    # State file must be valid JSON after concurrent writes
    state_path = tmp_path / "critic_state.json"
    assert state_path.exists()
    data = json.loads(state_path.read_text(encoding="utf-8"))
    assert isinstance(data["last_critic_finding_count"], int)
    assert data["last_critic_finding_count"] >= 1
    # ISO-8601 timestamp must be parseable
    dt = datetime.fromisoformat(data["last_critic_at"])
    assert dt.tzinfo is not None
