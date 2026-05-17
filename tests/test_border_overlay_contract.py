from __future__ import annotations

from typing import ClassVar

from gaze.desktop.window_candidates import WindowCandidateSummary
from gaze.overlays.border import (
    AppKitBorderOverlay,
    BorderOverlayStyle,
    RecordingBorderOverlay,
    appkit_overlay_window_config,
    create_appkit_border_overlay,
)


def test_default_border_style_is_non_interactive() -> None:
    style = BorderOverlayStyle.default()

    assert style.ignores_mouse_events is True
    assert style.can_become_key is False
    assert style.activates_app is False
    assert style.opacity <= 0.35


def test_recording_overlay_tracks_show_and_hide_without_side_effects() -> None:
    overlay = RecordingBorderOverlay()
    candidate = WindowCandidateSummary("Terminal", 10, 20, 800, 600, confidence=0.9)

    overlay.show(candidate)
    overlay.hide()

    assert overlay.events == [("show", "Terminal"), ("hide", None)]
    assert overlay.visible is False


def test_appkit_overlay_factory_is_import_safe() -> None:
    overlay = create_appkit_border_overlay(appkit=None)

    assert overlay is None


def test_appkit_overlay_uses_non_interactive_style_contract() -> None:
    config = appkit_overlay_window_config(BorderOverlayStyle.default())

    assert config["ignores_mouse_events"] is True
    assert config["can_become_key"] is False
    assert config["activates_app"] is False
    assert config["hides_on_deactivate"] is False
    assert config["nonactivating_panel"] is True
    assert config["draws_thin_outline"] is True
    assert config["draws_soft_glow"] is True


class FakeLayer:
    def setBorderWidth_(self, width: float) -> None:
        self.border_width = width

    def setCornerRadius_(self, radius: float) -> None:
        self.corner_radius = radius

    def setShadowOpacity_(self, opacity: float) -> None:
        self.shadow_opacity = opacity

    def setShadowRadius_(self, radius: float) -> None:
        self.shadow_radius = radius


class FakeView:
    @classmethod
    def alloc(cls) -> FakeView:
        return cls()

    def initWithFrame_(self, frame: object) -> FakeView:
        self.frame = frame
        self._layer = FakeLayer()
        return self

    def setWantsLayer_(self, wants_layer: bool) -> None:
        self.wants_layer = wants_layer

    def layer(self) -> FakeLayer:
        return self._layer


class FakePanel:
    created: ClassVar[list[FakePanel]] = []

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    @classmethod
    def alloc(cls) -> FakePanel:
        return cls()

    def initWithContentRect_styleMask_backing_defer_(
        self,
        rect: object,
        style_mask: int,
        backing: int,
        defer: bool,
    ) -> FakePanel:
        self.rect = rect
        self.style_mask = style_mask
        self.backing = backing
        self.defer = defer
        self.__class__.created.append(self)
        return self

    def setOpaque_(self, value: bool) -> None:
        self.calls.append(("opaque", value))

    def setBackgroundColor_(self, value: object) -> None:
        self.calls.append(("background", value))

    def setIgnoresMouseEvents_(self, value: bool) -> None:
        self.calls.append(("ignores_mouse", value))

    def setCanHide_(self, value: bool) -> None:
        self.calls.append(("can_hide", value))

    def setHidesOnDeactivate_(self, value: bool) -> None:
        self.calls.append(("hides_on_deactivate", value))

    def setLevel_(self, value: int) -> None:
        self.calls.append(("level", value))

    def setCollectionBehavior_(self, value: int) -> None:
        self.calls.append(("collection_behavior", value))

    def setContentView_(self, value: object) -> None:
        self.calls.append(("content_view", value))

    def orderFrontRegardless(self) -> None:
        self.calls.append(("order_front", True))

    def setFrame_display_(self, rect: object, display: bool) -> None:
        self.calls.append(("frame", (rect, display)))

    def orderOut_(self, sender: object) -> None:
        self.calls.append(("order_out", sender))


class FakeColor:
    @staticmethod
    def clearColor() -> str:
        return "clear"


class FakeAppKit:
    NSView = FakeView
    NSPanel = FakePanel
    NSColor = FakeColor
    NSWindowStyleMaskBorderless = 1
    NSWindowStyleMaskNonactivatingPanel = 128
    NSBackingStoreBuffered = 2
    NSStatusWindowLevel = 3
    NSWindowCollectionBehaviorCanJoinAllSpaces = 4
    NSWindowCollectionBehaviorFullScreenAuxiliary = 8

    @staticmethod
    def NSMakeRect(x: float, y: float, width: float, height: float) -> tuple[float, ...]:
        return (x, y, width, height)


class FakeAppKitWithoutDeactivateSetter(FakeAppKit):
    class NSPanel(FakePanel):
        def setHidesOnDeactivate_(self, value: bool) -> None:
            raise AssertionError("older AppKit fake should not require this method")


def test_appkit_overlay_panel_does_not_hide_when_another_app_becomes_foreground() -> None:
    FakePanel.created = []
    overlay = AppKitBorderOverlay(FakeAppKit())

    overlay.show(WindowCandidateSummary("Terminal", 10, 20, 800, 600, confidence=0.9))

    panel = FakePanel.created[0]
    assert panel.style_mask & FakeAppKit.NSWindowStyleMaskNonactivatingPanel
    assert ("hides_on_deactivate", False) in panel.calls
    assert ("can_hide", False) in panel.calls
    assert ("order_front", True) in panel.calls
