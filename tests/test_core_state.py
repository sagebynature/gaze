from gaze.core.state import (
    CalibrationStatus,
    GazeFeatureFlags,
    GazeReadiness,
    manual_activation_allowed,
)


def test_manual_activation_is_disabled_by_default() -> None:
    readiness = GazeReadiness(
        calibration=CalibrationStatus.READY,
        camera_available=True,
        tracker_available=True,
    )

    assert manual_activation_allowed(GazeFeatureFlags(), readiness) is False


def test_manual_activation_requires_tracking_readiness() -> None:
    flags = GazeFeatureFlags(gaze_enabled=True)

    assert manual_activation_allowed(flags, GazeReadiness()) is False


def test_manual_activation_allowed_when_enabled_and_ready() -> None:
    flags = GazeFeatureFlags(gaze_enabled=True)
    readiness = GazeReadiness(
        calibration=CalibrationStatus.READY,
        camera_available=True,
        tracker_available=True,
    )

    assert manual_activation_allowed(flags, readiness) is True


def test_auto_activation_stays_disabled_by_default() -> None:
    assert GazeFeatureFlags().auto_activate_enabled is False
