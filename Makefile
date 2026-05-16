PYTHON ?= python3

.PHONY: sync run test lint typecheck check

sync:
	uv sync --dev

run:
	uv run gaze

test:
	uv run pytest -v

lint:
	uv run ruff check src tests

typecheck:
	uv run ty check src tests

check: lint typecheck test
