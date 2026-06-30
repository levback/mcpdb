from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urlparse

import mcp.types as types
from pydantic import AnyUrl

from mcpdb.db.base import Connector, OperationResult
from mcpdb.db.policy import OpClass
from mcpdb.server.context import Context, RequestContext

TABLES_TEMPLATE = "db://{profile}/tables"
SCHEMA_TEMPLATE = "db://{profile}/schema/{table}"


@dataclass(frozen=True)
class ProfileResourceBinding:
    profile: str
    backend: str
    connector: Connector


class ResourceNotFoundError(ValueError):
    """Raised when a resource URI references an unknown profile or target."""


class ResourceService:
    def __init__(self, bindings: Mapping[str, ProfileResourceBinding]) -> None:
        self._bindings = dict(bindings)

    async def list_resources(self) -> list[types.Resource]:
        resources: list[types.Resource] = []
        for binding in self._bindings.values():
            resources.append(
                types.Resource(
                    name=f"{binding.profile} tables",
                    uri=cast(AnyUrl, f"db://{binding.profile}/tables"),
                    description=f"List table/collection names for {binding.profile}",
                    mimeType="application/json",
                )
            )
        return resources

    async def list_resource_templates(self) -> list[types.ResourceTemplate]:
        return [
            types.ResourceTemplate(
                name="db tables",
                uriTemplate=TABLES_TEMPLATE,
                description="List tables or collections for a profile",
                mimeType="application/json",
            ),
            types.ResourceTemplate(
                name="db schema",
                uriTemplate=SCHEMA_TEMPLATE,
                description="Return JSON schema-like information for a table/collection",
                mimeType="application/json",
            ),
        ]

    async def read_resource(self, uri: AnyUrl) -> str:
        profile, target, table = self._parse_uri(str(uri))
        binding = self._binding(profile)
        request = RequestContext(
            principal="resource",
            source_ip="127.0.0.1",
            user_agent="mcp-resource",
        )
        context = Context(
            profile=profile,
            op_class=OpClass.READ,
            request=request,
        ).to_db_context()

        await binding.connector.connect(context)
        try:
            if target == "tables":
                result = await binding.connector.introspect(context, None)
                payload: dict[str, Any] = {
                    "profile": profile,
                    "backend": binding.backend,
                    "tables": self._extract_names(result),
                }
            elif target == "schema" and table is not None:
                introspect_target = table if binding.backend != "mongodb" else f"schema:{table}"
                result = await binding.connector.introspect(context, introspect_target)
                payload = {
                    "profile": profile,
                    "backend": binding.backend,
                    "table": table,
                    "schema": self._operation_rows(result),
                }
            else:
                raise ResourceNotFoundError(f"unknown resource target: {target}")
        finally:
            await binding.connector.close(context)

        return json.dumps(payload, sort_keys=True)

    def _binding(self, profile: str) -> ProfileResourceBinding:
        if profile not in self._bindings:
            raise ResourceNotFoundError(f"unknown profile: {profile}")
        return self._bindings[profile]

    def _parse_uri(self, raw_uri: str) -> tuple[str, str, str | None]:
        parsed = urlparse(raw_uri)
        if parsed.scheme != "db":
            raise ResourceNotFoundError("resource URI must use db:// scheme")

        profile = parsed.netloc
        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            raise ResourceNotFoundError("resource path must include a target")

        target = path_parts[0]
        table = path_parts[1] if len(path_parts) > 1 else None
        return profile, target, table

    @staticmethod
    def _extract_names(result: OperationResult) -> list[str]:
        names: list[str] = []
        for row in result.rows:
            if "table" in row:
                names.append(str(row["table"]))
            elif "collection" in row:
                names.append(str(row["collection"]))
        return names

    @staticmethod
    def _operation_rows(result: OperationResult) -> list[dict[str, object]]:
        return [dict(row) for row in result.rows]
