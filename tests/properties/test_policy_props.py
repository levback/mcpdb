from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from mcpdb.db.policy import OpClass, Policy


@settings(max_examples=1000, deadline=None)
@given(
    timeout=st.integers(min_value=1, max_value=120_000),
    rows=st.integers(min_value=1, max_value=100_000),
    payload=st.integers(min_value=1, max_value=10_000_000),
)
def test_policy_caps_monotonic_under_intensify(timeout: int, rows: int, payload: int) -> None:
    weaker = Policy(
        allow_reads=True,
        query_timeout_ms=timeout,
        max_rows=rows,
        max_payload_bytes=payload,
    )
    stronger = Policy(
        allow_reads=True,
        query_timeout_ms=max(1, timeout // 2),
        max_rows=max(1, rows // 2),
        max_payload_bytes=max(1, payload // 2),
    )

    weak = weaker.decide(OpClass.READ)
    strong = stronger.decide(OpClass.READ)
    assert weak.adjusted_cap is not None
    assert strong.adjusted_cap is not None
    assert strong.adjusted_cap.query_timeout_ms <= weak.adjusted_cap.query_timeout_ms
    assert strong.adjusted_cap.max_rows <= weak.adjusted_cap.max_rows
    assert strong.adjusted_cap.max_payload_bytes <= weak.adjusted_cap.max_payload_bytes


@settings(max_examples=1000, deadline=None)
@given(op=st.sampled_from(list(OpClass)))
def test_policy_deny_idempotent_for_same_inputs(op: OpClass) -> None:
    policy = Policy(allow_reads=False, allow_writes=False, allow_admin=False)
    first = policy.decide(op)
    second = policy.decide(op)
    # OWASP A04: pure policy decision invariant.
    assert first == second
