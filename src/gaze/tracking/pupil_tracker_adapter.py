"""Adapter seam for PupilTracker.

Implementation tasks connect this boundary to `pupil_tracker` while keeping unit
tests camera-free through fakes. Development can opt into a sibling editable
checkout without changing the release/default PyPI dependency path.
"""

from __future__ import annotations

import tomllib
from collections.abc import MutableSequence
from importlib.util import find_spec
from pathlib import Path


def pupil_tracker_available() -> bool:
    """Return whether the PupilTracker package is importable."""

    return find_spec("pupil_tracker") is not None


def editable_sibling_source_path(sibling_path: Path) -> Path | None:
    """Return the importable source path for a valid sibling PupilTracker checkout."""

    pyproject = sibling_path / "pyproject.toml"
    source_path = sibling_path / "src"
    package_path = source_path / "pupil_tracker"
    if not pyproject.is_file() or not package_path.is_dir():
        return None

    try:
        pyproject_data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return None
    if pyproject_data.get("project", {}).get("name") != "pupil-tracker":
        return None

    return source_path


def missing_pupil_tracker_guidance(sibling_path: Path) -> str:
    """Return setup guidance that preserves both editable-dev and PyPI paths."""

    return (
        "PupilTracker is not available. For editable sibling development run "
        f"`make sync-pupil-dev PUPIL_TRACKER_PATH={sibling_path}` then "
        f"`make check-pupil-dev PUPIL_TRACKER_PATH={sibling_path}` or "
        "`make run-pupil-dev` so uv uses the editable install with --no-sync. "
        "For the release/default PyPI path run `uv sync`; pyproject.toml keeps "
        "`pupil-tracker>=1.0.0` as the packaged dependency."
    )


def enable_editable_sibling_import(
    sibling_path: Path,
    *,
    sys_path: MutableSequence[str],
) -> Path:
    """Prepend a validated sibling PupilTracker `src` path for explicit dev mode.

    This function does not import PupilTracker, start cameras, or touch runtime
    permissions. It only adjusts the supplied import path sequence after checking
    that the sibling checkout looks like the expected project.
    """

    source_path = editable_sibling_source_path(sibling_path)
    if source_path is None:
        raise RuntimeError(missing_pupil_tracker_guidance(sibling_path))

    source_path_text = str(source_path)
    if source_path_text in sys_path:
        sys_path.remove(source_path_text)
    sys_path.insert(0, source_path_text)
    return source_path
