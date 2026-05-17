"""Runtime AppKit window factory seams for settings and developer panels."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from gaze.tracking.calibration import CalibrationProviderSnapshot
from gaze.ui.developer_actions import DeveloperPanelActions
from gaze.ui.developer_panel import DeveloperControl, developer_controls
from gaze.ui.setup_window import (
    default_calibration_wizard_snapshot,
    render_calibration_wizard_text,
    setup_sections,
)

_RETAINED_DEVELOPER_TARGETS: list[DeveloperPanelActionTarget] = []


class DeveloperPanelActionTarget:
    """Objective-C selector target that keeps developer panel buttons fake-safe."""

    def __init__(
        self,
        actions: DeveloperPanelActions,
        *,
        after_action: Callable[[], None] | None = None,
    ) -> None:
        self._actions = actions
        self._after_action = after_action

    def _done(self) -> None:
        if self._after_action is not None:
            self._after_action()

    def start_scripted_demo_(self, sender: Any | None = None) -> None:
        self._actions.start_scripted_demo()
        self._actions.tick(now_ms=1000)
        self._actions.tick(now_ms=1400)
        self._done()

    def stop_scripted_demo_(self, sender: Any | None = None) -> None:
        self._actions.stop_scripted_demo()
        self._done()

    def set_fake_target_(self, sender: Any | None = None) -> None:
        self._actions.enable_gaze()
        self._actions.set_fake_target(
            app_name="Terminal",
            x=120,
            y=120,
            width=900,
            height=700,
            confidence=0.91,
        )
        self._actions.set_fake_lock_state(True)
        self._done()

    def set_fake_target_bounds_(self, sender: Any | None = None) -> None:
        self._actions.set_fake_target_bounds(x=120, y=120, width=900, height=700)
        self._done()

    def set_fake_confidence_(self, sender: Any | None = None) -> None:
        self._actions.set_fake_confidence(0.91)
        self._done()

    def set_fake_lock_state_(self, sender: Any | None = None) -> None:
        self._actions.enable_gaze()
        self._actions.set_fake_lock_state(True)
        self._done()

    def set_fake_frontmost_app_(self, sender: Any | None = None) -> None:
        self._actions.set_fake_frontmost_app("Terminal")
        self._done()

    def trigger_activation_success_(self, sender: Any | None = None) -> None:
        self._actions.trigger_activation_success()
        self._done()

    def trigger_activation_failure_(self, sender: Any | None = None) -> None:
        self._actions.trigger_activation_failure()
        self._done()

    def trigger_no_target_(self, sender: Any | None = None) -> None:
        self._actions.trigger_no_target()
        self._done()

    def trigger_degraded_(self, sender: Any | None = None) -> None:
        self._actions.trigger_degraded()
        self._done()


def _utility_window(appkit: Any, *, width: int, height: int) -> Any:
    style_mask = appkit.NSWindowStyleMaskTitled | appkit.NSWindowStyleMaskClosable
    return appkit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        appkit.NSMakeRect(0, 0, width, height),
        style_mask,
        appkit.NSBackingStoreBuffered,
        False,
    )


def _show_window(window: Any, *, title: str, content_view: Any) -> Any:
    window.setTitle_(title)
    window.setContentView_(content_view)
    if hasattr(window, "center"):
        window.center()
    window.makeKeyAndOrderFront_(None)
    return window


def _text_view(appkit: Any, text: str, *, action_names: list[str] | None = None) -> Any:
    view = appkit.NSTextView.alloc().init()
    view.setString_(text)
    view.setEditable_(False)
    if hasattr(view, "setSelectable_"):
        view.setSelectable_(True)
    if action_names is not None and hasattr(view, "setActionNames_"):
        view.setActionNames_(action_names)
    return view


def _developer_action_selector(action: str) -> str:
    return f"{action}:"


def _button_stack(
    appkit: Any,
    *,
    controls: list[DeveloperControl],
    target: DeveloperPanelActionTarget,
) -> Any | None:
    if not hasattr(appkit, "NSStackView") or not hasattr(appkit, "NSButton"):
        return None
    stack = appkit.NSStackView.alloc().init()
    if hasattr(stack, "setOrientation_") and hasattr(
        appkit,
        "NSUserInterfaceLayoutOrientationVertical",
    ):
        stack.setOrientation_(appkit.NSUserInterfaceLayoutOrientationVertical)
    for control in controls:
        button = appkit.NSButton.buttonWithTitle_target_action_(
            control.label,
            target,
            _developer_action_selector(control.action),
        )
        if hasattr(stack, "addArrangedSubview_"):
            stack.addArrangedSubview_(button)
        else:
            stack.addView_inGravity_(button, 0)
    return stack


def create_settings_window(appkit: Any | None) -> Any | None:
    if appkit is None:
        return None
    sections = setup_sections()
    text = "\n\n".join(
        f"{section.label}\n{section.description}" for section in sections
    )
    action_names = [section.action for section in sections if section.action is not None]
    return _show_window(
        _utility_window(appkit, width=420, height=320),
        title="Gaze Settings",
        content_view=_text_view(appkit, text, action_names=action_names),
    )


def create_calibration_wizard_window(
    appkit: Any | None,
    *,
    snapshot: CalibrationProviderSnapshot | None = None,
) -> Any | None:
    if appkit is None or not hasattr(appkit, "NSWindow"):
        return None
    safe_snapshot = snapshot or default_calibration_wizard_snapshot()
    return _show_window(
        _utility_window(appkit, width=460, height=420),
        title="Gaze Calibration",
        content_view=_text_view(
            appkit,
            render_calibration_wizard_text(safe_snapshot),
            action_names=["recalibrate", "settings"],
        ),
    )


def create_launch_setup_window(appkit: Any | None) -> Any | None:
    if appkit is None:
        return None
    return _show_window(
        _utility_window(appkit, width=460, height=360),
        title="Gaze Setup",
        content_view=_text_view(
            appkit,
            render_calibration_wizard_text(default_calibration_wizard_snapshot()),
            action_names=["recalibrate", "settings"],
        ),
    )


def create_developer_panel(
    appkit: Any | None,
    *,
    development_mode: bool,
    actions: DeveloperPanelActions | None = None,
    after_action: Callable[[], None] | None = None,
) -> Any | None:
    if appkit is None or not development_mode or actions is None:
        return None
    controls = developer_controls()
    target = DeveloperPanelActionTarget(actions, after_action=after_action)
    _RETAINED_DEVELOPER_TARGETS.append(target)
    content_view = _button_stack(appkit, controls=controls, target=target)
    if content_view is None:
        text = "\n".join(control.label for control in controls)
        action_names = [control.action for control in controls]
        content_view = _text_view(appkit, text, action_names=action_names)
    return _show_window(
        _utility_window(appkit, width=460, height=480),
        title="Gaze Developer Panel",
        content_view=content_view,
    )
