from __future__ import annotations

import mcp.types as types
import pytest

from mcpdb.db.base import ConnectionFailure, PolicyRefused, QueryFailure
from mcpdb.db.nosql.query import MongoFilterError
from mcpdb.server.errors import McpErrorCode, map_exception


def test_errors_policy_refused_maps_to_forbidden() -> None:
    mapped = map_exception(PolicyRefused("denied"))

    assert mapped.code is McpErrorCode.FORBIDDEN
    assert mapped.message == "denied"


def test_errors_unsupported_backend_maps_to_internal() -> None:
    mapped = map_exception(QueryFailure("backend unsupported"))

    assert mapped.code is McpErrorCode.INTERNAL


def test_errors_invalid_params_carries_field_path() -> None:
    mapped = map_exception(ValueError("bad field"))
    data = mapped.to_error_data()

    assert mapped.code is McpErrorCode.INVALID_PARAMS
    assert data.code == types.INVALID_PARAMS


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (PermissionError("unauthorized"), McpErrorCode.UNAUTHORIZED),
        (TypeError("wrong type"), McpErrorCode.INVALID_PARAMS),
        (MongoFilterError("bad filter"), McpErrorCode.INVALID_PARAMS),
        (ConnectionFailure("conn"), McpErrorCode.INTERNAL),
        (KeyError("missing"), McpErrorCode.INTERNAL),
        (RuntimeError("boom"), McpErrorCode.INTERNAL),
    ],
)
def test_errors_mapping_matrix(error: Exception, expected: McpErrorCode) -> None:
    mapped = map_exception(error)
    assert mapped.code is expected
