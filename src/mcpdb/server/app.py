from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import mcp.types as types
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from mcpdb.config.models import McpDbSettings, Profile
from mcpdb.db.nosql.mongo import MongoConnector
from mcpdb.db.policy import Policy
from mcpdb.db.sql.mysql import MysqlConnector
from mcpdb.db.sql.postgres import PostgresConnector
from mcpdb.db.sql.sqlite import SqliteConnector
from mcpdb.server.resources import ProfileResourceBinding, ResourceService
from mcpdb.server.tools import ProfileToolBinding, ToolService, register_tools


@dataclass(frozen=True)
class BuiltServer:
    server: Server[Any, Any]
    tool_service: ToolService
    resource_service: ResourceService


def build_server(settings: McpDbSettings) -> Server[Any, Any]:
    built = build_server_components(settings)
    server = built.server

    async def _list_resources(_: types.ListResourcesRequest) -> types.ServerResult:
        resources = await built.resource_service.list_resources()
        return types.ServerResult(types.ListResourcesResult(resources=resources))

    async def _list_resource_templates(_: types.ListResourceTemplatesRequest) -> types.ServerResult:
        templates = await built.resource_service.list_resource_templates()
        return types.ServerResult(types.ListResourceTemplatesResult(resourceTemplates=templates))

    async def _read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
        payload = await built.resource_service.read_resource(req.params.uri)
        contents: list[types.TextResourceContents | types.BlobResourceContents] = [
            types.TextResourceContents(
                uri=req.params.uri,
                text=payload,
                mimeType="application/json",
            )
        ]
        return types.ServerResult(types.ReadResourceResult(contents=contents))

    server.request_handlers[types.ListResourcesRequest] = _list_resources
    server.request_handlers[types.ListResourceTemplatesRequest] = _list_resource_templates
    server.request_handlers[types.ReadResourceRequest] = _read_resource
    return server


def build_server_components(settings: McpDbSettings) -> BuiltServer:
    bindings: dict[str, ProfileToolBinding] = {}
    resource_bindings: dict[str, ProfileResourceBinding] = {}

    for profile in settings.profiles:
        connector = _build_connector(profile)
        policy = _build_policy(profile, settings)
        tool_binding = ProfileToolBinding(
            profile=profile.name,
            backend=profile.backend,
            connector=connector,
            policy=policy,
        )
        bindings[profile.name] = tool_binding
        resource_bindings[profile.name] = ProfileResourceBinding(
            profile=profile.name,
            backend=profile.backend,
            connector=connector,
        )

    server = Server(name="mcpdb", version="0.1.0")
    tool_service = ToolService(bindings)
    resource_service = ResourceService(resource_bindings)
    register_tools(server, tool_service)

    return BuiltServer(server=server, tool_service=tool_service, resource_service=resource_service)


def select_transport(settings: McpDbSettings, requested: str | None = None) -> str:
    transport = requested or settings.mcp.transport or "stdio"
    if transport == "http" and not settings.security.auth_enabled:
        raise ValueError("http transport requires security.auth_enabled=true")
    if transport not in {"stdio", "http"}:
        raise ValueError(f"unsupported transport: {transport}")
    return transport


def build_http_app(settings: McpDbSettings, server: Server[Any, Any]) -> Starlette:
    manager = StreamableHTTPSessionManager(server, stateless=False)

    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    async def mcp_asgi(scope: Scope, receive: Receive, send: Send) -> None:
        await manager.handle_request(scope, receive, send)

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        async with manager.run():
            yield

    return Starlette(
        routes=[
            Route("/healthz", endpoint=healthz, methods=["GET"]),
            Mount("/mcp", app=mcp_asgi),
            Route("/", endpoint=lambda _: PlainTextResponse("mcpdb"), methods=["GET"]),
        ],
        lifespan=lifespan,
    )


def _build_policy(profile: Profile, settings: McpDbSettings) -> Policy:
    return Policy(
        query_timeout_ms=settings.limits.query_timeout_ms,
        max_rows=settings.limits.max_rows,
        max_payload_bytes=settings.limits.max_payload_bytes,
        allow_reads=True,
        allow_writes=profile.allow_writes and profile.mode == "read_write",
        allow_admin=False,
    )


def _build_connector(profile: Profile) -> Any:
    dsn = _profile_dsn(profile)
    policy = Policy(allow_reads=True)

    if profile.backend == "postgres":
        return PostgresConnector(dsn=dsn, policy=policy)
    if profile.backend == "mysql":
        return MysqlConnector(dsn=dsn, policy=policy)
    if profile.backend == "sqlite":
        return SqliteConnector(dsn=dsn, policy=policy)
    if profile.backend == "mongodb":
        database = profile.database or "admin"
        return MongoConnector(uri=dsn, database=database, policy=policy)

    raise ValueError(f"unsupported backend: {profile.backend}")


def _profile_dsn(profile: Profile) -> str:
    if profile.dsn is not None:
        return profile.dsn.get_secret_value()

    if profile.host is None or profile.database is None:
        raise ValueError(f"profile '{profile.name}' is missing dsn or host/database")

    port = profile.port or _default_port(profile.backend)
    if profile.backend == "postgres":
        return f"postgresql+asyncpg://{profile.host}:{port}/{profile.database}"
    if profile.backend == "mysql":
        return f"mysql+aiomysql://{profile.host}:{port}/{profile.database}"
    if profile.backend == "sqlite":
        return f"sqlite+aiosqlite:///{profile.database}"
    if profile.backend == "mongodb":
        return f"mongodb://{profile.host}:{port}/{profile.database}"

    raise ValueError(f"unsupported backend: {profile.backend}")


def _default_port(backend: str) -> int:
    if backend == "postgres":
        return 5432
    if backend == "mysql":
        return 3306
    if backend == "mongodb":
        return 27017
    return 0
