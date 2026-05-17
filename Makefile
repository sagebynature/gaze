PYTHON ?= python3
PUPIL_TRACKER_PATH ?= ../pupil-tracker

.PHONY: sync sync-pupil-dev run run-pupil-dev app-bundle app-bundle-pupil-dev test lint typecheck check check-pupil-dev

sync:
	uv sync --dev

sync-pupil-dev: sync
	uv pip install --editable "$(PUPIL_TRACKER_PATH)"

run:
	uv run gaze

run-pupil-dev: sync-pupil-dev
	uv run --no-sync gaze

app-bundle: sync
	uv run python -m tools.build_app_bundle

app-bundle-pupil-dev: sync-pupil-dev
	uv run --no-sync python -m tools.build_app_bundle --pupil-tracker-path "$(PUPIL_TRACKER_PATH)"

test:
	uv run pytest -v

lint:
	uv run ruff check src tests tools

typecheck:
	uv run ty check src tests tools

check: lint typecheck test

check-pupil-dev: sync-pupil-dev
	uv run --no-sync ruff check src tests tools
	uv run --no-sync ty check src tests tools
	uv run --no-sync pytest -v
