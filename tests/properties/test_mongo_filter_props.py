from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from mcpdb.db.nosql.query import (
    ALLOWED_FILTER_OPERATORS,
    MongoFilter,
    MongoFilterError,
    QueryValidationConfig,
)

_FIELD_NAME = st.text(
    alphabet=st.characters(min_codepoint=97, max_codepoint=122),
    min_size=1,
    max_size=8,
)

_SCALAR = st.one_of(
    st.integers(min_value=-10_000, max_value=10_000),
    st.text(max_size=16),
    st.booleans(),
)


@settings(max_examples=1000, deadline=None)
@given(field=_FIELD_NAME, value=_SCALAR)
def test_mongo_filter_round_trip_via_motor_translator(field: str, value: object) -> None:
    payload = {field: {"$eq": value}}
    model = MongoFilter.from_document(payload, config=QueryValidationConfig())

    # OWASP A04: invariant-based test ensures translation is deterministic.
    assert model.document == payload
    assert model.uses_regex is False


@settings(max_examples=1000, deadline=None)
@given(
    field=_FIELD_NAME,
    invalid_op=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=10,
    ).filter(lambda s: f"${s}" not in ALLOWED_FILTER_OPERATORS),
)
def test_mongo_filter_rejects_unknown_op_invariant(field: str, invalid_op: str) -> None:
    payload = {field: {f"${invalid_op}": 1}}

    try:
        MongoFilter.from_document(payload, config=QueryValidationConfig())
    except MongoFilterError:
        assert True
    else:  # pragma: no cover
        raise AssertionError("unknown operator unexpectedly accepted")
