from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import mcp.types as types

from mcpdb.db.base import Connector, OperationResult, PolicyRefused, QueryFailure
from mcpdb.db.policy import OpClass, Policy
from mcpdb.server.context import Context, RequestContext
from mcpdb.server.errors import McpMappedError, map_exception

LOGGER = logging.getLogger(__name__)
SQL_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
SQL_LINE_COMMENT_RE = re.compile(r"--[^\n]*")


@dataclass(frozen=True)
class ProfileToolBinding:
    profile: str
    backend: str
    connector: Connector
    policy: Policy


class ToolService:
    def __init__(self, bindings: Mapping[str, ProfileToolBinding]) -> None:
        self._bindings = dict(bindings)

    async def db_query(
        self,
        *,
        profile: str,
        statement: str | None = None,
        parameters: dict[str, Any] | None = None,
        operation: str | None = None,
        collection: str | None = None,
        filter_doc: dict[str, Any] | None = None,
        projection: dict[str, int] | None = None,
        limit: int | None = None,
        request: RequestContext,
    ) -> dict[str, Any]:
        binding = self._binding(profile)

        if binding.backend == "mongodb":
            mongo_operation = operation or "find"
            op_class = self._mongo_op_class(mongo_operation)
            self._check_policy(binding, op_class)
            payload = {
                "collection": collection,
                "filter": filter_doc,
                "projection": projection,
                "limit": limit,
                "parameters": parameters,
            }
            result = await self._execute(binding, request, mongo_operation, payload)
        else:
            if statement is None or not statement.strip():
                raise ValueError("statement is required for SQL query")
            op_class = self._sql_op_class(statement)
            self._check_policy(binding, op_class)
            result = await self._execute(binding, request, statement, parameters or {})

        return self._operation_payload(profile, binding.backend, result)

    async def db_introspect(
        self,
        *,
        profile: str,
        target: str | None,
        request: RequestContext,
    ) -> dict[str, Any]:
        binding = self._binding(profile)
        self._check_policy(binding, OpClass.READ)
        context = Context(profile=profile, op_class=OpClass.READ, request=request).to_db_context()
        await binding.connector.connect(context)
        try:
            result = await binding.connector.introspect(context, target)
        finally:
            await binding.connector.close(context)
        return self._operation_payload(profile, binding.backend, result)

    async def db_ping(self, *, profile: str, request: RequestContext) -> dict[str, Any]:
        binding = self._binding(profile)
        self._check_policy(binding, OpClass.READ)
        context = Context(profile=profile, op_class=OpClass.READ, request=request).to_db_context()
        await binding.connector.connect(context)
        try:
            latency_ms = await binding.connector.ping(context)
        finally:
            await binding.connector.close(context)
        return {"profile": profile, "backend": binding.backend, "latency_ms": latency_ms}

    async def db_list_profiles(self) -> dict[str, Any]:
        profiles = [
            {"name": binding.profile, "backend": binding.backend}
            for binding in self._bindings.values()
        ]
        return {"profiles": sorted(profiles, key=lambda item: str(item["name"]))}

    async def dispatch(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any] | types.CallToolResult:
        request = self._request_context(arguments)
        LOGGER.info(
            "tool_invocation",
            extra={
                "tool": tool_name,
                "correlation_id": request.correlation_id,
                "principal": request.principal,
            },
        )  # NIST AU-3: structured tool invocation log

        try:
            if tool_name == "db_query":
                return await self.db_query(
                    profile=str(arguments.get("profile", "")),
                    statement=self._as_optional_str(arguments.get("statement")),
                    parameters=self._as_optional_dict(arguments.get("parameters")),
                    operation=self._as_optional_str(arguments.get("operation")),
                    collection=self._as_optional_str(arguments.get("collection")),
                    filter_doc=self._as_optional_dict(arguments.get("filter")),
                    projection=self._as_projection(arguments.get("projection")),
                    limit=self._as_optional_int(arguments.get("limit")),
                    request=request,
                )

            if tool_name == "db_introspect":
                return await self.db_introspect(
                    profile=str(arguments.get("profile", "")),
                    target=self._as_optional_str(arguments.get("target")),
                    request=request,
                )

            if tool_name == "db_ping":
                return await self.db_ping(
                    profile=str(arguments.get("profile", "")),
                    request=request,
                )

            if tool_name == "db_list_profiles":
                return await self.db_list_profiles()

            raise ValueError(f"unknown tool: {tool_name}")
        except Exception as error:
            mapped = map_exception(error)
            return self._tool_error_result(mapped)

    def tool_definitions(self) -> list[types.Tool]:
        return [
            types.Tool(
                name="db_query",
                description="Execute database query for SQL or Mongo profiles",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profile": {"type": "string"},
                        "statement": {"type": "string"},
                        "parameters": {"type": "object"},
                        "operation": {"type": "string"},
                        "collection": {"type": "string"},
                        "filter": {"type": "object"},
                        "projection": {"type": "object"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["profile"],
                },
            ),
            types.Tool(
                name="db_introspect",
                description="Introspect profile metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profile": {"type": "string"},
                        "target": {"type": "string"},
                    },
                    "required": ["profile"],
                },
            ),
            types.Tool(
                name="db_ping",
                description="Ping profile database and return latency",
                inputSchema={
                    "type": "object",
                    "properties": {"profile": {"type": "string"}},
                    "required": ["profile"],
                },
            ),
            types.Tool(
                name="db_list_profiles",
                description="List configured profile names and backends",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    def _binding(self, profile: str) -> ProfileToolBinding:
        if not profile or profile not in self._bindings:
            raise ValueError(f"unknown profile: {profile}")
        return self._bindings[profile]

    def _check_policy(self, binding: ProfileToolBinding, op_class: OpClass) -> None:
        decision = binding.policy.decide(op_class)
        if not decision.allowed:
            raise PolicyRefused(decision.reason)  # OWASP A01: enforce OpClass at Tool boundary

    async def _execute(
        self,
        binding: ProfileToolBinding,
        request: RequestContext,
        statement: str,
        parameters: dict[str, Any],
    ) -> OperationResult:
        op_class = (
            self._mongo_op_class(statement)
            if binding.backend == "mongodb"
            else self._sql_op_class(statement)
        )
        context = Context(
            profile=binding.profile,
            op_class=op_class,
            request=request,
        ).to_db_context()
        await binding.connector.connect(context)
        try:
            return await binding.connector.execute(context, statement, parameters)
        finally:
            await binding.connector.close(context)

    @staticmethod
    def _sql_op_class(statement: str) -> OpClass:
        normalized = SQL_BLOCK_COMMENT_RE.sub("", statement)
        normalized = SQL_LINE_COMMENT_RE.sub("", normalized)
        normalized = normalized.lstrip().lower()
        if normalized.startswith(("insert", "update", "delete", "create", "drop", "alter")):
            return OpClass.WRITE
        if normalized.startswith(("grant", "revoke", "set ", "vacuum", "analyze")):
            return OpClass.ADMIN
        return OpClass.READ

    @staticmethod
    def _mongo_op_class(operation: str) -> OpClass:
        normalized = operation.strip().lower()
        if normalized in {"find", "aggregate"}:
            return OpClass.READ
        if normalized in {"insert_one", "update_one", "delete_one"}:
            return OpClass.WRITE
        if normalized in {"server_status"}:
            return OpClass.ADMIN
        raise QueryFailure(f"unknown operation class for statement: {operation}")

    @staticmethod
    def _operation_payload(profile: str, backend: str, result: OperationResult) -> dict[str, Any]:
        return {
            "profile": profile,
            "backend": backend,
            "rows": [dict(row) for row in result.rows],
            "row_count": result.row_count,
            "payload_bytes": result.payload_bytes,
            "latency_ms": result.latency_ms,
            "truncated": result.truncated,
        }

    @staticmethod
    def _tool_error_result(mapped: McpMappedError) -> types.CallToolResult:
        return types.CallToolResult(
            isError=True,
            content=[types.TextContent(type="text", text=mapped.message)],
            structuredContent={
                "code": mapped.code,
                "message": mapped.message,
                "field_path": mapped.field_path,
            },
        )

    @staticmethod
    def _request_context(arguments: dict[str, Any]) -> RequestContext:
        # OWASP A01/A07: never trust caller-provided identity metadata at tool arg boundary.
        _ = arguments
        return RequestContext(
            correlation_id="tool-request",
            principal="anonymous",
            source_ip="127.0.0.1",
            user_agent="mcp-client",
        )

    @staticmethod
    def _as_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("expected string argument")
        return value

    @staticmethod
    def _as_optional_dict(value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("expected object argument")
        return dict(value)

    @staticmethod
    def _as_projection(value: Any) -> dict[str, int] | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValueError("projection must be an object")
        normalized: dict[str, int] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or item not in (0, 1, False, True):
                raise ValueError("projection must map field names to 0/1")
            normalized[key] = int(bool(item))
        return normalized

    @staticmethod
    def _as_optional_int(value: Any) -> int | None:
        if value is None:
            return None
        if not isinstance(value, int):
            raise ValueError("expected integer argument")
        return value


def register_tools(server: Any, service: ToolService) -> None:
    async def _list_tools(_: types.ListToolsRequest) -> types.ServerResult:
        return types.ServerResult(types.ListToolsResult(tools=service.tool_definitions()))

    async def _call_tool(req: types.CallToolRequest) -> types.ServerResult:
        result = await service.dispatch(req.params.name, req.params.arguments or {})
        if isinstance(result, types.CallToolResult):
            return types.ServerResult(result)

        return types.ServerResult(
            types.CallToolResult(
                isError=False,
                content=[types.TextContent(type="text", text=json.dumps(result, indent=2))],
                structuredContent=result,
            )
        )

    server.request_handlers[types.ListToolsRequest] = _list_tools
    server.request_handlers[types.CallToolRequest] = _call_tool
