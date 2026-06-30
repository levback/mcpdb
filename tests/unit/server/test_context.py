from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from mcpdb.db.policy import OpClass
from mcpdb.server.context import Context, RequestContext, build_request_context


def test_context_is_frozen() -> None:
    request = RequestContext(correlation_id="cid", principal="alice")

    with pytest.raises(FrozenInstanceError):
        request.principal = "bob"  # type: ignore[misc]


def test_context_correlation_id_propagates() -> None:
    request = build_request_context(correlation_id="corr-123", principal="alice")
    context = Context(profile="main", op_class=OpClass.READ, request=request)

    db_context = context.to_db_context()

    assert db_context.request_id == "corr-123"
    assert db_context.principal == "alice"
