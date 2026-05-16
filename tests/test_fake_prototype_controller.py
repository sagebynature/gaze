from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import ActivationOutcome, FakeActivationService
from gaze.dev.fakes import FakeTarget
from gaze.overlays.border import RecordingBorderOverlay


def test_locked_fake_target_shows_overlay_after_stability_threshold() -> None:
    overlay = RecordingBorderOverlay()
    controller = FakePrototypeController(overlay=overlay, activation=FakeActivationService())
    controller.enable_gaze()
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))

    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    assert controller.state.current_target is not None
    assert controller.state.current_target.locked is True
    assert overlay.visible is True


def test_disable_hides_overlay_and_blocks_activation() -> None:
    overlay = RecordingBorderOverlay()
    service = FakeActivationService()
    controller = FakePrototypeController(overlay=overlay, activation=service)
    controller.enable_gaze()
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))
    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    controller.disable_gaze()
    outcome = controller.activate()

    assert overlay.visible is False
    assert outcome == ActivationOutcome.DISABLED
    assert service.calls == []


def test_activation_success_updates_status() -> None:
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    controller.enable_gaze()
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))
    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    outcome = controller.activate()

    assert outcome == ActivationOutcome.SUCCESS
    assert controller.state.last_status_message == "Activated Terminal"


def test_no_target_activation_reports_no_target() -> None:
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    controller.enable_gaze()

    outcome = controller.activate()

    assert outcome == ActivationOutcome.NO_TARGET
    assert controller.state.last_status_message == "No target"


def test_tick_while_disabled_does_not_show_target_or_overlay() -> None:
    overlay = RecordingBorderOverlay()
    controller = FakePrototypeController(overlay=overlay, activation=FakeActivationService())
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))

    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    assert controller.state.current_target is None
    assert overlay.visible is False
    assert controller.activate() == ActivationOutcome.DISABLED
