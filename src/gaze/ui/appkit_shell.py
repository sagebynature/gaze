"""Runtime AppKit shell builders.

Importing this module must not import AppKit. Call ``build_menu_bar_app`` only
from runtime launch code.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any, Protocol, cast

from gaze.core.state import GazeAppState
from gaze.desktop.activation import ActivationOutcome
from gaze.hotkeys.bindings import (
    GAZE_TOGGLE_ACTION,
    MANUAL_ACTIVATE_ACTION,
    HotkeyBinding,
    HotkeySettings,
    default_hotkey_settings,
)
from gaze.hotkeys.commands import GazeCommandController
from gaze.ui.menu_model import MenuItem, menu_items_for_state
from gaze.ui.window_factories import create_developer_panel, create_settings_window

_REAL_PREVIEW_TICK_INTERVAL_SECONDS = 1.0 / 30.0


class RuntimeHotkeyRegistry:
    """Small runtime seam for manual hotkeys.

    The first prototype keeps hotkey effects injectable and testable. Platform-specific
    global registration can wrap this registry later without changing command logic.
    """

    def __init__(self, *, unavailable_hotkeys: tuple[str, ...] = ()) -> None:
        self._handlers: dict[str, Callable[[], None]] = {}
        self._unavailable_hotkeys = set(unavailable_hotkeys)
        self.feedback_messages: list[str] = []

    def register(self, hotkey: str, handler: Callable[[], None], *, label: str) -> None:
        if hotkey in self._unavailable_hotkeys:
            self.feedback_messages.append(f"unavailable {hotkey} for {label}")
            return
        if hotkey in self._handlers:
            self.feedback_messages.append(f"conflict {hotkey} for {label}")
            return
        self._handlers[hotkey] = handler

    def trigger(self, hotkey: str) -> None:
        handler = self._handlers.get(hotkey)
        if handler is not None:
            handler()


class RuntimeTickDriver:
    """NSTimer target that advances the real preview loop."""

    def __init__(self, controller: Any, refresh: Callable[[], None]) -> None:
        self._controller = controller
        self._refresh = refresh

    def tick_(self, sender: Any | None = None) -> None:
        tick = getattr(self._controller, "tick", None)
        if tick is None:
            return
        now_seconds = time.monotonic()
        tick(now_seconds=now_seconds, now_ms=int(now_seconds * 1000))
        self._refresh()


class MenuRuntimeController(Protocol):
    """Controller surface needed by the menu-bar shell."""

    state: GazeAppState

    def activate(self) -> ActivationOutcome:
        """Request manual target activation."""
        ...

    def enable_gaze(self) -> None:
        """Enable gaze preview."""
        ...

    def disable_gaze(self) -> None:
        """Disable gaze preview."""
        ...

    def start_calibration(self) -> None:
        """Start calibration."""
        ...

    def toggle_border_enabled(self) -> None:
        """Toggle target border visibility."""
        ...

    def toggle_heatmap_enabled(self) -> None:
        """Toggle heatmap visibility."""
        ...


@dataclass
class MenuBarRuntime:
    appkit: Any
    app: Any
    status_item: Any
    menu: Any
    action_dispatcher: MenuActionDispatcher
    controller: MenuRuntimeController
    development_mode: bool
    hotkeys: RuntimeHotkeyRegistry
    tick_driver: RuntimeTickDriver | None = None
    tick_timer: Any | None = None

    def refresh_menu(self) -> None:
        self.menu.removeAllItems()
        _populate_menu(
            self.appkit,
            self.menu,
            self.controller,
            self.development_mode,
            self.action_dispatcher,
            tuple(self.hotkeys.feedback_messages),
        )


class MenuActionDispatcher:
    """Runtime target for menu item actions."""

    def __init__(
        self,
        *,
        appkit: Any,
        controller: MenuRuntimeController,
        development_mode: bool,
    ) -> None:
        self._appkit = appkit
        self._controller = controller
        self._commands = GazeCommandController(controller)
        self._development_mode = development_mode
        self._refresh: Callable[[], None] | None = None
        self.settings_window: Any | None = None
        self.developer_panel: Any | None = None

    def set_refresh_callback(self, refresh: Callable[[], None]) -> None:
        self._refresh = refresh

    def _refresh_menu(self) -> None:
        if self._refresh is not None:
            self._refresh()

    def manual_activate_(self, sender: Any | None = None) -> None:
        self._commands.manual_activate_command()
        self._refresh_menu()

    def toggle_gaze_(self, sender: Any | None = None) -> None:
        self._commands.toggle_gaze_command()
        self._refresh_menu()

    def settings_(self, sender: Any | None = None) -> None:
        self.settings_window = create_settings_window(self._appkit)
        self._refresh_menu()

    def developer_panel_(self, sender: Any | None = None) -> None:
        developer_actions = getattr(self._controller, "developer_actions", None)
        if developer_actions is None:
            self._refresh_menu()
            return
        self.developer_panel = create_developer_panel(
            self._appkit,
            development_mode=self._development_mode,
            actions=developer_actions(),
            after_action=self._refresh_menu,
        )
        self._refresh_menu()

    def toggle_border_(self, sender: Any | None = None) -> None:
        self._controller.toggle_border_enabled()
        self._refresh_menu()

    def toggle_heatmap_(self, sender: Any | None = None) -> None:
        self._controller.toggle_heatmap_enabled()
        self._refresh_menu()

    def recalibrate_(self, sender: Any | None = None) -> None:
        self._commands.recalibrate_command()
        self._refresh_menu()

    def quit_(self, sender: Any | None = None) -> None:
        self._appkit.NSApplication.sharedApplication().terminate_(sender)


def _load_appkit() -> Any:
    return cast(Any, import_module("AppKit"))


def selector_for_menu_action(action_name: str) -> str | None:
    selectors = {
        "manual_activate": "manual_activate:",
        "toggle_gaze": "toggle_gaze:",
        "toggle_border": "toggle_border:",
        "toggle_heatmap": "toggle_heatmap:",
        "recalibrate": "recalibrate:",
        "settings": "settings:",
        "developer_panel": "developer_panel:",
        "quit": "quit:",
    }
    return selectors.get(action_name)


def _modifier_mask(appkit: Any, modifier_names: tuple[str, ...]) -> int:
    mask = 0
    for modifier in modifier_names:
        if modifier == "cmd":
            mask |= int(appkit.NSEventModifierFlagCommand)
        if modifier == "option":
            mask |= int(appkit.NSEventModifierFlagOption)
    return mask


def _menu_item(appkit: Any, item: MenuItem, dispatcher: MenuActionDispatcher) -> Any:
    action = selector_for_menu_action(item.action) if item.action is not None else None
    menu_item = appkit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        item.label,
        action,
        item.key_equivalent,
    )
    if item.modifier_names and hasattr(menu_item, "setKeyEquivalentModifierMask_"):
        menu_item.setKeyEquivalentModifierMask_(_modifier_mask(appkit, item.modifier_names))
    if action is not None:
        menu_item.setTarget_(dispatcher)
    return menu_item


def _populate_menu(
    appkit: Any,
    menu: Any,
    controller: MenuRuntimeController,
    development_mode: bool,
    dispatcher: MenuActionDispatcher,
    hotkey_feedback: tuple[str, ...] = (),
) -> None:
    items = menu_items_for_state(controller.state)
    for message in hotkey_feedback:
        items.append(MenuItem(f"Hotkeys: {message}"))
    if development_mode:
        items.append(MenuItem("Open Developer Panel", "developer_panel"))
    for item in items:
        menu.addItem_(_menu_item(appkit, item, dispatcher))


def build_menu_bar_app(
    *,
    appkit: Any | None = None,
    controller: MenuRuntimeController,
    development_mode: bool,
    hotkey_settings: HotkeySettings | None = None,
    unavailable_hotkeys: tuple[str, ...] = (),
) -> MenuBarRuntime:
    runtime_appkit = appkit or _load_appkit()
    app = runtime_appkit.NSApplication.sharedApplication()
    app.setActivationPolicy_(runtime_appkit.NSApplicationActivationPolicyAccessory)

    status_item = runtime_appkit.NSStatusBar.systemStatusBar().statusItemWithLength_(
        runtime_appkit.NSSquareStatusItemLength
    )
    status_item.button().setTitle_("◉")

    dispatcher = MenuActionDispatcher(
        appkit=runtime_appkit,
        controller=controller,
        development_mode=development_mode,
    )

    menu = runtime_appkit.NSMenu()
    hotkeys = RuntimeHotkeyRegistry(unavailable_hotkeys=unavailable_hotkeys)
    runtime = MenuBarRuntime(
        appkit=runtime_appkit,
        app=app,
        status_item=status_item,
        menu=menu,
        action_dispatcher=dispatcher,
        controller=controller,
        development_mode=development_mode,
        hotkeys=hotkeys,
    )
    dispatcher.set_refresh_callback(runtime.refresh_menu)
    if hasattr(runtime_appkit, "NSTimer"):
        runtime.tick_driver = RuntimeTickDriver(controller, runtime.refresh_menu)
        timer_class = runtime_appkit.NSTimer
        schedule_timer_name = "scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_"
        schedule_timer = getattr(timer_class, schedule_timer_name)
        runtime.tick_timer = schedule_timer(
            _REAL_PREVIEW_TICK_INTERVAL_SECONDS,
            runtime.tick_driver,
            "tick:",
            None,
            True,
        )
    settings = hotkey_settings or default_hotkey_settings()
    _register_runtime_hotkeys(settings, hotkeys, dispatcher)
    _populate_menu(
        runtime_appkit,
        menu,
        controller,
        development_mode,
        dispatcher,
        tuple(hotkeys.feedback_messages),
    )
    status_item.setMenu_(menu)
    return runtime


def _register_runtime_hotkeys(
    settings: HotkeySettings,
    hotkeys: RuntimeHotkeyRegistry,
    dispatcher: MenuActionDispatcher,
) -> None:
    handlers: dict[str, tuple[Callable[[], None], str]] = {
        MANUAL_ACTIVATE_ACTION: (dispatcher.manual_activate_, "Activate Target"),
        GAZE_TOGGLE_ACTION: (dispatcher.toggle_gaze_, "Toggle Gaze"),
    }
    for binding in settings.bindings:
        _register_runtime_hotkey(binding, hotkeys, handlers)


def _register_runtime_hotkey(
    binding: HotkeyBinding,
    hotkeys: RuntimeHotkeyRegistry,
    handlers: dict[str, tuple[Callable[[], None], str]],
) -> None:
    if not binding.enabled:
        return
    handler = handlers.get(binding.action)
    if handler is None:
        return
    callback, label = handler
    hotkeys.register(binding.hotkey, callback, label=label)
