from __future__ import annotations

import re

SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

TYPE_MAP: dict[str, str] = {
    "integer": "int",
    "bigint": "int",
    "text": "str",
    "varchar": "str",
    "boolean": "bool",
    "timestamp": "datetime",
}


def normalize_backend(backend: str) -> str:
    return backend.strip().lower()


def validate_identifier(identifier: str) -> str:
    if not identifier:
        raise ValueError("identifier cannot be empty")
    if '"' in identifier or "'" in identifier or "`" in identifier:
        raise ValueError("identifier contains quotes")
    if not SAFE_IDENTIFIER_PATTERN.fullmatch(identifier):
        raise ValueError(f"unsafe identifier: {identifier}")
    return identifier


def quote_identifier(backend: str, identifier: str) -> str:
    safe = validate_identifier(identifier)
    normalized = normalize_backend(backend)
    if normalized == "mysql":
        return f"`{safe}`"
    return f'"{safe}"'


def quote_table(backend: str, table_name: str) -> str:
    parts = table_name.split(".")
    if len(parts) == 1:
        return quote_identifier(backend, parts[0])
    if len(parts) == 2:
        schema, table = parts
        return f"{quote_identifier(backend, schema)}.{quote_identifier(backend, table)}"
    raise ValueError(f"invalid table name: {table_name}")
