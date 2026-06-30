from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import mcp.types as types

from mcpdb.db.base import ConnectionFailure, PolicyRefused, QueryFailure, RegistryError
from mcpdb.db.nosql.query import MongoFilterError


class McpErrorCode(StrEnum):
    INVALID_PARAMS = "INVALID_PARAMS"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL = "INTERNAL"


@dataclass(frozen=True)
class McpMappedError:
    code: McpErrorCode
    message: str
    field_path: str | None = None

    def to_error_data(self) -> types.ErrorData:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field_path is not None:
            payload["field_path"] = self.field_path

        if self.code is McpErrorCode.INVALID_PARAMS:
            rpc_code = types.INVALID_PARAMS
        else:
            rpc_code = types.INTERNAL_ERROR

        return types.ErrorData(code=rpc_code, message=self.message, data=payload)


def map_exception(error: Exception) -> McpMappedError:
    if isinstance(error, PolicyRefused):
        return McpMappedError(McpErrorCode.FORBIDDEN, str(error))

    if isinstance(error, PermissionError):
        return McpMappedError(McpErrorCode.UNAUTHORIZED, str(error))

    if isinstance(error, ValueError | TypeError | MongoFilterError):
        return McpMappedError(McpErrorCode.INVALID_PARAMS, str(error))

    if isinstance(error, ConnectionFailure | QueryFailure | RegistryError | KeyError):
        return McpMappedError(McpErrorCode.INTERNAL, str(error))

    return McpMappedError(McpErrorCode.INTERNAL, "internal server error")
