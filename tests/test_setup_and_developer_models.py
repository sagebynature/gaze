from gaze.ui.developer_panel import developer_controls
from gaze.ui.setup_window import setup_sections


def test_setup_window_contains_mvp_essentials_only() -> None:
    sections = setup_sections()
    labels = [section.label for section in sections]

    assert labels == [
        "Privacy & Trust",
        "Calibration",
        "Hotkeys",
        "Border",
        "Heatmap",
        "Diagnostics",
    ]
    assert "Auto Activation" not in labels
    assert "Per-App Policy" not in labels


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
