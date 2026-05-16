"""Tests for real gaze-to-window target selection."""

from __future__ import annotations

import importlib
import sys
from dataclasses import replace

from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    GazeSampleSummary,
    TargetSummary,
)
from gaze.desktop.window_candidates import WindowCandidateSummary


def _ready_state(*, sample: GazeSampleSummary | None) -> GazeAppState:
    return GazeAppState.default().__class__(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
        current_gaze_sample=sample,
        last_status_message="Gaze ready",
    )


def _sample(*, x: float = 150, y: float = 150, valid: bool = True) -> GazeSampleSummary:
    return GazeSampleSummary(timestamp=1.0, x=x, y=y, confidence=0.91, valid=valid)


def _candidate(
    app_name: str,
    *,
    x: float,
    y: float,
    width: float = 200,
    height: float = 200,
    confidence: float = 1.0,
    owner_process_id: int | None = None,
) -> WindowCandidateSummary:
    return WindowCandidateSummary(
        app_name=app_name,
        bounds_x=x,
        bounds_y=y,
        bounds_width=width,
        bounds_height=height,
        confidence=confidence,
        owner_process_id=owner_process_id,
    )


def test_target_selection_import_does_not_load_quartz_or_appkit() -> None:
    sys.modules.pop("gaze.core.target_selection", None)
    sys.modules.pop("Quartz", None)
    sys.modules.pop("AppKit", None)

    importlib.import_module("gaze.core.target_selection")

    assert "Quartz" not in sys.modules
    assert "AppKit" not in sys.modules


def test_topmost_matching_candidate_wins_for_overlapping_windows() -> None:
    from gaze.core.target_selection import candidate_at_gaze_point

    top = _candidate("Top App", x=100, y=100, owner_process_id=20)
    bottom = _candidate("Bottom App", x=50, y=50, owner_process_id=10)

    assert candidate_at_gaze_point(_sample(x=150, y=150), (top, bottom)) == top


def test_no_target_is_selected_outside_all_candidates() -> None:
    from gaze.core.target_selection import candidate_at_gaze_point

    candidates = (_candidate("Terminal", x=100, y=100),)

    assert candidate_at_gaze_point(_sample(x=500, y=500), candidates) is None


def test_no_target_is_selected_without_a_valid_gaze_sample() -> None:
    from gaze.core.target_selection import GazeTargetSelectionPipeline

    pipeline = GazeTargetSelectionPipeline(stability_ms=400)
    locked_state = replace(
        _ready_state(sample=_sample(valid=False)),
        current_target=TargetSummary(app_name="Terminal", confidence=1.0, locked=True),
        overlay_visible=True,
    )

    next_state = pipeline.apply(
        locked_state,
        (_candidate("Terminal", x=100, y=100),),
        now_ms=1500,
    )

    assert next_state.current_target is None
    assert next_state.overlay_visible is False


def test_candidate_must_be_stable_before_becoming_current_target() -> None:
    from gaze.core.target_selection import GazeTargetSelectionPipeline

    pipeline = GazeTargetSelectionPipeline(stability_ms=400)
    state = _ready_state(sample=_sample(x=150, y=150))
    candidates = (_candidate("Terminal", x=100, y=100, confidence=0.88, owner_process_id=777),)

    state = pipeline.apply(state, candidates, now_ms=1000)
    assert state.current_target is None

    state = pipeline.apply(state, candidates, now_ms=1400)
    assert state.current_target is not None
    assert state.current_target.app_name == "Terminal"
    assert state.current_target.confidence == 0.88
    assert state.current_target.owner_process_id == 777
    assert state.current_target.locked is True
    assert state.overlay_visible is True


def test_candidate_change_restarts_stability_timing() -> None:
    from gaze.core.target_selection import GazeTargetSelectionPipeline

    pipeline = GazeTargetSelectionPipeline(stability_ms=400)
    terminal = _candidate("Terminal", x=100, y=100)
    safari = _candidate("Safari", x=400, y=100)
    state = _ready_state(sample=_sample(x=150, y=150))

    state = pipeline.apply(state, (terminal, safari), now_ms=1000)
    state = pipeline.apply(state, (terminal, safari), now_ms=1400)
    assert state.current_target is not None
    assert state.current_target.app_name == "Terminal"

    state = replace(state, current_gaze_sample=_sample(x=450, y=150))
    state = pipeline.apply(state, (terminal, safari), now_ms=1450)
    assert state.current_target is None

    state = pipeline.apply(state, (terminal, safari), now_ms=1850)
    assert state.current_target is not None
    assert state.current_target.app_name == "Safari"


def test_empty_candidate_list_covers_system_ui_no_target_case() -> None:
    from gaze.core.target_selection import GazeTargetSelectionPipeline

    pipeline = GazeTargetSelectionPipeline(stability_ms=400)
    state = _ready_state(sample=_sample(x=150, y=150))

    next_state = pipeline.apply(state, (), now_ms=1000)

    assert next_state.current_target is None
    assert next_state.last_status_message == "No target"
