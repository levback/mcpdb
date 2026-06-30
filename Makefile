.PHONY: install lint type test sec build run

install:
	uv sync --all-extras --dev

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

type:
	uv run mypy src --strict

test:
	uv run pytest --cov=mcpdb --cov-branch --cov-fail-under=90 -q

sec:
	uv run bandit -r src -lll
	uv run pip-audit

build:
	docker build -t mcpdb:dev .

run:
	uv run python -m mcpdb