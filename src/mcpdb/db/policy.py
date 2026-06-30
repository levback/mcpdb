from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from mcpdb.db.base import Cap


class OpClass(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    ADMIN = "ADMIN"


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    adjusted_cap: Cap | None


@dataclass(frozen=True)
class Policy:
    query_timeout_ms: int = 30_000
    max_rows: int = 10_000
    max_payload_bytes: int = 5_000_000
    allow_reads: bool = False  # OWASP A01: default deny
    allow_writes: bool = False
    allow_admin: bool = False
    allowlist_tables: tuple[str, ...] | None = None

    def decide(
        self,
        op_class: OpClass,
        *,
        table: str | None = None,
        requested_cap: Cap | None = None,
    ) -> Decision:
        if op_class is OpClass.READ and not self.allow_reads:
            return Decision(False, "READ denied by policy", None)  # OWASP A01

        if op_class is OpClass.WRITE and not self.allow_writes:
            return Decision(False, "WRITE denied by policy", None)  # OWASP A01

        if op_class is OpClass.ADMIN and not self.allow_admin:
            return Decision(False, "ADMIN denied by policy", None)  # OWASP A01

        if (
            table is not None
            and self.allowlist_tables is not None
            and table not in self.allowlist_tables
        ):
            return Decision(False, f"Table '{table}' is not allowlisted", None)

        return Decision(True, "allowed", self._adjust_cap(requested_cap))

    def _adjust_cap(self, requested_cap: Cap | None) -> Cap:
        if requested_cap is None:
            return self.base_cap()

        return Cap(
            query_timeout_ms=min(self.query_timeout_ms, requested_cap.query_timeout_ms),
            max_rows=min(self.max_rows, requested_cap.max_rows),
            max_payload_bytes=min(self.max_payload_bytes, requested_cap.max_payload_bytes),
        )

    def base_cap(self) -> Cap:
        return Cap(
            query_timeout_ms=self.query_timeout_ms,
            max_rows=self.max_rows,
            max_payload_bytes=self.max_payload_bytes,
        )
