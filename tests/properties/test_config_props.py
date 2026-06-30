from __future__ import annotations

import tempfile
from pathlib import Path

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from mcpdb.config.loader import load_settings
from mcpdb.config.models import McpDbSettings


@settings(max_examples=1000, deadline=None)
@given(
    timeout=st.integers(min_value=1, max_value=120_000),
    max_rows=st.integers(min_value=1, max_value=1_000_000),
    name=st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=10,
    ),
)
def test_config_dump_then_load_equals_original(
    timeout: int,
    max_rows: int,
    name: str,
) -> None:
    payload = {
        "profiles": [
            {
                "name": "main",
                "backend": "sqlite",
                "dsn": f"sqlite+aiosqlite:///{name}.db",
            }
        ],
        "limits": {"query_timeout_ms": timeout, "max_rows": max_rows},
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "roundtrip.yaml"
        config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

        loaded = load_settings(config_path)
        dumped = loaded.model_dump(mode="python")
        reloaded = McpDbSettings.model_validate(dumped)

        assert loaded.model_dump(mode="python") == reloaded.model_dump(mode="python")
