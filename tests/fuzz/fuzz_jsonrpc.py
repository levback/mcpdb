from __future__ import annotations

import json
from typing import Any


def _exercise_jsonrpc(raw: bytes) -> None:
    text = raw.decode("utf-8", errors="ignore")
    if not text.strip():
        return

    payload: Any
    try:
        payload = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return

    if not isinstance(payload, dict):
        return

    jsonrpc = payload.get("jsonrpc")
    method = payload.get("method")
    params = payload.get("params")
    request_id = payload.get("id")

    if jsonrpc not in (None, "2.0"):
        return
    if method is not None and not isinstance(method, str):
        return
    if params is not None and not isinstance(params, dict | list):
        return
    if request_id is not None and isinstance(request_id, dict):
        return


def test_fuzz_jsonrpc_no_unhandled_exception() -> None:
    corpus = [
        b"",
        b"{}",
        b'{"jsonrpc":"2.0","method":"db_query","params":{"profile":"main"},"id":1}',
        b'{"jsonrpc":"2.0","method":123,"params":null,"id":{}}',
        b'[{"jsonrpc":"2.0"}]',
        b"\x00\x01\x02",
    ]
    for sample in corpus:
        _exercise_jsonrpc(sample)


def _atheris_entry(data: bytes) -> None:
    _exercise_jsonrpc(data)


if __name__ == "__main__":
    try:
        import atheris
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("atheris is not installed") from exc

    atheris.Setup([], _atheris_entry)
    atheris.Fuzz()
