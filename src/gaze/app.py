"""Native macOS application bootstrap.

The bootstrap is deliberately side-effect light: importing this module does not
start the camera, enumerate windows, register hotkeys, or activate apps.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast


def main() -> int:
    """Launch the AppKit application shell when PyObjC is available."""

    try:
        appkit = cast(Any, import_module("AppKit"))
    except ModuleNotFoundError as exc:
        print(
            "Gaze requires PyObjC/AppKit on macOS. Run `make sync` on macOS before launching."
        )
        raise SystemExit(1) from exc

    app = appkit.NSApplication.sharedApplication()
    app.setActivationPolicy_(appkit.NSApplicationActivationPolicyRegular)
    app.activateIgnoringOtherApps_(True)
    return int(appkit.NSApplicationMain([], None) or 0)
