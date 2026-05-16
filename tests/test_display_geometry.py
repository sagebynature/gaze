import importlib
import sys

from gaze.core.display_geometry import DisplayGeometry, DisplayLayoutSnapshot
from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    TargetSummary,
)
from gaze.tracking.calibration import CalibrationOnboardingController, CalibrationResult


class FixedCalibrationSession:
    def __init__(self, result: CalibrationResult) -> None:
        self.result = result

    def start(self) -> CalibrationResult:
        return self.result


def built_in_left_of_external_layout() -> DisplayLayoutSnapshot:
    return DisplayLayoutSnapshot(
        displays=(
            DisplayGeometry(
                display_id=1,
                x=0,
                y=0,
                width=1728,
                height=1117,
                scale=2.0,
                built_in=True,
            ),
            DisplayGeometry(
                display_id=2,
                x=1728,
                y=-120,
                width=2560,
                height=1440,
                scale=1.0,
                built_in=False,
            ),
        )
    )


def external_above_built_in_layout() -> DisplayLayoutSnapshot:
    return DisplayLayoutSnapshot(
        displays=(
            DisplayGeometry(
                display_id=1,
                x=0,
                y=1440,
                width=1728,
                height=1117,
                scale=2.0,
                built_in=True,
            ),
            DisplayGeometry(
                display_id=2,
                x=-416,
                y=0,
                width=2560,
                height=1440,
                scale=1.0,
                built_in=False,
            ),
        )
    )


def test_display_geometry_imports_are_platform_safe() -> None:
    sys.modules.pop("Quartz", None)
    sys.modules.pop("AppKit", None)

    importlib.import_module("gaze.core.display_geometry")
    importlib.import_module("gaze.desktop.display_provider")

    assert "Quartz" not in sys.modules
    assert "AppKit" not in sys.modules


def test_display_layout_signature_records_geometry_without_titles_or_content() -> None:
    layout = built_in_left_of_external_layout()

    assert layout.signature == (
        "1:built-in:0.0,0.0,1728.0,1117.0@2.0|"
        "2:external:1728.0,-120.0,2560.0,1440.0@1.0"
    )
    assert layout.visible_regions == (
        (0.0, 0.0, 1728.0, 1117.0),
        (1728.0, -120.0, 2560.0, 1440.0),
    )
    assert not hasattr(layout, "window_title")


def test_last_good_calibration_records_display_signature_and_geometry() -> None:
    layout = built_in_left_of_external_layout()
    session = FixedCalibrationSession(
        CalibrationResult.ready("Calibration ready", display_layout=layout)
    )

    state = CalibrationOnboardingController(session=session).run(GazeAppState.default())

    assert state.calibration_display_layout == layout
    recorded_layout = state.calibration_display_layout
    assert recorded_layout is not None
    assert recorded_layout.signature == layout.signature
    assert state.readiness.calibration == CalibrationStatus.READY


def test_display_layout_change_degrades_calibration_and_recommends_recalibration() -> None:
    original_layout = built_in_left_of_external_layout()
    changed_layout = external_above_built_in_layout()
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
        calibration_display_layout=original_layout,
    ).with_target(TargetSummary(app_name="Terminal", confidence=0.9, locked=True))

    degraded = state.with_current_display_layout(changed_layout)

    assert degraded.readiness.calibration == CalibrationStatus.DEGRADED
    assert degraded.current_target is None
    assert degraded.overlay_visible is False
    assert degraded.last_status_message == "Display layout changed; recalibrate recommended"


def test_matching_display_layout_keeps_ready_calibration_and_target() -> None:
    layout = built_in_left_of_external_layout()
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
        calibration_display_layout=layout,
    ).with_target(TargetSummary(app_name="Terminal", confidence=0.9, locked=True))

    unchanged = state.with_current_display_layout(built_in_left_of_external_layout())

    assert unchanged.readiness.calibration == CalibrationStatus.READY
    assert unchanged.current_target == state.current_target
    assert unchanged.last_status_message == state.last_status_message


def test_two_built_in_external_layouts_have_distinct_validation_signatures() -> None:
    first = built_in_left_of_external_layout()
    second = external_above_built_in_layout()

    assert first.signature != second.signature
    assert first.has_built_in_display is True
    assert first.has_external_display is True
    assert second.has_built_in_display is True
    assert second.has_external_display is True
