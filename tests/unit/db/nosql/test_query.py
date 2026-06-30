from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from mcpdb.db.base import Context, QueryFailure
from mcpdb.db.nosql.mongo import MongoConnector
from mcpdb.db.nosql.query import (
    MongoFilter,
    MongoFilterError,
    MongoPipeline,
    QueryValidationConfig,
)
from mcpdb.db.policy import Policy


def test_filter_eq_ne_gt_translates_to_motor() -> None:
    model = MongoFilter.from_document(
        {
            "age": {"$gt": 21, "$ne": 65},
            "name": {"$eq": "alice"},
        },
        config=QueryValidationConfig(),
    )

    assert model.document["age"]["$gt"] == 21
    assert model.document["name"]["$eq"] == "alice"


def test_filter_where_is_rejected_with_clear_error() -> None:
    with pytest.raises(MongoFilterError, match="blocked"):
        MongoFilter.from_document(
            {"name": {"$where": "this.age > 1"}},
            config=QueryValidationConfig(),
        )


def test_filter_function_is_rejected() -> None:
    with pytest.raises(MongoFilterError, match="blocked"):
        MongoFilter.from_document(
            {"name": {"$function": {"body": "function(){}"}}},
            config=QueryValidationConfig(),
        )


def test_filter_regex_rejected_when_disabled() -> None:
    with pytest.raises(MongoFilterError, match="disabled"):
        MongoFilter.from_document(
            {"name": {"$regex": "^adm"}},
            config=QueryValidationConfig(regex_enabled=False),
        )


def test_filter_regex_timeout_set_when_enabled() -> None:
    model = MongoFilter.from_document(
        {"name": {"$regex": "^adm"}},
        config=QueryValidationConfig(regex_enabled=True, regex_timeout_ms=200),
    )

    assert model.uses_regex is True


def test_filter_in_nin_type_validated() -> None:
    with pytest.raises(MongoFilterError, match="requires a list"):
        MongoFilter.from_document(
            {"name": {"$in": "alice"}},
            config=QueryValidationConfig(),
        )


def test_aggregate_out_rejected() -> None:
    with pytest.raises(MongoFilterError, match="blocked"):
        MongoPipeline.from_stages(
            [{"$out": "archive"}],
            config=QueryValidationConfig(),
        )


def test_aggregate_lookup_within_same_db_allowed() -> None:
    model = MongoPipeline.from_stages(
        [
            {
                "$lookup": {
                    "from": "orders",
                    "localField": "order_id",
                    "foreignField": "_id",
                    "as": "orders",
                }
            }
        ],
        config=QueryValidationConfig(allowed_collections=("orders", "users")),
    )

    assert model.stages[0]["$lookup"]["from"] == "orders"


def test_aggregate_lookup_cross_db_rejected() -> None:
    with pytest.raises(MongoFilterError, match="cross-database"):
        MongoPipeline.from_stages(
            [{"$lookup": {"from": "otherdb.orders", "as": "orders"}}],
            config=QueryValidationConfig(),
        )


@dataclass
class FakeCursor:
    docs: list[dict[str, Any]]

    async def to_list(self, length: int) -> list[dict[str, Any]]:
        return list(self.docs)[:length]


class FakeCollection:
    def __init__(self) -> None:
        self.docs: list[dict[str, Any]] = []

    def find(
        self,
        filter_doc: dict[str, Any],
        *,
        projection: dict[str, int] | None,
        limit: int,
        max_time_ms: int,
    ) -> FakeCursor:
        filtered = [doc for doc in self.docs if _matches(doc, filter_doc)]
        if projection is not None:
            projected: list[dict[str, Any]] = []
            for doc in filtered:
                projected.append(
                    {key: value for key, value in doc.items() if projection.get(key, 0) == 1}
                )
            filtered = projected
        return FakeCursor(filtered[:limit])

    def aggregate(self, pipeline: list[dict[str, Any]], **kwargs: Any) -> FakeCursor:
        docs = list(self.docs)
        for stage in pipeline:
            if "$match" in stage:
                docs = [doc for doc in docs if _matches(doc, stage["$match"])]
            if "$limit" in stage:
                docs = docs[: int(stage["$limit"])]
        return FakeCursor(docs)

    async def insert_one(self, document: dict[str, Any]) -> SimpleNamespace:
        stored = dict(document)
        stored.setdefault("_id", f"id-{len(self.docs) + 1}")
        self.docs.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    async def find_one(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        return self.docs[0] if self.docs else None

    async def index_information(self) -> dict[str, dict[str, Any]]:
        return {"_id_": {"key": [("_id", 1)]}}

    async def estimated_document_count(self, **kwargs: Any) -> int:
        return len(self.docs)


class FakeDatabase:
    def __init__(self) -> None:
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, collection_name: str) -> FakeCollection:
        if collection_name not in self.collections:
            self.collections[collection_name] = FakeCollection()
        return self.collections[collection_name]

    async def command(self, name: str) -> dict[str, Any]:
        if name == "ping":
            return {"ok": 1}
        if name == "serverStatus":
            return {"ok": 1, "uptime": 10, "version": "7.0"}
        return {"ok": 0}

    async def list_collection_names(self) -> list[str]:
        return sorted(self.collections.keys())


class FakeClient:
    async def list_database_names(self) -> list[str]:
        return ["admin", "mcpdb_test"]

    def close(self) -> None:
        return None


def _matches(document: dict[str, Any], filter_doc: dict[str, Any]) -> bool:
    for field, clause in filter_doc.items():
        if not isinstance(clause, dict):
            if document.get(field) != clause:
                return False
            continue

        for op, value in clause.items():
            current = document.get(field)
            if op == "$eq" and current != value:
                return False
            if op == "$ne" and current == value:
                return False
            if op == "$gt" and (current is None or current <= value):
                return False
    return True


@pytest.mark.asyncio
async def test_mongo_connector_execute_find_aggregate_and_insert() -> None:
    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb_test",
        policy=Policy(allow_reads=True, allow_writes=True),
        profile_collections=("users",),
    )
    connector._database = FakeDatabase()
    connector._client = FakeClient()
    context = Context(profile="mongo", request_id="u-1", principal="tester")

    inserted = await connector.execute(
        context,
        "insert_one",
        {
            "collection": "users",
            "document": {"name": "alice", "age": 34},
        },
    )
    found = await connector.execute(
        context,
        "find",
        {
            "collection": "users",
            "filter": {"name": {"$eq": "alice"}},
            "projection": {"name": 1},
            "limit": 5,
        },
    )
    aggregated = await connector.execute(
        context,
        "aggregate",
        {
            "collection": "users",
            "pipeline": [{"$match": {"name": {"$eq": "alice"}}}, {"$limit": 1}],
            "limit": 5,
        },
    )

    assert inserted.row_count == 1
    assert found.row_count == 1
    assert found.rows[0]["name"] == "alice"
    assert aggregated.row_count == 1


@pytest.mark.asyncio
async def test_mongo_connector_introspect_views() -> None:
    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb_test",
        policy=Policy(allow_reads=True, allow_admin=True),
        profile_collections=("users",),
    )
    connector._database = FakeDatabase()
    connector._client = FakeClient()
    connector._database.collections["users"] = FakeCollection()
    await connector._database.collections["users"].insert_one({"name": "alice", "age": 40})
    context = Context(profile="mongo", request_id="u-2", principal="tester")

    overview = await connector.introspect(context)
    collections = await connector.introspect(context, "collections")
    schema = await connector.introspect(context, "schema:users")
    indexes = await connector.introspect(context, "indexes:users")
    stats = await connector.introspect(context, "stats:users")
    status = await connector.introspect(context, "server_status")

    assert overview.row_count == 1
    assert collections.row_count == 1
    assert schema.rows[0]["fields"]["name"] == "str"
    assert indexes.row_count == 1
    assert stats.rows[0]["estimated_document_count"] == 1
    assert status.rows[0]["ok"] == 1


@pytest.mark.asyncio
async def test_mongo_connector_error_paths() -> None:
    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb_test",
        policy=Policy(allow_reads=True, allow_writes=False),
        profile_collections=("users",),
    )
    connector._database = FakeDatabase()
    connector._client = FakeClient()
    context = Context(profile="mongo", request_id="u-3", principal="tester")

    with pytest.raises(QueryFailure, match="unknown operation class"):
        await connector.execute(context, "unknown")

    with pytest.raises(MongoFilterError, match="projection"):
        await connector.execute(
            context,
            "find",
            {"collection": "users", "projection": {"name": 2}},
        )

    with pytest.raises(MongoFilterError, match="limit"):
        await connector.execute(
            context,
            "find",
            {"collection": "users", "limit": 0},
        )

    with pytest.raises(QueryFailure, match="unknown introspection"):
        await connector.introspect(context, "unknown")


def test_filter_top_level_operator_rejected() -> None:
    with pytest.raises(MongoFilterError, match="top-level operator"):
        MongoFilter.from_document(
            {"$gt": {"age": 1}},
            config=QueryValidationConfig(),
        )


def test_filter_and_or_shape_validated() -> None:
    with pytest.raises(MongoFilterError, match="non-empty list"):
        MongoFilter.from_document(
            {"$and": []},
            config=QueryValidationConfig(),
        )

    with pytest.raises(MongoFilterError, match="entries must be documents"):
        MongoFilter.from_document(
            {"$or": ["bad-entry"]},
            config=QueryValidationConfig(),
        )


def test_filter_regex_validation_errors() -> None:
    with pytest.raises(MongoFilterError, match="positive regex_timeout_ms"):
        MongoFilter.from_document(
            {"name": {"$regex": "^adm"}},
            config=QueryValidationConfig(regex_enabled=True, regex_timeout_ms=0),
        )

    with pytest.raises(MongoFilterError, match="literal string"):
        MongoFilter.from_document(
            {"name": {"$regex": ["bad"]}},
            config=QueryValidationConfig(regex_enabled=True),
        )

    with pytest.raises(MongoFilterError, match="invalid"):
        MongoFilter.from_document(
            {"name": {"$regex": "["}},
            config=QueryValidationConfig(regex_enabled=True),
        )

    with pytest.raises(MongoFilterError, match="maximum length"):
        MongoFilter.from_document(
            {"name": {"$regex": "a" * 400}},
            config=QueryValidationConfig(regex_enabled=True),
        )


def test_filter_exists_validation_errors() -> None:
    with pytest.raises(MongoFilterError, match="boolean"):
        MongoFilter.from_document(
            {"active": {"$exists": "yes"}},
            config=QueryValidationConfig(),
        )


def test_pipeline_validation_errors() -> None:
    with pytest.raises(MongoFilterError, match="exactly one operator"):
        MongoPipeline.from_stages(
            [{"$match": {}, "$limit": 1}],
            config=QueryValidationConfig(),
        )

    with pytest.raises(MongoFilterError, match="not allow-listed"):
        MongoPipeline.from_stages(
            [{"$facet": {}}],
            config=QueryValidationConfig(),
        )

    with pytest.raises(MongoFilterError, match="expects a document"):
        MongoPipeline.from_stages(
            [{"$match": "bad"}],
            config=QueryValidationConfig(),
        )

    with pytest.raises(MongoFilterError, match="expects an object"):
        MongoPipeline.from_stages(
            [{"$lookup": "bad"}],
            config=QueryValidationConfig(),
        )

    with pytest.raises(MongoFilterError, match="non-empty collection"):
        MongoPipeline.from_stages(
            [{"$lookup": {"from": "", "as": "items"}}],
            config=QueryValidationConfig(),
        )

    with pytest.raises(MongoFilterError, match="outside profile scope"):
        MongoPipeline.from_stages(
            [{"$lookup": {"from": "orders", "as": "items"}}],
            config=QueryValidationConfig(allowed_collections=("users",)),
        )


@pytest.mark.asyncio
async def test_mongo_connector_lifecycle_with_patched_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_db = FakeDatabase()

    class PatchedClient:
        def __init__(self, uri: str, **kwargs: Any) -> None:
            self.uri = uri
            self.server_selection_timeout_ms = int(kwargs["serverSelectionTimeoutMS"])
            self.closed = False

        def __getitem__(self, db_name: str) -> FakeDatabase:
            return fake_db

        async def list_database_names(self) -> list[str]:
            return ["mcpdb_test"]

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr("mcpdb.db.nosql.mongo.AsyncIOMotorClient", PatchedClient)

    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb_test",
        policy=Policy(allow_reads=True),
    )
    context = Context(profile="mongo", request_id="u-4", principal="tester")

    await connector.connect(context)
    latency_ms = await connector.ping(context)
    await connector.close(context)

    assert latency_ms >= 0
    assert connector._client is None


@pytest.mark.asyncio
async def test_mongo_connector_helper_error_branches() -> None:
    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb_test",
        policy=Policy(allow_reads=True),
        profile_collections=("users",),
    )

    with pytest.raises(QueryFailure, match="not connected"):
        connector._require_client()

    with pytest.raises(QueryFailure, match="not connected"):
        connector._require_database()

    connector._database = FakeDatabase()
    connector._client = FakeClient()

    with pytest.raises(MongoFilterError, match="collection is required"):
        connector._get_collection({})

    with pytest.raises(MongoFilterError, match="outside profile scope"):
        connector._collection("orders")

    with pytest.raises(MongoFilterError, match="projection must be"):
        connector._validate_projection("bad")

    with pytest.raises(MongoFilterError, match="non-empty strings"):
        connector._validate_projection({"": 1})

    assert connector._validate_projection({"name": True}) == {"name": 1}
    assert connector._resolve_limit(None) == connector._policy.max_rows

    with pytest.raises(MongoFilterError, match="positive integer"):
        connector._resolve_limit(-1)

    with pytest.raises(QueryFailure, match="unknown operation class"):
        connector._detect_op_class("something-else")

    assert connector._normalize_document({"x": 1}) == {"x": 1}


@pytest.mark.asyncio
async def test_mongo_connector_transaction_and_insert_validation() -> None:
    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb_test",
        policy=Policy(allow_reads=True, allow_writes=True),
        profile_collections=("users",),
    )
    connector._database = FakeDatabase()
    connector._client = FakeClient()
    context = Context(profile="mongo", request_id="u-5", principal="tester")

    with pytest.raises(QueryFailure, match="out of scope"):
        await connector.transaction(context)

    with pytest.raises(MongoFilterError, match="document object"):
        await connector.execute(
            context,
            "insert_one",
            {"collection": "users", "document": "bad"},
        )


@pytest.mark.asyncio
async def test_mongo_connector_sample_schema_empty_collection() -> None:
    connector = MongoConnector(
        uri="mongodb://localhost:27017",
        database="mcpdb_test",
        policy=Policy(allow_reads=True),
        profile_collections=("users",),
    )
    connector._database = FakeDatabase()
    connector._client = FakeClient()

    result = await connector._sample_schema("users")

    assert result == {"collection": "users", "fields": {}}


def test_mongo_uri_security_rules() -> None:
    direct = MongoConnector(
        uri="mongodb://example.com:27017/?directConnection=true",
        database="mcpdb_test",
        policy=Policy(allow_reads=True),
    )
    with pytest.raises(QueryFailure, match="directConnection=true"):
        direct._enforce_uri_security()

    srv = MongoConnector(
        uri="mongodb+srv://cluster.example.com/mcpdb_test",
        database="mcpdb_test",
        policy=Policy(allow_reads=True),
        srv_resolved=False,
    )
    with pytest.raises(QueryFailure, match="pre-resolved"):
        srv._enforce_uri_security()

    localhost = MongoConnector(
        uri="mongodb://localhost:27017/?directConnection=true",
        database="mcpdb_test",
        policy=Policy(allow_reads=True),
    )
    localhost._enforce_uri_security()
