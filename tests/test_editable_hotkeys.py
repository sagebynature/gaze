from __future__ import annotations

from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import FakeActivationService
from gaze.hotkeys.bindings import (
    GAZE_TOGGLE_ACTION,
    MANUAL_ACTIVATE_ACTION,
    HotkeySettings,
    default_hotkey_settings,
)
from gaze.overlays.border import RecordingBorderOverlay
from gaze.ui.appkit_shell import build_menu_bar_app
from gaze.ui.setup_window import setup_sections
from test_appkit_shell_model import FakeAppKit


def test_hotkey_settings_can_disable_and_rebind_defaults() -> None:
    settings = default_hotkey_settings()

    updated = settings.disable(MANUAL_ACTIVATE_ACTION).rebind(GAZE_TOGGLE_ACTION, "ctrl+g")

    assert updated.binding_for(MANUAL_ACTIVATE_ACTION).enabled is False
    assert updated.binding_for(GAZE_TOGGLE_ACTION).hotkey == "ctrl+g"


def test_runtime_uses_rebound_hotkeys_and_skips_disabled_bindings() -> None:
    appkit = FakeAppKit()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    settings = HotkeySettings.default().disable(MANUAL_ACTIVATE_ACTION).rebind(
        GAZE_TOGGLE_ACTION,
        "ctrl+g",
    )

    runtime = build_menu_bar_app(
        appkit=appkit,
        controller=controller,
        development_mode=True,
        hotkey_settings=settings,
    )

    runtime.hotkeys.trigger("option+cmd+g")
    assert controller.state.flags.gaze_enabled is False

    runtime.hotkeys.trigger("ctrl+g")
    assert controller.state.flags.gaze_enabled is True

    runtime.hotkeys.trigger("cmd+g")
    assert controller.state.last_status_message == "Gaze ready"


def test_runtime_surfaces_unavailable_hotkey_registration_feedback() -> None:
    appkit = FakeAppKit()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )

    runtime = build_menu_bar_app(
        appkit=appkit,
        controller=controller,
        development_mode=True,
        unavailable_hotkeys=("cmd+g",),
    )

    assert "Hotkeys: unavailable cmd+g for Activate Target" in runtime.status_item.menu.items
    runtime.hotkeys.trigger("cmd+g")
    assert controller.state.last_status_message == "Gaze off"


def test_runtime_surfaces_conflicting_hotkey_feedback() -> None:
    appkit = FakeAppKit()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    settings = HotkeySettings.default().rebind(GAZE_TOGGLE_ACTION, "cmd+g")

    runtime = build_menu_bar_app(
        appkit=appkit,
        controller=controller,
        development_mode=True,
        hotkey_settings=settings,
    )

    assert "Hotkeys: conflict cmd+g for Toggle Gaze" in runtime.status_item.menu.items


def test_settings_window_exposes_hotkey_editing_action() -> None:
    sections = setup_sections()

    assert any(section.label == "Hotkeys" and section.action == "hotkeys" for section in sections)
