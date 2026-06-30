import pytest

from mcpdb.db.sql.dialect import quote_identifier, quote_table, validate_identifier


@pytest.mark.parametrize("identifier", ["users", "user_1", "_internal"])
def test_dialect_identifier_must_match_safe_regex(identifier: str) -> None:
    assert validate_identifier(identifier) == identifier


@pytest.mark.parametrize("identifier", ['users"', "users'", "users`", "users;drop", "a b"])
def test_dialect_identifier_rejects_embedded_quote(identifier: str) -> None:
    with pytest.raises(ValueError):
        validate_identifier(identifier)


def test_quote_identifier_per_backend() -> None:
    assert quote_identifier("postgres", "users") == '"users"'
    assert quote_identifier("mysql", "users") == "`users`"


def test_quote_table_handles_schema_table() -> None:
    assert quote_table("postgres", "public.users") == '"public"."users"'
