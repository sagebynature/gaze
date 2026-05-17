from gaze.core.state import CalibrationStatus
from gaze.tracking.calibration import (
    CalibrationProviderSnapshot,
    CalibrationStage,
    CalibrationTargetPoint,
)
from gaze.ui.developer_panel import developer_controls
from gaze.ui.setup_window import (
    calibration_wizard_steps,
    render_calibration_wizard_text,
    setup_sections,
)


def test_setup_window_contains_mvp_essentials_only() -> None:
    sections = setup_sections()
    labels = [section.label for section in sections]

    assert labels == [
        "Privacy & Trust",
        "Calibration",
        "Gaze Control",
        "Target Border",
        "Hotkeys",
        "Auto-Activate",
        "Activation Delay",
        "Privacy & Diagnostics",
        "Reset Calibration",
    ]
    assert "Heatmap" not in labels
    assert "Per-App Policy" not in labels
    assert "Developer" not in labels


def test_gaze_owned_calibration_wizard_models_four_trust_steps() -> None:
    snapshot = CalibrationProviderSnapshot(
        stage=CalibrationStage.TARGET_SEQUENCE,
        message="Follow the target",
        current_target=CalibrationTargetPoint(x=0.5, y=0.5, index=2, total=5),
        progress=0.4,
    )

    steps = calibration_wizard_steps(snapshot)

    assert [step.label for step in steps] == [
        "Privacy",
        "Readiness",
        "Calibration Targets",
        "Result",
    ]
    assert [step.state for step in steps] == ["complete", "complete", "current", "pending"]
    assert steps[0].description == "Camera access starts only when you ask to calibrate."
    assert steps[2].detail == "Target 2 of 5"


def test_gaze_owned_calibration_wizard_renders_content_safe_copy() -> None:
    text = render_calibration_wizard_text(
        CalibrationProviderSnapshot(
            stage=CalibrationStage.RESULT,
            message="Ready",
            result_status=CalibrationStatus.READY,
            quality={"mean_error_px": 3.2, "recommendation": "good"},
        )
    )

    assert "Gaze Calibration" in text
    assert "No recording, screenshots, window titles, URLs, filenames, or desktop content" in text
    assert "Ready" in text
    assert "mean_error_px" not in text
    forbidden = ["/Users/", "/tmp/", "http://", "https://", "window title:"]
    assert not any(token in text for token in forbidden)


def test_developer_panel_controls_are_separate_from_setup() -> None:
    controls = developer_controls()
    labels = [control.label for control in controls]

    assert "Start Scripted Demo" in labels
    assert "Set Fake Target" in labels
    assert "Set Fake Target Bounds" in labels
    assert "Set Fake Confidence" in labels
    assert "Set Fake Lock State" in labels
    assert "Set Fake Frontmost App" in labels
    assert "Trigger Activation Success" in labels
    assert "Trigger Activation Failure" in labels
    assert "Trigger No Target" in labels
    assert "Trigger Degraded" in labels


def test_runtime_window_factories_are_import_safe_without_appkit() -> None:
    from gaze.ui.window_factories import create_developer_panel, create_settings_window

    assert create_settings_window(appkit=None) is None
    assert create_developer_panel(appkit=None, development_mode=True) is None


def test_developer_panel_is_development_gated() -> None:
    from gaze.ui.window_factories import create_developer_panel

    assert create_developer_panel(appkit=object(), development_mode=False) is None


def test_developer_actions_drive_fake_controller() -> None:
    from gaze.core.prototype import FakePrototypeController
    from gaze.desktop.activation import ActivationOutcome, FakeActivationService
    from gaze.overlays.border import RecordingBorderOverlay
    from gaze.ui.developer_actions import DeveloperPanelActions

    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    actions = DeveloperPanelActions(controller)

    actions.set_fake_target(app_name="Terminal", x=10, y=20, width=800, height=600, confidence=0.91)
    actions.enable_gaze()
    actions.tick(now_ms=1000)
    actions.tick(now_ms=1400)

    assert controller.state.current_target is not None
    assert controller.state.current_target.app_name == "Terminal"
    assert actions.manual_activate() == ActivationOutcome.SUCCESS


def test_developer_actions_cover_every_fake_control() -> None:
    from gaze.core.prototype import FakePrototypeController
    from gaze.desktop.activation import ActivationOutcome, FakeActivationService
    from gaze.overlays.border import RecordingBorderOverlay
    from gaze.ui.developer_actions import DeveloperPanelActions

    service = FakeActivationService()
    controller = FakePrototypeController(overlay=RecordingBorderOverlay(), activation=service)
    actions = DeveloperPanelActions(controller)

    actions.start_scripted_demo()
    actions.advance_scripted_demo(now_ms=1000)
    assert controller.state.last_status_message == "Scripted demo running"

    actions.stop_scripted_demo()
    assert controller.state.last_status_message == "Scripted demo stopped"

    actions.set_fake_target(app_name="Terminal", x=10, y=20, width=800, height=600, confidence=0.5)
    actions.set_fake_target_bounds(x=20, y=30, width=700, height=500)
    actions.set_fake_confidence(0.96)
    actions.set_fake_lock_state(True)
    assert controller.state.current_target is not None
    assert controller.state.current_target.confidence == 0.96
    assert controller.state.current_target.locked is True

    actions.set_fake_frontmost_app("Terminal")
    assert actions.manual_activate() == ActivationOutcome.ALREADY_FRONTMOST

    actions.trigger_activation_failure()
    actions.set_fake_frontmost_app(None)
    assert actions.manual_activate() == ActivationOutcome.UNAVAILABLE

    actions.trigger_activation_success()
    assert actions.manual_activate() == ActivationOutcome.SUCCESS

    actions.trigger_no_target()
    assert controller.state.current_target is None

    actions.trigger_degraded()
    assert controller.state.readiness.calibration.value == "degraded"


def test_stop_scripted_demo_clears_scripted_target_and_overlay() -> None:
    from gaze.core.prototype import FakePrototypeController
    from gaze.desktop.activation import FakeActivationService
    from gaze.overlays.border import RecordingBorderOverlay
    from gaze.ui.developer_actions import DeveloperPanelActions

    overlay = RecordingBorderOverlay()
    controller = FakePrototypeController(overlay=overlay, activation=FakeActivationService())
    actions = DeveloperPanelActions(controller)

    actions.start_scripted_demo()
    actions.tick(now_ms=1000)
    actions.tick(now_ms=1400)
    assert controller.state.current_target is not None
    assert overlay.visible is True

    actions.stop_scripted_demo()
    actions.tick(now_ms=1800)

    assert controller.state.current_target is None
    assert overlay.visible is False


def test_developer_lock_and_bounds_controls_keep_overlay_in_sync() -> None:
    from gaze.core.prototype import FakePrototypeController
    from gaze.desktop.activation import FakeActivationService
    from gaze.overlays.border import RecordingBorderOverlay
    from gaze.ui.developer_actions import DeveloperPanelActions

    overlay = RecordingBorderOverlay()
    controller = FakePrototypeController(overlay=overlay, activation=FakeActivationService())
    actions = DeveloperPanelActions(controller)
    actions.enable_gaze()
    actions.set_fake_target(app_name="Terminal", x=10, y=20, width=800, height=600, confidence=0.5)

    actions.set_fake_lock_state(True)
    assert overlay.visible is True

    actions.set_fake_target_bounds(x=20, y=30, width=700, height=500)
    assert overlay.last_candidate is not None
    assert overlay.last_candidate.bounds_x == 20
    assert overlay.last_candidate.bounds_width == 700

    actions.set_fake_lock_state(False)
    assert overlay.visible is False


def test_developer_panel_action_target_makes_controls_visible_and_refreshes() -> None:
    from gaze.core.prototype import FakePrototypeController
    from gaze.desktop.activation import FakeActivationService
    from gaze.overlays.border import RecordingBorderOverlay
    from gaze.ui.developer_actions import DeveloperPanelActions
    from gaze.ui.window_factories import DeveloperPanelActionTarget

    overlay = RecordingBorderOverlay()
    controller = FakePrototypeController(overlay=overlay, activation=FakeActivationService())
    refreshes = 0

    def refresh() -> None:
        nonlocal refreshes
        refreshes += 1

    target = DeveloperPanelActionTarget(DeveloperPanelActions(controller), after_action=refresh)

    target.set_fake_target_()

    assert controller.state.flags.gaze_enabled is True
    assert controller.state.current_target is not None
    assert controller.state.current_target.app_name == "Terminal"
    assert controller.state.current_target.locked is True
    assert overlay.visible is True
    assert refreshes == 1

    target.trigger_no_target_()

    assert controller.state.current_target is None
    assert overlay.visible is False
    assert refreshes == 2


def test_start_scripted_demo_button_immediately_surfaces_locked_target() -> None:
    from gaze.core.prototype import FakePrototypeController
    from gaze.desktop.activation import FakeActivationService
    from gaze.overlays.border import RecordingBorderOverlay
    from gaze.ui.developer_actions import DeveloperPanelActions
    from gaze.ui.window_factories import DeveloperPanelActionTarget

    overlay = RecordingBorderOverlay()
    controller = FakePrototypeController(overlay=overlay, activation=FakeActivationService())
    target = DeveloperPanelActionTarget(DeveloperPanelActions(controller))

    target.start_scripted_demo_()

    assert controller.state.flags.gaze_enabled is True
    assert controller.state.current_target is not None
    assert controller.state.current_target.locked is True
    assert overlay.visible is True
