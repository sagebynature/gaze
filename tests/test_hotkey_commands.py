from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import ActivationOutcome, FakeActivationService
from gaze.dev.fakes import FakeTarget
from gaze.hotkeys.commands import GazeCommandController
from gaze.overlays.border import RecordingBorderOverlay


def test_toggle_gaze_command_enables_and_disables() -> None:
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    commands = GazeCommandController(controller)

    commands.toggle_gaze_command()
    assert controller.state.flags.gaze_enabled is True

    commands.toggle_gaze_command()
    assert controller.state.flags.gaze_enabled is False


def test_manual_activate_command_routes_to_fake_activation() -> None:
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    commands = GazeCommandController(controller)
    commands.toggle_gaze_command()
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))
    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    assert commands.manual_activate_command() == ActivationOutcome.SUCCESS
