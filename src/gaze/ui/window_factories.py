"""Runtime AppKit window factory seams for settings and developer panels."""

from __future__ import annotations

from typing import Any

from gaze.ui.developer_actions import DeveloperPanelActions


def create_settings_window(appkit: Any | None) -> Any | None:
    if appkit is None:
        return None
    return appkit.NSWindow.alloc().init()


def create_developer_panel(
    appkit: Any | None,
    *,
    development_mode: bool,
    actions: DeveloperPanelActions | None = None,
) -> Any | None:
    if appkit is None or not development_mode or actions is None:
        return None
    return appkit.NSWindow.alloc().init()
