from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Mapping
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs, urlparse

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

from mcpdb.db.base import Connector, Context, OperationResult, PolicyRefused, QueryFailure
from mcpdb.db.nosql.query import MongoFilter, MongoFilterError, MongoPipeline, QueryValidationConfig
from mcpdb.db.policy import OpClass, Policy

LOGGER = logging.getLogger(__name__)


class MongoConnector(Connector):
    backend = "mongodb"

    def __init__(
        self,
        *,
        uri: str,
        database: str,
        policy: Policy,
        profile_collections: tuple[str, ...] | None = None,
        regex_enabled: bool = False,
        regex_timeout_ms: int = 1_000,
        srv_resolved: bool = False,
    ) -> None:
        self._uri = uri
        self._database_name = database
        self._policy = policy
        self._profile_collections = profile_collections
        self._config = QueryValidationConfig(
            regex_enabled=regex_enabled,
            regex_timeout_ms=regex_timeout_ms,
            allowed_collections=profile_collections,
        )
        self._srv_resolved = srv_resolved
        self._client: AsyncIOMotorClient[Any] | None = None
        self._database: AsyncIOMotorDatabase[Any] | None = None

    async def connect(self, context: Context) -> None:
        self._enforce_uri_security()
        self._client = AsyncIOMotorClient(
            self._uri,
            serverSelectionTimeoutMS=self._policy.query_timeout_ms,
        )
        self._database = self._client[self._database_name]
        await self._database.command("ping")

    async def close(self, context: Context) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._database = None

    async def ping(self, context: Context) -> float:
        db = self._require_database()
        started = perf_counter()
        await db.command("ping")
        return (perf_counter() - started) * 1000

    async def execute(
        self,
        context: Context,
        statement: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> OperationResult:
        op_class = self._detect_op_class(statement)
        decision = self._policy.decide(op_class)
        if not decision.allowed:
            raise PolicyRefused(decision.reason)  # OWASP A01: default deny by Policy

        payload = dict(parameters or {})
        fingerprint = self._fingerprint(statement, payload)
        LOGGER.info("mongo_execute fingerprint=%s", fingerprint)  # NIST AU-3: fingerprint only

        started = perf_counter()
        if statement == "find":
            result = await self._run_find(payload)
        elif statement == "aggregate":
            result = await self._run_aggregate(payload)
        elif statement == "insert_one":
            result = await self._run_insert_one(payload)
        elif statement == "server_status":
            if op_class is not OpClass.ADMIN:
                raise QueryFailure("server_status requires ADMIN operation class")
            stats = await self._require_database().command("serverStatus")
            result = [{"ok": stats.get("ok", 0), "version": stats.get("version")}]
        else:
            raise QueryFailure(f"unknown Mongo statement: {statement}")

        latency_ms = (perf_counter() - started) * 1000
        rows = self._apply_row_cap(result)
        payload_bytes = len(json.dumps(rows, default=str, sort_keys=True))
        return OperationResult(
            rows=tuple(rows),
            row_count=len(result),
            payload_bytes=payload_bytes,
            latency_ms=latency_ms,
            truncated=len(rows) < len(result),
        )

    async def introspect(self, context: Context, target: str | None = None) -> OperationResult:
        if target == "server_status":
            decision = self._policy.decide(OpClass.ADMIN)
            if not decision.allowed:
                raise PolicyRefused(decision.reason)

        db = self._require_database()

        if target is None:
            rows = await self._introspect_overview()
        elif target == "collections":
            names = await db.list_collection_names()
            rows = [{"collection": name} for name in names]
        elif target.startswith("schema:"):
            rows = [await self._sample_schema(target.removeprefix("schema:"))]
        elif target.startswith("indexes:"):
            rows = await self._list_indexes(target.removeprefix("indexes:"))
        elif target.startswith("stats:"):
            rows = [await self._collection_stats(target.removeprefix("stats:"))]
        elif target == "server_status":
            stats = await db.command("serverStatus")
            rows = [{"ok": stats.get("ok", 0), "uptime": stats.get("uptime", 0)}]
        else:
            raise QueryFailure(f"unknown introspection target: {target}")

        payload_bytes = len(json.dumps(rows, default=str, sort_keys=True))
        return OperationResult(rows=tuple(rows), row_count=len(rows), payload_bytes=payload_bytes)

    async def transaction(self, context: Context) -> None:
        raise QueryFailure("Mongo transactions are out of scope for this phase")

    async def _run_find(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        collection = self._get_collection(payload)
        mongo_filter = MongoFilter.from_document(payload.get("filter"), config=self._config)
        projection = self._validate_projection(payload.get("projection"))
        limit = self._resolve_limit(payload.get("limit"))

        cursor = collection.find(
            mongo_filter.document,
            projection=projection,
            limit=limit,
            max_time_ms=self._policy.query_timeout_ms,
        )
        docs = await cursor.to_list(length=limit)
        return [self._normalize_document(doc) for doc in docs]

    async def _run_aggregate(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        collection = self._get_collection(payload)
        pipeline = MongoPipeline.from_stages(payload.get("pipeline"), config=self._config)
        limit = self._resolve_limit(payload.get("limit"))

        cursor = collection.aggregate(
            list(pipeline.stages),
            maxTimeMS=self._policy.query_timeout_ms,
        )
        docs = await cursor.to_list(length=limit)
        return [self._normalize_document(doc) for doc in docs]

    async def _run_insert_one(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        collection = self._get_collection(payload)
        document = payload.get("document")
        if not isinstance(document, dict):
            raise MongoFilterError("insert_one requires a document object")
        result = await collection.insert_one(document)
        return [{"inserted_id": str(result.inserted_id)}]

    async def _introspect_overview(self) -> list[dict[str, Any]]:
        client = self._require_client()
        db = self._require_database()
        databases = await client.list_database_names()
        collections = await db.list_collection_names()
        return [{"databases": databases, "collections": collections}]

    async def _sample_schema(self, collection_name: str) -> dict[str, Any]:
        collection = self._collection(collection_name)
        sample = await collection.find_one({}, max_time_ms=self._policy.query_timeout_ms)
        if sample is None:
            return {"collection": collection_name, "fields": {}}
        fields = {key: type(value).__name__ for key, value in sample.items()}
        return {"collection": collection_name, "fields": fields}

    async def _list_indexes(self, collection_name: str) -> list[dict[str, Any]]:
        collection = self._collection(collection_name)
        index_info = await collection.index_information()
        return [
            {"collection": collection_name, "index": name, "spec": spec}
            for name, spec in index_info.items()
        ]

    async def _collection_stats(self, collection_name: str) -> dict[str, Any]:
        collection = self._collection(collection_name)
        count = await collection.estimated_document_count(
            maxTimeMS=self._policy.query_timeout_ms,
        )
        return {"collection": collection_name, "estimated_document_count": count}

    def _detect_op_class(self, statement: str) -> OpClass:
        normalized = statement.strip().lower()
        if normalized in {"find", "aggregate"}:
            return OpClass.READ
        if normalized in {"insert_one", "update_one", "delete_one"}:
            return OpClass.WRITE
        if normalized in {"server_status"}:
            return OpClass.ADMIN
        raise QueryFailure(f"unknown operation class for statement: {statement}")

    def _get_collection(self, payload: dict[str, Any]) -> AsyncIOMotorCollection[Any]:
        collection = payload.get("collection")
        if not isinstance(collection, str) or not collection:
            raise MongoFilterError("collection is required")
        return self._collection(collection)

    def _collection(self, collection_name: str) -> AsyncIOMotorCollection[Any]:
        if (
            self._profile_collections is not None
            and collection_name not in self._profile_collections
        ):
            raise MongoFilterError("collection is outside profile scope")  # OWASP A03
        return self._require_database()[collection_name]

    def _validate_projection(self, projection: Any) -> dict[str, int] | None:
        if projection is None:
            return None
        if not isinstance(projection, dict):
            raise MongoFilterError("projection must be a document")

        normalized: dict[str, int] = {}
        for field, value in projection.items():
            if not isinstance(field, str) or not field:
                raise MongoFilterError("projection field names must be non-empty strings")
            if value not in (0, 1, False, True):
                raise MongoFilterError("projection values must be 0/1")
            normalized[field] = int(bool(value))
        return normalized

    def _resolve_limit(self, limit: Any) -> int:
        if limit is None:
            return self._policy.max_rows
        if not isinstance(limit, int) or limit <= 0:
            raise MongoFilterError("limit must be a positive integer")
        return min(limit, self._policy.max_rows)

    def _apply_row_cap(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return rows[: self._policy.max_rows]

    def _normalize_document(self, document: Mapping[str, Any]) -> dict[str, Any]:
        normalized = dict(document)
        if "_id" in normalized:
            normalized["_id"] = str(normalized["_id"])
        return normalized

    def _fingerprint(self, statement: str, payload: dict[str, Any]) -> str:
        canonical = json.dumps(
            {"statement": statement, "payload_keys": sorted(payload.keys())},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _enforce_uri_security(self) -> None:
        parsed = urlparse(self._uri)
        if parsed.scheme == "mongodb+srv" and not self._srv_resolved:
            raise QueryFailure("mongodb+srv requires pre-resolved DNS allow-list")  # OWASP A10

        query = parse_qs(parsed.query)
        direct = query.get("directConnection", ["false"])[0].lower() == "true"
        if direct:
            host = (parsed.hostname or "").lower()
            is_loopback = host in {"localhost", "127.0.0.1", "::1"} or host.startswith("127.")
            if not is_loopback:
                raise QueryFailure(
                    "directConnection=true is only allowed for loopback hosts"
                )  # OWASP A05

    def _require_client(self) -> AsyncIOMotorClient[Any]:
        if self._client is None:
            raise QueryFailure("Mongo connector is not connected")
        return self._client

    def _require_database(self) -> AsyncIOMotorDatabase[Any]:
        if self._database is None:
            raise QueryFailure("Mongo connector is not connected")
        return self._database
