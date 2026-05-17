import importlib
import sys
from typing import Any, cast

import pytest

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
    CalibrationProviderSnapshot,
    CalibrationResult,
    CalibrationStage,
    CalibrationTargetPoint,
    ScalarValue,
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


def test_gaze_owned_calibration_provider_snapshot_models_wizard_stages() -> None:
    snapshot = CalibrationProviderSnapshot(
        stage=CalibrationStage.TARGET_SEQUENCE,
        message="Follow the target",
        camera_available=True,
        tracker_available=True,
        current_target=CalibrationTargetPoint(x=0.5, y=0.25, index=3, total=9),
        progress=0.33,
    )

    assert snapshot.stage is CalibrationStage.TARGET_SEQUENCE
    assert snapshot.current_target == CalibrationTargetPoint(x=0.5, y=0.25, index=3, total=9)
    assert snapshot.progress == 0.33
    assert snapshot.to_scalar_payload() == {
        "stage": "target_sequence",
        "message": "Follow the target",
        "camera_available": True,
        "tracker_available": True,
        "current_target": {"x": 0.5, "y": 0.25, "index": 3, "total": 9},
        "progress": 0.33,
        "quality": None,
        "result_status": None,
    }


def test_calibration_provider_snapshot_can_represent_all_wizard_states() -> None:
    snapshots = [
        CalibrationProviderSnapshot(stage=CalibrationStage.PRIVACY, message="Private by design"),
        CalibrationProviderSnapshot(stage=CalibrationStage.READINESS, message="Checking camera"),
        CalibrationProviderSnapshot(
            stage=CalibrationStage.TARGET_SEQUENCE,
            message="Follow the target",
            current_target=CalibrationTargetPoint(x=0.5, y=0.5, index=1, total=1),
        ),
        CalibrationProviderSnapshot(
            stage=CalibrationStage.RESULT,
            message="Ready",
            result_status=CalibrationStatus.READY,
        ),
        CalibrationProviderSnapshot(
            stage=CalibrationStage.RETRY_REQUIRED,
            message="Try calibration again",
            result_status=CalibrationStatus.RETRY_REQUIRED,
        ),
        CalibrationProviderSnapshot(
            stage=CalibrationStage.UNAVAILABLE,
            message="Camera unavailable",
        ),
    ]

    assert [snapshot.stage.value for snapshot in snapshots] == [
        "privacy",
        "readiness",
        "target_sequence",
        "result",
        "retry_required",
        "unavailable",
    ]


def test_calibration_provider_snapshot_rejects_content_or_raw_visual_fields() -> None:
    forbidden_fields = [
        "window_title",
        "windowTitle",
        "active_url",
        "filename",
        "camera_frame_path",
        "raw_frame_bytes",
        "document_name",
        "screenshot",
        "camera_frame",
        "raw_frame",
        "desktop_content",
    ]

    for field in forbidden_fields:
        with pytest.raises(ValueError, match="forbidden calibration payload field"):
            CalibrationProviderSnapshot(
                stage=CalibrationStage.READINESS,
                message="Camera ready",
                extra_scalars={field: "forbidden"},
            )


def test_calibration_provider_snapshot_freezes_payloads_after_validation() -> None:
    extra_scalars: dict[str, ScalarValue] = {"sample_count": 3}
    quality: dict[str, ScalarValue] = {"mean_error_px": 4.2}
    snapshot = CalibrationProviderSnapshot(
        stage=CalibrationStage.RESULT,
        message="Ready",
        quality=quality,
        extra_scalars=extra_scalars,
    )

    extra_scalars["window_title"] = "forbidden"
    quality["raw_frame"] = "forbidden"

    payload = snapshot.to_scalar_payload()

    assert "window_title" not in payload
    assert payload["sample_count"] == 3
    assert payload["quality"] == {"mean_error_px": 4.2}


def test_calibration_provider_snapshot_rejects_reserved_payload_overrides() -> None:
    with pytest.raises(ValueError, match="reserved calibration payload field"):
        CalibrationProviderSnapshot(
            stage=CalibrationStage.READINESS,
            message="Camera ready",
            extra_scalars={"stage": "target_sequence"},
        )


def test_calibration_provider_snapshot_rejects_unknown_extra_scalars() -> None:
    for field in ["window_name", "active_uri", "link", "selection_text", "app_name"]:
        with pytest.raises(ValueError, match="unsupported calibration payload field"):
            CalibrationProviderSnapshot(
                stage=CalibrationStage.READINESS,
                message="Camera ready",
                extra_scalars={field: "forbidden content"},
            )


def test_calibration_provider_snapshot_rejects_content_values_for_metric_fields() -> None:
    with pytest.raises(ValueError, match="must be a non-negative integer"):
        CalibrationProviderSnapshot(
            stage=CalibrationStage.READINESS,
            message="Camera ready",
            extra_scalars={"sample_count": "/Users/alice/private/document.txt"},
        )
    with pytest.raises(ValueError, match="must be a finite non-negative number"):
        CalibrationProviderSnapshot(
            stage=CalibrationStage.RESULT,
            message="Ready",
            quality={"mean_error_px": "https://example.invalid/secret"},
        )
    with pytest.raises(ValueError, match="unsupported calibration recommendation"):
        CalibrationProviderSnapshot(
            stage=CalibrationStage.RESULT,
            message="Ready",
            quality={"recommendation": "Secret Client Plan"},
        )


def test_calibration_provider_snapshot_rejects_content_bearing_messages() -> None:
    for message in [
        "/Users/alice/private/document.txt",
        "https://example.invalid/secret",
        "window title: Secret Client Plan",
        "Calibration unavailable: /tmp/private-client-plan.txt",
        "PUPIL_TRACKER_PATH=/tmp/pupil-tracker",
        "Calibration unavailable: ~/.ssh/config",
        "Calibration unavailable: C:\\Users\\alice\\secret.txt",
    ]:
        with pytest.raises(ValueError, match="forbidden calibration snapshot message"):
            CalibrationProviderSnapshot(stage=CalibrationStage.READINESS, message=message)


def test_calibration_provider_snapshot_rejects_non_finite_metrics() -> None:
    for value in [float("nan"), float("inf")]:
        with pytest.raises(ValueError, match="must be a finite non-negative number"):
            CalibrationProviderSnapshot(
                stage=CalibrationStage.RESULT,
                message="Ready",
                quality={"mean_error_px": value},
            )


def test_calibration_provider_snapshot_rejects_invalid_fixed_field_types() -> None:
    path_value = cast(Any, "/tmp/private-client-plan.txt")
    with pytest.raises(ValueError, match="stage must be CalibrationStage"):
        CalibrationProviderSnapshot(stage=path_value, message="Camera ready")
    with pytest.raises(ValueError, match="camera_available must be bool"):
        CalibrationProviderSnapshot(
            stage=CalibrationStage.READINESS,
            message="Camera ready",
            camera_available=path_value,
        )
    with pytest.raises(ValueError, match="tracker_available must be bool"):
        CalibrationProviderSnapshot(
            stage=CalibrationStage.READINESS,
            message="Camera ready",
            tracker_available=path_value,
        )
    with pytest.raises(ValueError, match="current_target must be CalibrationTargetPoint"):
        CalibrationProviderSnapshot(
            stage=CalibrationStage.READINESS,
            message="Camera ready",
            current_target=path_value,
        )
    with pytest.raises(ValueError, match="result_status must be CalibrationStatus"):
        CalibrationProviderSnapshot(
            stage=CalibrationStage.RESULT,
            message="Ready",
            result_status=path_value,
        )


def test_calibration_target_point_rejects_invalid_runtime_values() -> None:
    path_value = cast(Any, "/tmp/private-client-plan.txt")
    with pytest.raises(ValueError, match="calibration target x must be finite"):
        CalibrationTargetPoint(x=path_value, y=0.5, index=1, total=1)
    with pytest.raises(ValueError, match="calibration target index must be a positive integer"):
        CalibrationTargetPoint(x=0.5, y=0.5, index=cast(Any, True), total=1)
