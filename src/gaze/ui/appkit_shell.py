"""Runtime AppKit shell builders.

Importing this module must not import AppKit. Call ``build_menu_bar_app`` only
from runtime launch code.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, cast

from gaze.core.prototype import FakePrototypeController
from gaze.hotkeys.commands import GazeCommandController
from gaze.ui.menu_model import MenuItem, menu_items_for_state
from gaze.ui.window_factories import create_developer_panel, create_settings_window


@dataclass(frozen=True)
class MenuBarRuntime:
    app: Any
    status_item: Any
    menu: Any
    action_dispatcher: MenuActionDispatcher


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
        self.settings_window: Any | None = None
        self.developer_panel: Any | None = None

    def toggle_gaze_(self, sender: Any | None = None) -> None:
        self._commands.toggle_gaze_command()

    def settings_(self, sender: Any | None = None) -> None:
        self.settings_window = create_settings_window(self._appkit)

    def developer_panel_(self, sender: Any | None = None) -> None:
        self.developer_panel = create_developer_panel(
            self._appkit,
            development_mode=self._development_mode,
            actions=self._controller.developer_actions(),
        )

    def toggle_border_(self, sender: Any | None = None) -> None:
        self._controller.toggle_border_enabled()

    def toggle_heatmap_(self, sender: Any | None = None) -> None:
        self._controller.toggle_heatmap_enabled()

    def recalibrate_(self, sender: Any | None = None) -> None:
        self._controller.start_fake_recalibration()

    def quit_(self, sender: Any | None = None) -> None:
        self._appkit.NSApplication.sharedApplication().terminate_(sender)


def _load_appkit() -> Any:
    return cast(Any, import_module("AppKit"))


def selector_for_menu_action(action_name: str) -> str | None:
    selectors = {
        "toggle_gaze": "toggle_gaze:",
        "toggle_border": "toggle_border:",
        "toggle_heatmap": "toggle_heatmap:",
        "recalibrate": "recalibrate:",
        "settings": "settings:",
        "developer_panel": "developer_panel:",
        "quit": "quit:",
    }
    return selectors.get(action_name)


def _menu_item(appkit: Any, item: MenuItem, dispatcher: MenuActionDispatcher) -> Any:
    action = selector_for_menu_action(item.action) if item.action is not None else None
    menu_item = appkit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        item.label,
        action,
        "",
    )
    if action is not None:
        menu_item.setTarget_(dispatcher)
    return menu_item


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
    items = menu_items_for_state(controller.state)
    if development_mode:
        items.append(MenuItem("Open Developer Panel", "developer_panel"))
    for item in items:
        menu.addItem_(_menu_item(runtime_appkit, item, dispatcher))
    status_item.setMenu_(menu)
    return MenuBarRuntime(app=app, status_item=status_item, menu=menu, action_dispatcher=dispatcher)
