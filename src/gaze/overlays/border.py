"""Target border overlay boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from gaze.desktop.window_candidates import WindowCandidateSummary


class TargetBorderOverlay(Protocol):
    """Draws a non-interactive border around the current target."""

    def show(self, candidate: WindowCandidateSummary) -> None:
        """Show the border for a candidate."""

    def hide(self) -> None:
        """Hide the border immediately."""


@dataclass(frozen=True)
class BorderOverlayStyle:
    ignores_mouse_events: bool
    can_become_key: bool
    activates_app: bool
    hides_on_deactivate: bool
    opacity: float
    line_width: float
    corner_radius: float

    @classmethod
    def default(cls) -> BorderOverlayStyle:
        return cls(
            ignores_mouse_events=True,
            can_become_key=False,
            activates_app=False,
            hides_on_deactivate=False,
            opacity=0.24,
            line_width=2.0,
            corner_radius=12.0,
        )


class RecordingBorderOverlay:
    def __init__(self) -> None:
        self.visible = False
        self.last_candidate: WindowCandidateSummary | None = None
        self.events: list[tuple[str, str | None]] = []

    def show(self, candidate: WindowCandidateSummary) -> None:
        self.visible = True
        self.last_candidate = candidate
        self.events.append(("show", candidate.app_name))

    def hide(self) -> None:
        self.visible = False
        self.last_candidate = None
        self.events.append(("hide", None))


def appkit_overlay_window_config(style: BorderOverlayStyle) -> dict[str, bool | float]:
    """Return the AppKit overlay safety/drawing contract as testable scalars."""

    return {
        "ignores_mouse_events": style.ignores_mouse_events,
        "can_become_key": style.can_become_key,
        "activates_app": style.activates_app,
        "hides_on_deactivate": style.hides_on_deactivate,
        "nonactivating_panel": True,
        "opacity": style.opacity,
        "line_width": style.line_width,
        "corner_radius": style.corner_radius,
        "draws_thin_outline": True,
        "draws_soft_glow": True,
    }


class AppKitBorderOverlay:
    """Runtime AppKit overlay; importing this module does not import AppKit."""

    def __init__(self, appkit: Any, *, style: BorderOverlayStyle | None = None) -> None:
        self._appkit = appkit
        self._style = style or BorderOverlayStyle.default()
        self._window: Any | None = None

    def _make_content_view(self, frame: Any) -> Any:
        appkit = self._appkit
        view = appkit.NSView.alloc().initWithFrame_(frame)
        view.setWantsLayer_(True)
        layer = view.layer()
        layer.setBorderWidth_(self._style.line_width)
        layer.setCornerRadius_(self._style.corner_radius)
        layer.setShadowOpacity_(self._style.opacity)
        layer.setShadowRadius_(10.0)
        return view

    def _make_window(self, candidate: WindowCandidateSummary) -> Any:
        appkit = self._appkit
        rect = appkit.NSMakeRect(
            candidate.bounds_x,
            candidate.bounds_y,
            candidate.bounds_width,
            candidate.bounds_height,
        )
        style_mask = appkit.NSWindowStyleMaskBorderless | getattr(
            appkit,
            "NSWindowStyleMaskNonactivatingPanel",
            0,
        )
        window = appkit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            style_mask,
            appkit.NSBackingStoreBuffered,
            False,
        )
        window.setOpaque_(False)
        window.setBackgroundColor_(appkit.NSColor.clearColor())
        window.setIgnoresMouseEvents_(self._style.ignores_mouse_events)
        window.setCanHide_(False)
        if hasattr(window, "setHidesOnDeactivate_"):
            window.setHidesOnDeactivate_(self._style.hides_on_deactivate)
        window.setLevel_(appkit.NSStatusWindowLevel)
        window.setCollectionBehavior_(
            appkit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | appkit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        window.setContentView_(self._make_content_view(rect))
        return window

    def show(self, candidate: WindowCandidateSummary) -> None:
        rect = self._appkit.NSMakeRect(
            candidate.bounds_x,
            candidate.bounds_y,
            candidate.bounds_width,
            candidate.bounds_height,
        )
        window = self._window
        if window is None:
            window = self._make_window(candidate)
            self._window = window
        else:
            window.setFrame_display_(rect, True)
        window.orderFrontRegardless()

    def hide(self) -> None:
        if self._window is not None:
            self._window.orderOut_(None)


def create_appkit_border_overlay(appkit: Any | None = None) -> TargetBorderOverlay | None:
    """Create the real overlay only when runtime AppKit is explicitly supplied."""

    if appkit is None:
        return None
    return AppKitBorderOverlay(appkit)
