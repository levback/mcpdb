from __future__ import annotations

import os

import pytest

from mcpdb.db.base import Context
from mcpdb.db.nosql.mongo import MongoConnector
from mcpdb.db.policy import Policy


@pytest.mark.asyncio
async def test_mongo_integration_insert_find() -> None:
    uri = os.getenv("MCPDB_TEST_MONGO_URI")
    if not uri:
        pytest.skip("MCPDB_TEST_MONGO_URI is not configured")

    connector = MongoConnector(
        uri=uri,
        database="mcpdb_it",
        policy=Policy(allow_reads=True, allow_writes=True),
        profile_collections=("users",),
    )
    context = Context(profile="mongo", request_id="it-mongo-1", principal="integration")

    await connector.connect(context)
    await connector.execute(
        context,
        "insert_one",
        {
            "collection": "users",
            "document": {"name": "alice", "age": 33},
        },
    )
    result = await connector.execute(
        context,
        "find",
        {
            "collection": "users",
            "filter": {"name": {"$eq": "alice"}},
            "limit": 5,
        },
    )
    await connector.close(context)

    assert result.row_count >= 1
    assert any(row.get("name") == "alice" for row in result.rows)


@pytest.mark.asyncio
async def test_mongo_integration_aggregation_pipeline() -> None:
    uri = os.getenv("MCPDB_TEST_MONGO_URI")
    if not uri:
        pytest.skip("MCPDB_TEST_MONGO_URI is not configured")

    connector = MongoConnector(
        uri=uri,
        database="mcpdb_it",
        policy=Policy(allow_reads=True, allow_writes=True),
        profile_collections=("orders",),
    )
    context = Context(profile="mongo", request_id="it-mongo-2", principal="integration")

    await connector.connect(context)
    await connector.execute(
        context,
        "insert_one",
        {
            "collection": "orders",
            "document": {"kind": "book", "qty": 2},
        },
    )
    result = await connector.execute(
        context,
        "aggregate",
        {
            "collection": "orders",
            "pipeline": [{"$match": {"kind": {"$eq": "book"}}}, {"$limit": 5}],
            "limit": 5,
        },
    )
    await connector.close(context)

    assert result.row_count >= 1
    assert all(row.get("kind") == "book" for row in result.rows)
