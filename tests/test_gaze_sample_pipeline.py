import importlib
import sys
from dataclasses import dataclass

from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    TargetSummary,
)
from gaze.tracking.gaze_pipeline import GazeSamplePipeline


@dataclass(frozen=True)
class FakePupilTrackerSample:
    timestamp: float
    x: float
    y: float
    confidence: float
    valid: bool = True
    reason: str | None = None


def tracking_state() -> GazeAppState:
    return GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    )


def test_gaze_pipeline_import_does_not_load_pupil_tracker_or_appkit() -> None:
    sys.modules.pop("pupil_tracker", None)
    sys.modules.pop("AppKit", None)

    importlib.import_module("gaze.tracking.gaze_pipeline")

    assert "pupil_tracker" not in sys.modules
    assert "AppKit" not in sys.modules


def test_valid_pupil_tracker_sample_updates_current_gaze_point() -> None:
    sample = FakePupilTrackerSample(
        timestamp=10.0,
        x=321.5,
        y=654.25,
        confidence=0.82,
    )

    state = GazeSamplePipeline(min_confidence=0.60, max_sample_age_seconds=0.25).apply(
        tracking_state(),
        sample,
        now_seconds=10.12,
    )

    assert state.current_gaze_sample is not None
    assert state.current_gaze_sample.x == 321.5
    assert state.current_gaze_sample.y == 654.25
    assert state.current_gaze_sample.confidence == 0.82
    assert state.current_gaze_sample.timestamp == 10.0
    assert state.current_gaze_sample.valid is True
    assert state.current_gaze_sample.reason is None
    assert state.readiness.calibration == CalibrationStatus.READY
    assert state.last_status_message == "Gaze sample ready"


def test_invalid_sample_degrades_state_without_crashing_and_clears_target() -> None:
    prior = tracking_state().with_target(
        TargetSummary(app_name="Terminal", confidence=0.9, locked=True)
    )
    sample = FakePupilTrackerSample(
        timestamp=20.0,
        x=100.0,
        y=200.0,
        confidence=0.0,
        valid=False,
        reason="no face detected",
    )

    state = GazeSamplePipeline().apply(prior, sample, now_seconds=20.01)

    assert state.current_gaze_sample is not None
    assert state.current_gaze_sample.valid is False
    assert state.current_gaze_sample.reason == "no face detected"
    assert state.readiness.calibration == CalibrationStatus.DEGRADED
    assert state.current_target is None
    assert state.overlay_visible is False
    assert state.last_status_message == "Gaze degraded: no face detected"


def test_low_confidence_sample_degrades_state_without_crashing() -> None:
    sample = FakePupilTrackerSample(
        timestamp=30.0,
        x=40.0,
        y=50.0,
        confidence=0.39,
    )

    state = GazeSamplePipeline(min_confidence=0.40).apply(
        tracking_state(),
        sample,
        now_seconds=30.01,
    )

    assert state.current_gaze_sample is not None
    assert state.current_gaze_sample.valid is False
    assert state.current_gaze_sample.reason == "low confidence"
    assert state.readiness.calibration == CalibrationStatus.DEGRADED
    assert state.last_status_message == "Gaze degraded: low confidence"


def test_stale_sample_degrades_state_without_crashing() -> None:
    sample = FakePupilTrackerSample(
        timestamp=40.0,
        x=400.0,
        y=500.0,
        confidence=0.91,
    )

    state = GazeSamplePipeline(max_sample_age_seconds=0.25).apply(
        tracking_state(),
        sample,
        now_seconds=40.26,
    )

    assert state.current_gaze_sample is not None
    assert state.current_gaze_sample.valid is False
    assert state.current_gaze_sample.reason == "stale sample"
    assert state.readiness.calibration == CalibrationStatus.DEGRADED
    assert state.last_status_message == "Gaze degraded: stale sample"


def test_sample_is_rejected_when_tracking_is_not_ready() -> None:
    sample = FakePupilTrackerSample(
        timestamp=50.0,
        x=10.0,
        y=20.0,
        confidence=0.95,
    )

    state = GazeSamplePipeline().apply(GazeAppState.default(), sample, now_seconds=50.0)

    assert state.current_gaze_sample is not None
    assert state.current_gaze_sample.valid is False
    assert state.current_gaze_sample.reason == "tracking not ready"
    assert state.readiness.calibration == CalibrationStatus.NOT_READY
    assert state.last_status_message == "Gaze degraded: tracking not ready"
