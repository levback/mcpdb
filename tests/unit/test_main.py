import runpy
import subprocess
import sys

import pytest

from mcpdb import __main__ as package_main
from mcpdb.cli import __main__ as cli_main


def test_module_runs_as_script() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mcpdb"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.stdout.strip() == "mcpdb 0.1.0"


def test_exit_code_zero() -> None:
    result = subprocess.run([sys.executable, "-m", "mcpdb"], check=False)

    assert result.returncode == 0


def test_render_version_returns_expected_text() -> None:
    assert package_main.render_version() == "mcpdb 0.1.0"


def test_main_prints_version(capsys: object) -> None:
    package_main.main()

    captured = capsys.readouterr()
    assert captured.out.strip() == "mcpdb 0.1.0"


def test_module_branch_runs_with_runpy(capsys: object) -> None:
    runpy.run_module("mcpdb", run_name="__main__")

    captured = capsys.readouterr()
    assert captured.out.strip() == "mcpdb 0.1.0"


def test_cli_main_without_version_is_silent(capsys: object) -> None:
    cli_main.main(False)

    captured = capsys.readouterr()
    assert captured.out == ""


def test_cli_main_with_version_prints_version(capsys: object) -> None:
    cli_main.main(True)

    captured = capsys.readouterr()
    assert captured.out.strip() == "mcpdb 0.1.0"


def test_cli_help_exit_code_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mcpdb.cli", "--help"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "mcpdb command-line interface" in result.stdout
    assert "--version" in result.stdout


def test_cli_version_flag_prints_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mcpdb.cli", "--version"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "mcpdb 0.1.0" in result.stdout


def test_cli_module_branch_runs_with_runpy(monkeypatch: object, capsys: object) -> None:
    monkeypatch.setattr(sys, "argv", ["python", "--version"])
    with pytest.raises(SystemExit) as raised_error:
        runpy.run_module("mcpdb.cli.__main__", run_name="__main__")

    captured = capsys.readouterr()
    assert raised_error.value.code == 0
    assert captured.out.strip() == "mcpdb 0.1.0"
