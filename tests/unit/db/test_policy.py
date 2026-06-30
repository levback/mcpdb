from mcpdb.db.base import Cap
from mcpdb.db.policy import OpClass, Policy


def test_policy_read_only_denies_write_with_clear_reason() -> None:
    policy = Policy(allow_reads=True, allow_writes=False)

    decision = policy.decide(OpClass.WRITE)

    assert decision.allowed is False
    assert "WRITE denied" in decision.reason


def test_policy_allowlist_blocks_unlisted_table() -> None:
    policy = Policy(allow_reads=True, allowlist_tables=("users",))

    decision = policy.decide(OpClass.READ, table="audit")

    assert decision.allowed is False
    assert "not allowlisted" in decision.reason


def test_policy_max_rows_caps_result_size() -> None:
    policy = Policy(allow_reads=True, max_rows=50)

    decision = policy.decide(
        OpClass.READ,
        requested_cap=Cap(
            query_timeout_ms=1000,
            max_rows=999,
            max_payload_bytes=4096,
        ),
    )

    assert decision.allowed is True
    assert decision.adjusted_cap is not None
    assert decision.adjusted_cap.max_rows == 50


def test_policy_timeout_adjusted_to_min_of_policy_and_request() -> None:
    policy = Policy(allow_reads=True, query_timeout_ms=250)

    decision = policy.decide(
        OpClass.READ,
        requested_cap=Cap(
            query_timeout_ms=700,
            max_rows=10,
            max_payload_bytes=1024,
        ),
    )

    assert decision.adjusted_cap is not None
    assert decision.adjusted_cap.query_timeout_ms == 250


def test_policy_admin_requires_explicit_opt_in() -> None:
    policy = Policy(allow_reads=True, allow_admin=False)

    decision = policy.decide(OpClass.ADMIN)

    assert decision.allowed is False
    assert "ADMIN denied" in decision.reason


def test_policy_decision_is_pure() -> None:
    policy = Policy(allow_reads=True, allow_writes=True, allow_admin=False)

    first = policy.decide(OpClass.READ, table="users")
    second = policy.decide(OpClass.READ, table="users")

    assert first == second
