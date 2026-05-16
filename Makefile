PYTHON ?= python3
PUPIL_TRACKER_PATH ?= ../pupil-tracker

.PHONY: sync sync-pupil-dev run run-pupil-dev test lint typecheck check check-pupil-dev

sync:
	uv sync --dev

sync-pupil-dev: sync
	uv pip install --editable "$(PUPIL_TRACKER_PATH)"

run:
	uv run gaze

run-pupil-dev: sync-pupil-dev
	uv run --no-sync gaze

test:
	uv run pytest -v

lint:
	uv run ruff check src tests

typecheck:
	uv run ty check src tests

check: lint typecheck test

check-pupil-dev: sync-pupil-dev
	uv run --no-sync ruff check src tests
	uv run --no-sync ty check src tests
	uv run --no-sync pytest -v
