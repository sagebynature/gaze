"""Native macOS application bootstrap.

The bootstrap is deliberately side-effect light: importing this module does not
start the camera, enumerate windows, register hotkeys, or activate apps.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, cast

from gaze.core.real_trust_preview import GazeSampleSource, RealTrustPreviewController
from gaze.desktop.activation import AppKitActivationService, TargetActivationService
from gaze.desktop.display_provider import CoreGraphicsDisplayProvider
from gaze.desktop.visible_windows import CoreGraphicsVisibleWindowProvider
from gaze.overlays.border import (
    RecordingBorderOverlay,
    TargetBorderOverlay,
    create_appkit_border_overlay,
)
from gaze.tracking.calibration import CalibrationSession
from gaze.tracking.pupil_tracker_runtime import (
    PupilTrackerDesktopCalibrationSession,
    PupilTrackerTelemetrySampleSource,
    default_bridge_path,
)
from gaze.ui.appkit_shell import build_menu_bar_app


def create_runtime_controller(
    *,
    overlay: TargetBorderOverlay,
    activation: TargetActivationService | None = None,
    calibration_session: CalibrationSession | None = None,
    sample_source: GazeSampleSource | None = None,
    window_provider: Any | None = None,
    display_provider: Any | None = None,
) -> RealTrustPreviewController:
    """Compose the real trust-preview runtime without starting side effects."""

    resolved_display_provider = display_provider or CoreGraphicsDisplayProvider()
    resolved_calibration_session = calibration_session or PupilTrackerDesktopCalibrationSession(
        display_provider=resolved_display_provider,
        bridge_path=default_bridge_path(),
    )
    return RealTrustPreviewController(
        overlay=overlay,
        activation=activation or AppKitActivationService(),
        calibration_session=resolved_calibration_session,
        sample_source=sample_source or PupilTrackerTelemetrySampleSource(default_bridge_path()),
        window_provider=window_provider or CoreGraphicsVisibleWindowProvider(),
        display_provider=resolved_display_provider,
    )


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
    controller = create_runtime_controller(overlay=overlay)
    build_menu_bar_app(appkit=appkit, controller=controller, development_mode=False)
    return _run_event_loop(appkit)


def _run_event_loop(appkit: Any) -> int:
    """Run the PyObjC AppKit event loop with the supported signature."""

    return int(appkit.NSApplicationMain([]) or 0)
