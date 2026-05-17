from __future__ import annotations

from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import FakeActivationService
from gaze.hotkeys.global_hotkeys import CarbonGlobalHotkeyRegistry
from gaze.overlays.border import RecordingBorderOverlay
from gaze.ui.appkit_shell import build_menu_bar_app
from test_appkit_shell_model import FakeAppKit


class FakeCarbonHotkeyAPI:
    def __init__(self) -> None:
        self.registered: list[tuple[int, int, int]] = []
        self.next_ref = object()

    def register_event_hotkey(self, key_code: int, modifiers: int, hotkey_id: int) -> object:
        self.registered.append((key_code, modifiers, hotkey_id))
        return self.next_ref


class RecordingHandler:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


def test_carbon_registry_registers_cmd_g_as_global_hotkey_and_dispatches_press() -> None:
    carbon = FakeCarbonHotkeyAPI()
    registry = CarbonGlobalHotkeyRegistry(carbon=carbon)
    handler = RecordingHandler()

    registry.register("cmd+g", handler, label="Activate Target")

    assert carbon.registered == [(5, 256, 1)]
    registry.dispatch_hotkey_id(1)
    assert handler.calls == 1


def test_carbon_registry_surfaces_unavailable_feedback_for_unsupported_bindings() -> None:
    carbon = FakeCarbonHotkeyAPI()
    registry = CarbonGlobalHotkeyRegistry(carbon=carbon)

    registry.register("shift+g", lambda: None, label="Unsupported")

    assert carbon.registered == []
    assert registry.feedback_messages == ["unavailable shift+g for Unsupported"]


def test_menu_bar_runtime_can_use_carbon_registry_for_global_hotkeys() -> None:
    appkit = FakeAppKit()
    carbon = FakeCarbonHotkeyAPI()
    hotkeys = CarbonGlobalHotkeyRegistry(carbon=carbon)
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )

    runtime = build_menu_bar_app(
        appkit=appkit,
        controller=controller,
        development_mode=True,
        hotkeys=hotkeys,
    )

    runtime.hotkeys.trigger("option+cmd+g")
    assert controller.state.flags.gaze_enabled is True
    assert carbon.registered == [(5, 256, 1), (5, 2304, 2)]
