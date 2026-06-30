from __future__ import annotations

import json

import pytest

from mcpdb.db.base import Context as DbContext
from mcpdb.db.base import OperationResult
from mcpdb.db.fake import FakeConnector
from mcpdb.server.resources import ProfileResourceBinding, ResourceNotFoundError, ResourceService


class FakeResourceConnector(FakeConnector):
    async def introspect(self, context: DbContext, target: str | None = None) -> OperationResult:
        if target is None:
            return OperationResult(rows=({"table": "users"}, {"table": "orders"}), row_count=2)
        if target.startswith("schema:"):
            return OperationResult(rows=({"field": "name", "type": "string"},), row_count=1)
        return OperationResult(rows=({"column": "id", "type": "integer"},), row_count=1)


@pytest.mark.asyncio
async def test_resources_db_tables_lists_table_names() -> None:
    service = ResourceService(
        {
            "main": ProfileResourceBinding(
                profile="main",
                backend="postgres",
                connector=FakeResourceConnector(),
            )
        }
    )

    payload = await service.read_resource("db://main/tables")
    parsed = json.loads(payload)

    assert parsed["tables"] == ["users", "orders"]


@pytest.mark.asyncio
async def test_resources_db_schema_returns_json_schema() -> None:
    service = ResourceService(
        {
            "mongo": ProfileResourceBinding(
                profile="mongo",
                backend="mongodb",
                connector=FakeResourceConnector(),
            )
        }
    )

    payload = await service.read_resource("db://mongo/schema/users")
    parsed = json.loads(payload)

    assert parsed["table"] == "users"
    assert parsed["schema"][0]["field"] == "name"


@pytest.mark.asyncio
async def test_resources_invalid_profile_returns_not_found() -> None:
    service = ResourceService({})

    with pytest.raises(ResourceNotFoundError):
        await service.read_resource("db://missing/tables")


@pytest.mark.asyncio
async def test_resources_templates_and_listing() -> None:
    service = ResourceService(
        {
            "main": ProfileResourceBinding(
                profile="main",
                backend="sqlite",
                connector=FakeResourceConnector(),
            )
        }
    )

    resources = await service.list_resources()
    templates = await service.list_resource_templates()

    assert str(resources[0].uri) == "db://main/tables"
    assert len(templates) == 2
