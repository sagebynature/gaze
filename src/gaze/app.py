"""Native macOS application bootstrap.

The bootstrap is deliberately side-effect light: importing this module does not
start the camera, enumerate windows, register hotkeys, or activate apps.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import FakeActivationService
from gaze.overlays.border import RecordingBorderOverlay, create_appkit_border_overlay
from gaze.ui.appkit_shell import build_menu_bar_app


def main() -> int:
    """Launch the AppKit menu-bar shell when PyObjC is available."""

    try:
        appkit = cast(Any, import_module("AppKit"))
    except ModuleNotFoundError as exc:
        print(
            "Gaze requires PyObjC/AppKit on macOS. Run `make sync` on macOS before launching."
        )
        raise SystemExit(1) from exc

    overlay = create_appkit_border_overlay(appkit) or RecordingBorderOverlay()
    controller = FakePrototypeController(
        overlay=overlay,
        activation=FakeActivationService(),
    )
    build_menu_bar_app(appkit=appkit, controller=controller, development_mode=True)
    return _run_event_loop(appkit)


def _run_event_loop(appkit: Any) -> int:
    """Run the PyObjC AppKit event loop with the supported signature."""

    return int(appkit.NSApplicationMain([]) or 0)
