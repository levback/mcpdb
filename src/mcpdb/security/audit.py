from __future__ import annotations

import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    who: str
    source: str
    action: str
    target: str
    outcome: str
    request_id: str
    meta: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())


class AuditSink(ABC):
    @abstractmethod
    def write(self, entry: AuditEntry) -> str:
        """Write an Audit Entry and return its hash."""


class HMACChainSink(AuditSink):
    def __init__(self, path: Path, key: str, key_id: str = "default") -> None:
        self._path = path
        self._key = key.encode("utf-8")
        self._key_id = key_id
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._prev_hash = self._load_prev_hash()

    def write(self, entry: AuditEntry) -> str:
        base_payload = {
            "prev_hash": self._prev_hash,
            "key_id": self._key_id,
            "ts": entry.ts,
            "who": entry.who,
            "source": entry.source,
            "action": entry.action,
            "target": entry.target,
            "outcome": entry.outcome,
            "request_id": entry.request_id,
            "meta": entry.meta,
        }
        digest = self._digest(base_payload)
        payload = dict(base_payload)
        payload["hash"] = digest

        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()  # NIST AU-9: durable write

        self._prev_hash = digest
        return digest

    def _load_prev_hash(self) -> str:
        if not self._path.exists():
            return "0" * 64

        lines = [
            line for line in self._path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        if not lines:
            return "0" * 64
        last = json.loads(lines[-1])
        existing_hash = last.get("hash")
        if not isinstance(existing_hash, str):
            raise ValueError("Invalid audit line: missing hash")
        return existing_hash

    def _digest(self, payload: dict[str, Any]) -> str:
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        material = f"{payload['prev_hash']}{canonical_json}".encode()
        return hmac.new(self._key, material, hashlib.sha256).hexdigest()  # OWASP A09

    @staticmethod
    def verify(path: Path, key: str) -> bool:
        if not path.exists():
            return True

        key_bytes = key.encode("utf-8")
        previous_hash = "0" * 64
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in lines:
            payload = json.loads(line)
            stored_hash = payload.pop("hash", None)
            if not isinstance(stored_hash, str):
                return False
            if payload.get("prev_hash") != previous_hash:
                return False

            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            material = f"{payload['prev_hash']}{canonical}".encode()
            computed = hmac.new(key_bytes, material, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(stored_hash, computed):
                return False

            previous_hash = stored_hash

        return True


class CompositeSink(AuditSink):
    def __init__(self, sinks: list[AuditSink]) -> None:
        self._sinks = list(sinks)

    def write(self, entry: AuditEntry) -> str:
        last_hash = ""
        for sink in self._sinks:
            last_hash = sink.write(entry)
        return last_hash
