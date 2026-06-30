from __future__ import annotations

import pytest

from mcpdb.db.base import Context, PolicyRefused
from mcpdb.db.nosql.mongo import MongoConnector
from mcpdb.db.nosql.query import MongoFilter, MongoFilterError, MongoPipeline, QueryValidationConfig
from mcpdb.db.policy import Policy


@pytest.mark.parametrize(
    "payload",
    [
        {"name": {"$where": "this.age > 21"}},
        {"name": {"$function": {"body": "function(){}"}}},
        {"name": {"$accumulator": {"init": "function(){}"}}},
    ],
)
def test_filter_js_operators_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(MongoFilterError):
        MongoFilter.from_document(payload, config=QueryValidationConfig())


def test_aggregate_out_rejected() -> None:
    with pytest.raises(MongoFilterError):
        MongoPipeline.from_stages(
            [{"$out": "archive"}],
            config=QueryValidationConfig(),
        )


def test_aggregate_merge_rejected() -> None:
    with pytest.raises(MongoFilterError):
        MongoPipeline.from_stages(
            [{"$merge": "archive"}],
            config=QueryValidationConfig(),
        )


@pytest.mark.asyncio
async def test_policy_read_only_blocks_insert_one() -> None:
    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb",
        policy=Policy(allow_reads=True, allow_writes=False),
        profile_collections=("users",),
    )

    with pytest.raises(PolicyRefused):
        await connector.execute(
            Context(profile="mongo", request_id="sec", principal="tester"),
            "insert_one",
            {
                "collection": "users",
                "document": {"name": "blocked"},
            },
        )


@pytest.mark.asyncio
async def test_introspect_server_status_requires_admin() -> None:
    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb",
        policy=Policy(allow_reads=True, allow_admin=False),
    )

    with pytest.raises(PolicyRefused):
        await connector.introspect(
            Context(profile="mongo", request_id="sec-2", principal="tester"),
            "server_status",
        )
