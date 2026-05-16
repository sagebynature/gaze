import importlib
import sys

from gaze.core.prototype import FakePrototypeController
from gaze.core.state import (
    CalibrationStatus,
    GazeAppState,
    GazeFeatureFlags,
    GazeReadiness,
    TargetSummary,
)
from gaze.desktop.activation import FakeActivationService
from gaze.hotkeys.commands import GazeCommandController
from gaze.overlays.border import RecordingBorderOverlay
from gaze.tracking.calibration import (
    CalibrationOnboardingController,
    CalibrationResult,
)
from gaze.ui.setup_window import setup_sections


class RecordingCalibrationSession:
    def __init__(self, result: CalibrationResult) -> None:
        self.result = result
        self.starts = 0
        self.camera_permission_requests = 0
        self.accessibility_permission_requests = 0

    def start(self) -> CalibrationResult:
        self.starts += 1
        self.camera_permission_requests += 1
        return self.result


def test_calibration_import_does_not_load_pupil_tracker_or_appkit() -> None:
    sys.modules.pop("pupil_tracker", None)
    sys.modules.pop("AppKit", None)

    importlib.import_module("gaze.tracking.calibration")

    assert "pupil_tracker" not in sys.modules
    assert "AppKit" not in sys.modules


def test_calibration_begin_is_side_effect_free_until_session_starts() -> None:
    session = RecordingCalibrationSession(CalibrationResult.ready("Calibration ready"))
    controller = CalibrationOnboardingController(session=session)
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    ).with_target(TargetSummary(app_name="Terminal", confidence=0.91, locked=True))

    calibrating = controller.begin(state)

    assert session.starts == 0
    assert session.camera_permission_requests == 0
    assert session.accessibility_permission_requests == 0
    assert calibrating.readiness.calibration == CalibrationStatus.CALIBRATING
    assert calibrating.current_target is None
    assert calibrating.overlay_visible is False
    assert calibrating.last_status_message == "Calibrating"


def test_calibration_start_requests_camera_permission_only_just_in_time() -> None:
    session = RecordingCalibrationSession(CalibrationResult.ready("Calibration ready"))
    controller = CalibrationOnboardingController(session=session)

    calibrated = controller.run(GazeAppState.default())

    assert session.starts == 1
    assert session.camera_permission_requests == 1
    assert session.accessibility_permission_requests == 0
    assert calibrated.readiness.calibration == CalibrationStatus.READY
    assert calibrated.readiness.camera_available is True
    assert calibrated.readiness.tracker_available is True
    assert calibrated.last_status_message == "Calibration ready"


def test_calibration_results_drive_ready_degraded_and_retry_required_state() -> None:
    cases = [
        (CalibrationResult.ready("Ready"), CalibrationStatus.READY, True),
        (CalibrationResult.degraded("Degraded"), CalibrationStatus.DEGRADED, True),
        (CalibrationResult.retry_required("Retry"), CalibrationStatus.RETRY_REQUIRED, False),
    ]
    base_state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(),
    )

    for result, expected_status, expected_can_track in cases:
        session = RecordingCalibrationSession(result)
        calibrated = CalibrationOnboardingController(session=session).run(base_state)

        assert calibrated.readiness.calibration == expected_status
        assert calibrated.readiness.can_track is expected_can_track
        assert calibrated.last_status_message == result.message


def test_recalibrate_command_runs_session_and_clears_existing_target() -> None:
    overlay = RecordingBorderOverlay()
    session = RecordingCalibrationSession(CalibrationResult.degraded("Calibration degraded"))
    controller = FakePrototypeController(
        overlay=overlay,
        activation=FakeActivationService(),
        calibration_session=session,
    )
    controller.state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    ).with_target(TargetSummary(app_name="Terminal", confidence=0.91, locked=True))
    commands = GazeCommandController(controller)

    commands.recalibrate_command()

    assert session.starts == 1
    assert session.camera_permission_requests == 1
    assert session.accessibility_permission_requests == 0
    assert controller.state.readiness.calibration == CalibrationStatus.DEGRADED
    assert controller.state.current_target is None
    assert controller.state.overlay_visible is False
    assert overlay.visible is False
    assert controller.state.last_status_message == "Calibration degraded"


def test_menu_status_surfaces_retry_required_calibration() -> None:
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.RETRY_REQUIRED,
            camera_available=True,
            tracker_available=True,
        ),
    )

    assert state.menu_status == "retry_required"


def test_setup_calibration_section_exposes_recalibration_action() -> None:
    calibration_section = next(
        section for section in setup_sections() if section.label == "Calibration"
    )

    assert calibration_section.action == "recalibrate"
    assert "Start" in calibration_section.description
    assert "retry" in calibration_section.description
