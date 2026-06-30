from __future__ import annotations

from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncConnection

from mcpdb.db.policy import Policy
from mcpdb.db.sql.base import QueryFailure, SqlConnector


class _NoopConnector(SqlConnector):
    backend: str = "sqlite"
    minimum_supported_major: int = 3

    async def _check_server_version(self, connection: AsyncConnection) -> None:
        _ = connection

    async def _execute_query(self, query: Any):
        _ = query
        raise NotImplementedError


@settings(max_examples=1000, deadline=None)
@given(
    column=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=8,
    ),
    value=st.integers(min_value=-1_000_000, max_value=1_000_000),
)
def test_sql_query_binds_never_string_concat_invariant(column: str, value: int) -> None:
    connector = _NoopConnector(dsn="sqlite+aiosqlite:///:memory:", policy=Policy(allow_reads=True))
    statement = f"SELECT :{column} AS {column}"
    query = connector._build_query(statement, {column: value})

    # OWASP A03: parameters remain in bound map and are not interpolated in SQL text.
    assert query.statement == statement
    assert query.parameters == {column: value}


@settings(max_examples=1000, deadline=None)
@given(
    raw=st.one_of(
        st.text(min_size=0, max_size=32).map(lambda s: "{" + s),
        st.text(min_size=0, max_size=32).map(lambda s: s + "}"),
        st.text(min_size=0, max_size=32).map(lambda s: "{" + s + "}"),
    )
)
def test_sql_query_template_braces_are_rejected(raw: str) -> None:
    connector = _NoopConnector(dsn="sqlite+aiosqlite:///:memory:", policy=Policy(allow_reads=True))
    try:
        connector._build_query(raw, {})
    except QueryFailure:
        assert True
    else:  # pragma: no cover
        raise AssertionError("template brace query unexpectedly accepted")
