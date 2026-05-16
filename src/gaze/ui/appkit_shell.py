"""Runtime AppKit shell builders.

Importing this module must not import AppKit. Call ``build_menu_bar_app`` only
from runtime launch code.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any, cast

from gaze.core.prototype import FakePrototypeController
from gaze.hotkeys.bindings import GAZE_TOGGLE_HOTKEY, MANUAL_ACTIVATE_HOTKEY
from gaze.hotkeys.commands import GazeCommandController
from gaze.ui.menu_model import MenuItem, menu_items_for_state
from gaze.ui.window_factories import create_developer_panel, create_settings_window


class RuntimeHotkeyRegistry:
    """Small runtime seam for manual hotkeys.

    The first prototype keeps hotkey effects injectable and testable. Platform-specific
    global registration can wrap this registry later without changing command logic.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[], None]] = {}

    def register(self, hotkey: str, handler: Callable[[], None]) -> None:
        self._handlers[hotkey] = handler

    def trigger(self, hotkey: str) -> None:
        handler = self._handlers.get(hotkey)
        if handler is not None:
            handler()


@dataclass
class MenuBarRuntime:
    appkit: Any
    app: Any
    status_item: Any
    menu: Any
    action_dispatcher: MenuActionDispatcher
    controller: FakePrototypeController
    development_mode: bool
    hotkeys: RuntimeHotkeyRegistry

    def refresh_menu(self) -> None:
        self.menu.removeAllItems()
        _populate_menu(
            self.appkit,
            self.menu,
            self.controller,
            self.development_mode,
            self.action_dispatcher,
        )


class MenuActionDispatcher:
    """Runtime target for menu item actions."""

    def __init__(
        self,
        *,
        appkit: Any,
        controller: FakePrototypeController,
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
        self.developer_panel = create_developer_panel(
            self._appkit,
            development_mode=self._development_mode,
            actions=self._controller.developer_actions(),
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
        self._controller.start_fake_recalibration()
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
    controller: FakePrototypeController,
    development_mode: bool,
    dispatcher: MenuActionDispatcher,
) -> None:
    items = menu_items_for_state(controller.state)
    if development_mode:
        items.append(MenuItem("Open Developer Panel", "developer_panel"))
    for item in items:
        menu.addItem_(_menu_item(appkit, item, dispatcher))


def build_menu_bar_app(
    *,
    appkit: Any | None = None,
    controller: FakePrototypeController,
    development_mode: bool,
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
    hotkeys = RuntimeHotkeyRegistry()
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
    _populate_menu(runtime_appkit, menu, controller, development_mode, dispatcher)
    status_item.setMenu_(menu)
    hotkeys.register(MANUAL_ACTIVATE_HOTKEY, dispatcher.manual_activate_)
    hotkeys.register(GAZE_TOGGLE_HOTKEY, dispatcher.toggle_gaze_)
    return runtime
