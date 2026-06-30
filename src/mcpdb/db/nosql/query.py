from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

ALLOWED_FILTER_OPERATORS = {
    "$eq",
    "$ne",
    "$gt",
    "$gte",
    "$lt",
    "$lte",
    "$in",
    "$nin",
    "$and",
    "$or",
    "$exists",
    "$type",
    "$all",
    "$regex",
}
BLOCKED_JS_OPERATORS = {"$where", "$function", "$accumulator"}
ALLOWED_PIPELINE_STAGES = {
    "$match",
    "$project",
    "$sort",
    "$limit",
    "$skip",
    "$group",
    "$unwind",
    "$lookup",
    "$count",
    "$addFields",
}
BLOCKED_PIPELINE_STAGES = {"$out", "$merge"}


class MongoFilterError(ValueError):
    """Raised when a Mongo filter or pipeline is unsafe or invalid."""


@dataclass(frozen=True)
class QueryValidationConfig:
    regex_enabled: bool = False
    regex_timeout_ms: int = 1_000
    regex_max_pattern_chars: int = 256
    allowed_collections: tuple[str, ...] | None = None


class MongoFilter(BaseModel):
    model_config = ConfigDict(frozen=True)

    document: dict[str, Any] = Field(default_factory=dict)
    uses_regex: bool = False

    @classmethod
    def from_document(
        cls,
        payload: dict[str, Any] | None,
        *,
        config: QueryValidationConfig,
    ) -> MongoFilter:
        document = payload or {}
        uses_regex = _validate_document(document, config=config)
        return cls(document=document, uses_regex=uses_regex)


class MongoPipeline(BaseModel):
    model_config = ConfigDict(frozen=True)

    stages: tuple[dict[str, Any], ...] = Field(default_factory=tuple)

    @classmethod
    def from_stages(
        cls,
        payload: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None,
        *,
        config: QueryValidationConfig,
    ) -> MongoPipeline:
        stages = tuple(payload or ())
        for stage in stages:
            _validate_stage(stage, config=config)
        return cls(stages=stages)


def _validate_document(document: dict[str, Any], *, config: QueryValidationConfig) -> bool:
    uses_regex = False
    for key, value in document.items():
        if key in ("$and", "$or"):
            if not isinstance(value, list) or not value:
                raise MongoFilterError(f"{key} requires a non-empty list")
            for nested in value:
                if not isinstance(nested, dict):
                    raise MongoFilterError(f"{key} entries must be documents")
                uses_regex = _validate_document(nested, config=config) or uses_regex
            continue

        if key.startswith("$"):
            raise MongoFilterError(f"top-level operator {key} is not allowed")

        if not isinstance(value, dict):
            continue

        uses_regex = _validate_field_operators(value, config=config) or uses_regex

    return uses_regex


def _validate_field_operators(value: dict[str, Any], *, config: QueryValidationConfig) -> bool:
    uses_regex = False
    for operator, operand in value.items():
        if operator in BLOCKED_JS_OPERATORS:
            raise MongoFilterError(f"operator {operator} is blocked")  # OWASP A03

        if operator not in ALLOWED_FILTER_OPERATORS:
            raise MongoFilterError(f"operator {operator} is not allow-listed")  # OWASP A03

        if operator == "$regex":
            if not config.regex_enabled:
                raise MongoFilterError("$regex is disabled by configuration")
            if config.regex_timeout_ms <= 0:
                raise MongoFilterError("$regex requires positive regex_timeout_ms")
            if not isinstance(operand, str):
                raise MongoFilterError("$regex pattern must be a literal string")
            if len(operand) > config.regex_max_pattern_chars:
                raise MongoFilterError("$regex pattern exceeds maximum length")
            try:
                re.compile(operand)
            except re.error as error:
                raise MongoFilterError("$regex pattern is invalid") from error
            uses_regex = True

        if operator in {"$in", "$nin", "$all"} and not isinstance(operand, list):
            raise MongoFilterError(f"{operator} requires a list")

        if operator == "$exists" and not isinstance(operand, bool):
            raise MongoFilterError("$exists requires a boolean")

    return uses_regex


def _validate_stage(stage: dict[str, Any], *, config: QueryValidationConfig) -> None:
    if len(stage) != 1:
        raise MongoFilterError("pipeline stage must have exactly one operator")

    stage_name, stage_value = next(iter(stage.items()))
    if stage_name in BLOCKED_JS_OPERATORS:
        raise MongoFilterError(f"pipeline stage {stage_name} is blocked")  # OWASP A03

    if stage_name in BLOCKED_PIPELINE_STAGES:
        raise MongoFilterError(f"pipeline stage {stage_name} is blocked")  # OWASP A03

    if stage_name not in ALLOWED_PIPELINE_STAGES:
        raise MongoFilterError(f"pipeline stage {stage_name} is not allow-listed")

    if stage_name == "$match":
        if not isinstance(stage_value, dict):
            raise MongoFilterError("$match expects a document")
        _validate_document(stage_value, config=config)

    if stage_name == "$lookup":
        if not isinstance(stage_value, dict):
            raise MongoFilterError("$lookup expects an object")
        foreign = stage_value.get("from")
        if not isinstance(foreign, str) or not foreign:
            raise MongoFilterError("$lookup.from must be a non-empty collection name")
        if "." in foreign:
            raise MongoFilterError("$lookup cross-database references are denied")  # OWASP A03
        if config.allowed_collections is not None and foreign not in config.allowed_collections:
            raise MongoFilterError("$lookup collection is outside profile scope")  # OWASP A03
