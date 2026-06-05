"""Property test for the pslist/psscan diff invariant (story BDD
lines 92-95). The agent uses ``psscan_pids -pslist_pids`` as the
"hidden-or-terminated" candidate set; the critic relies on this
relationship at demo time when challenging process-existence claims."""

from __future__ import annotations

from hypothesis import given, strategies as st

from silentwitness_mcp.tools.memory import hidden_or_terminated_candidates


@given(
    pslist_pids=st.sets(st.integers(min_value=0, max_value=65535), max_size=64),
    psscan_pids=st.sets(st.integers(min_value=0, max_value=65535), max_size=64),
)
def test_diff_is_set_subtraction(pslist_pids: set[int], psscan_pids: set[int]) -> None:
    """Identity: candidates ≡ psscan -pslist."""
    candidates = hidden_or_terminated_candidates(pslist_pids, psscan_pids)
    assert candidates == psscan_pids - pslist_pids
    # Every candidate is in psscan but NOT in pslist (the BDD-stated contract).
    for pid in candidates:
        assert pid in psscan_pids
        assert pid not in pslist_pids


@given(s=st.sets(st.integers(min_value=0, max_value=65535), max_size=64))
def test_diff_against_self_is_empty(s: set[int]) -> None:
    """Reflexivity: pslist == psscan ⇒ no hidden-or-terminated candidates."""
    assert hidden_or_terminated_candidates(s, s) == set()


@given(
    base=st.sets(st.integers(min_value=0, max_value=65535), max_size=32),
    extra=st.sets(st.integers(min_value=0, max_value=65535), max_size=32),
)
def test_extras_are_always_candidates(base: set[int], extra: set[int]) -> None:
    """Monotone: any PID present in psscan but not pslist appears in the
    candidate set, regardless of unrelated content."""
    pslist_pids = base
    psscan_pids = base | extra
    candidates = hidden_or_terminated_candidates(pslist_pids, psscan_pids)
    for pid in extra - base:
        assert pid in candidates
