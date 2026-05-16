from pathlib import Path

import pytest

from gaze.tracking.pupil_tracker_adapter import (
    editable_sibling_source_path,
    enable_editable_sibling_import,
    missing_pupil_tracker_guidance,
)


def _write_pupil_tracker_sibling(root: Path) -> Path:
    sibling = root / "pupil-tracker"
    (sibling / "src" / "pupil_tracker").mkdir(parents=True)
    (sibling / "pyproject.toml").write_text(
        '[project]\nname = "pupil-tracker"\nversion = "1.0.0"\n',
        encoding="utf-8",
    )
    return sibling


def test_editable_sibling_source_path_detects_valid_pupil_tracker_checkout(tmp_path: Path) -> None:
    sibling = _write_pupil_tracker_sibling(tmp_path)

    source_path = editable_sibling_source_path(sibling)

    assert source_path == sibling / "src"


def test_editable_sibling_source_path_accepts_equivalent_toml_formatting(tmp_path: Path) -> None:
    sibling = tmp_path / "pupil-tracker"
    (sibling / "src" / "pupil_tracker").mkdir(parents=True)
    (sibling / "pyproject.toml").write_text(
        "[project]\nname='pupil-tracker'\nversion='1.0.0'\n",
        encoding="utf-8",
    )

    assert editable_sibling_source_path(sibling) == sibling / "src"


def test_editable_sibling_source_path_rejects_missing_or_wrong_checkout(tmp_path: Path) -> None:
    wrong_project = tmp_path / "pupil-tracker"
    (wrong_project / "src" / "pupil_tracker").mkdir(parents=True)
    (wrong_project / "pyproject.toml").write_text(
        '[project]\nname = "not-pupil-tracker"\n',
        encoding="utf-8",
    )

    assert editable_sibling_source_path(wrong_project) is None
    assert editable_sibling_source_path(tmp_path / "missing") is None


def test_enable_editable_sibling_import_prepends_source_path_once(tmp_path: Path) -> None:
    sibling = _write_pupil_tracker_sibling(tmp_path)
    sys_path = ["/existing"]

    inserted = enable_editable_sibling_import(sibling, sys_path=sys_path)
    inserted_again = enable_editable_sibling_import(sibling, sys_path=sys_path)

    assert inserted == sibling / "src"
    assert inserted_again == sibling / "src"
    assert sys_path == [str(sibling / "src"), "/existing"]


def test_enable_editable_sibling_import_failure_is_actionable(tmp_path: Path) -> None:
    missing = tmp_path / "missing-pupil-tracker"

    with pytest.raises(RuntimeError, match="make sync-pupil-dev") as exc_info:
        enable_editable_sibling_import(missing, sys_path=[])

    message = str(exc_info.value)
    assert str(missing) in message
    assert "uv sync" in message


def test_missing_dependency_guidance_preserves_pypi_and_editable_paths(tmp_path: Path) -> None:
    sibling = tmp_path / "pupil-tracker"

    guidance = missing_pupil_tracker_guidance(sibling)

    assert "make sync-pupil-dev" in guidance
    assert "make check-pupil-dev" in guidance
    assert "--no-sync" in guidance
    assert str(sibling) in guidance
    assert "uv sync" in guidance
    assert "pupil-tracker>=1.0.0" in guidance


def test_makefile_provides_no_sync_check_after_editable_install() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "check-pupil-dev: sync-pupil-dev" in makefile
    assert "uv run --no-sync ruff check src tests" in makefile
    assert "uv run --no-sync ty check src tests" in makefile
    assert "uv run --no-sync pytest -v" in makefile
