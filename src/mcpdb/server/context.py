from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from mcpdb.db.base import Context as DbContext
from mcpdb.db.policy import OpClass


@dataclass(frozen=True)
class RequestContext:
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    principal: str = "anonymous"
    source_ip: str = "127.0.0.1"
    user_agent: str = "mcpdb"


@dataclass(frozen=True)
class Context:
    profile: str
    op_class: OpClass
    request: RequestContext

    def to_db_context(self) -> DbContext:
        return DbContext(
            profile=self.profile,
            request_id=self.request.correlation_id,
            principal=self.request.principal,
        )


def build_request_context(
    *,
    correlation_id: str | None = None,
    principal: str = "anonymous",
    source_ip: str = "127.0.0.1",
    user_agent: str = "mcpdb",
) -> RequestContext:
    return RequestContext(
        correlation_id=correlation_id or str(uuid.uuid4()),
        principal=principal,
        source_ip=source_ip,
        user_agent=user_agent,
    )
