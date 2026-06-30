from __future__ import annotations

import mcp.types as types
import pytest
from pydantic import SecretStr
from starlette.testclient import TestClient

from mcpdb.config.models import McpDbSettings, Profile, Security
from mcpdb.db.fake import FakeConnector
from mcpdb.server import app as app_module
from mcpdb.server.app import build_http_app, build_server, select_transport


def test_integration_http_starts_and_responds_health() -> None:
    settings = McpDbSettings(
        profiles=[
            Profile(
                name="main",
                backend="sqlite",
                dsn=SecretStr("sqlite+aiosqlite:///:memory:"),
            )
        ],
        security=Security(auth_enabled=True),
    )
    server = build_server(settings)
    app = build_http_app(settings, server)

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_integration_http_select_transport_requires_auth() -> None:
    settings = McpDbSettings(
        profiles=[
            Profile(
                name="main",
                backend="sqlite",
                dsn=SecretStr("sqlite+aiosqlite:///:memory:"),
            )
        ]
    )

    with pytest.raises(ValueError, match="auth_enabled"):
        select_transport(settings, requested="http")


def test_integration_http_select_transport_defaults_stdio() -> None:
    settings = McpDbSettings(
        profiles=[
            Profile(
                name="main",
                backend="sqlite",
                dsn=SecretStr("sqlite+aiosqlite:///:memory:"),
            )
        ]
    )

    assert select_transport(settings) == "stdio"


def test_integration_http_select_transport_invalid_value() -> None:
    settings = McpDbSettings(
        profiles=[
            Profile(
                name="main",
                backend="sqlite",
                dsn=SecretStr("sqlite+aiosqlite:///:memory:"),
            )
        ],
        security=Security(auth_enabled=True),
    )

    with pytest.raises(ValueError, match="unsupported transport"):
        select_transport(settings, requested="ws")


def test_app_private_helpers_dsn_policy_and_ports() -> None:
    settings = McpDbSettings(
        profiles=[
            Profile(
                name="rw",
                backend="postgres",
                mode="read_write",
                allow_writes=True,
                dsn=SecretStr("postgresql+asyncpg://localhost/test"),
            )
        ]
    )

    policy = app_module._build_policy(settings.profiles[0], settings)
    assert policy.allow_reads is True
    assert policy.allow_writes is True
    assert app_module._default_port("postgres") == 5432
    assert app_module._default_port("mysql") == 3306
    assert app_module._default_port("mongodb") == 27017
    assert app_module._default_port("other") == 0


def test_app_private_profile_dsn_for_discrete_profiles() -> None:
    postgres = Profile(name="p", backend="postgres", host="db", database="app")
    mysql = Profile(name="m", backend="mysql", host="db", database="app")
    sqlite = Profile(name="s", backend="sqlite", host="unused", database="local.db")
    mongo = Profile(name="g", backend="mongodb", host="db", database="app")

    assert app_module._profile_dsn(postgres).startswith("postgresql+asyncpg://db:5432/")
    assert app_module._profile_dsn(mysql).startswith("mysql+aiomysql://db:3306/")
    assert app_module._profile_dsn(sqlite) == "sqlite+aiosqlite:///local.db"
    assert app_module._profile_dsn(mongo).startswith("mongodb://db:27017/")


def test_app_build_connector_rejects_unknown_backend() -> None:
    unknown_profile = type(
        "ProfileLike",
        (),
        {
            "name": "u",
            "backend": "unknown",
            "dsn": SecretStr("x"),
            "host": None,
            "database": None,
        },
    )()

    with pytest.raises(ValueError, match="unsupported backend"):
        app_module._build_connector(unknown_profile)


@pytest.mark.asyncio
async def test_app_build_server_registers_resource_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        app_module,
        "_build_connector",
        lambda profile: FakeConnector(latency_ms=0.1),
    )

    settings = McpDbSettings(
        profiles=[
            Profile(
                name="main",
                backend="sqlite",
                dsn=SecretStr("sqlite+aiosqlite:///:memory:"),
            )
        ]
    )
    server = build_server(settings)

    list_handler = server.request_handlers[types.ListResourcesRequest]
    templates_handler = server.request_handlers[types.ListResourceTemplatesRequest]
    read_handler = server.request_handlers[types.ReadResourceRequest]

    list_result = await list_handler(types.ListResourcesRequest())
    template_result = await templates_handler(types.ListResourceTemplatesRequest())
    read_result = await read_handler(
        types.ReadResourceRequest(params=types.ReadResourceRequestParams(uri="db://main/tables"))
    )

    assert len(list_result.root.resources) == 1
    assert len(template_result.root.resourceTemplates) == 2
    assert read_result.root.contents[0].mimeType == "application/json"


@pytest.mark.skip(
    reason="Phase 07 adds enforced auth middleware for unauthenticated HTTP rejections"
)
def test_integration_http_rejects_request_without_auth_after_phase07() -> None:
    assert True
