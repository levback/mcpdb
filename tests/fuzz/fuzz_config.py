from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from mcpdb.config.loader import ConfigLoadError, load_settings


def _exercise_config(raw: bytes) -> None:
    text = raw.decode("utf-8", errors="ignore")
    if not text.strip():
        return

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fuzz.yaml"
        path.write_text(text, encoding="utf-8")
        try:
            load_settings(path)
        except (ConfigLoadError, ValueError, yaml.YAMLError):
            return


def test_fuzz_config_no_unhandled_exception() -> None:
    corpus = [
        b"",
        b"profiles: []",
        b"profiles: [",
        b"profiles:\n  - name: main\n    backend: sqlite\n    dsn: sqlite+aiosqlite:///:memory:\n",
        b"\xff\xfe\xfd",
    ]
    for sample in corpus:
        _exercise_config(sample)


def _atheris_entry(data: bytes) -> None:
    _exercise_config(data)


if __name__ == "__main__":
    try:
        import atheris
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("atheris is not installed") from exc

    atheris.Setup([], _atheris_entry)
    atheris.Fuzz()
