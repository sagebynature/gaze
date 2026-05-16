"""Adapter seam for PupilTracker.

Implementation tasks will connect this boundary to `pupil_tracker` while keeping
unit tests camera-free through fakes.
"""

from __future__ import annotations

from importlib.util import find_spec


def pupil_tracker_available() -> bool:
    """Return whether the PupilTracker package is importable."""

    return find_spec("pupil_tracker") is not None
