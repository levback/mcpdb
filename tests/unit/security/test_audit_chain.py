from __future__ import annotations

import json
from pathlib import Path

from mcpdb.security.audit import AuditEntry, CompositeSink, HMACChainSink


def test_audit_chain_integrity_pass(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    sink = HMACChainSink(path=path, key="test-key")

    sink.write(
        AuditEntry(
            who="alice",
            source="127.0.0.1",
            action="db_ping",
            target="main",
            outcome="allow",
            request_id="r-1",
        )
    )
    sink.write(
        AuditEntry(
            who="alice",
            source="127.0.0.1",
            action="db_query",
            target="main",
            outcome="allow",
            request_id="r-2",
        )
    )

    assert HMACChainSink.verify(path=path, key="test-key") is True


def test_audit_chain_detects_tamper_of_any_field(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    sink = HMACChainSink(path=path, key="test-key")
    sink.write(
        AuditEntry(
            who="alice",
            source="127.0.0.1",
            action="db_ping",
            target="main",
            outcome="allow",
            request_id="r-1",
        )
    )

    line = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    line["outcome"] = "deny"
    path.write_text(json.dumps(line, sort_keys=True) + "\n", encoding="utf-8")

    assert HMACChainSink.verify(path=path, key="test-key") is False


def test_audit_chain_detects_reorder(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    sink = HMACChainSink(path=path, key="test-key")
    sink.write(
        AuditEntry(
            who="alice",
            source="127.0.0.1",
            action="db_ping",
            target="main",
            outcome="allow",
            request_id="r-1",
        )
    )
    sink.write(
        AuditEntry(
            who="bob",
            source="127.0.0.1",
            action="db_query",
            target="main",
            outcome="deny",
            request_id="r-2",
        )
    )

    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")

    assert HMACChainSink.verify(path=path, key="test-key") is False


def test_audit_chain_composite_writes_to_all_sinks(tmp_path: Path) -> None:
    first_path = tmp_path / "audit-1.jsonl"
    second_path = tmp_path / "audit-2.jsonl"
    first = HMACChainSink(path=first_path, key="test-key")
    second = HMACChainSink(path=second_path, key="test-key")
    sink = CompositeSink([first, second])

    sink.write(
        AuditEntry(
            who="alice",
            source="127.0.0.1",
            action="db_ping",
            target="main",
            outcome="allow",
            request_id="r-1",
        )
    )

    assert HMACChainSink.verify(path=first_path, key="test-key") is True
    assert HMACChainSink.verify(path=second_path, key="test-key") is True
