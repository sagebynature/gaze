"""Runtime AppKit window factory seams for settings and developer panels."""

from __future__ import annotations

from typing import Any

from gaze.ui.developer_actions import DeveloperPanelActions
from gaze.ui.developer_panel import DeveloperControl, developer_controls
from gaze.ui.setup_window import setup_sections


class DeveloperPanelActionTarget:
    """Objective-C selector target that keeps developer panel buttons fake-safe."""

    def __init__(self, actions: DeveloperPanelActions) -> None:
        self._actions = actions

    def start_scripted_demo_(self, sender: Any | None = None) -> None:
        self._actions.start_scripted_demo()

    def stop_scripted_demo_(self, sender: Any | None = None) -> None:
        self._actions.stop_scripted_demo()

    def set_fake_target_(self, sender: Any | None = None) -> None:
        self._actions.set_fake_target(
            app_name="Terminal",
            x=120,
            y=120,
            width=900,
            height=700,
            confidence=0.91,
        )

    def set_fake_target_bounds_(self, sender: Any | None = None) -> None:
        self._actions.set_fake_target_bounds(x=120, y=120, width=900, height=700)

    def set_fake_confidence_(self, sender: Any | None = None) -> None:
        self._actions.set_fake_confidence(0.91)

    def set_fake_lock_state_(self, sender: Any | None = None) -> None:
        self._actions.set_fake_lock_state(True)

    def set_fake_frontmost_app_(self, sender: Any | None = None) -> None:
        self._actions.set_fake_frontmost_app("Terminal")

    def trigger_activation_success_(self, sender: Any | None = None) -> None:
        self._actions.trigger_activation_success()

    def trigger_activation_failure_(self, sender: Any | None = None) -> None:
        self._actions.trigger_activation_failure()

    def trigger_no_target_(self, sender: Any | None = None) -> None:
        self._actions.trigger_no_target()

    def trigger_degraded_(self, sender: Any | None = None) -> None:
        self._actions.trigger_degraded()


def _show_window(window: Any, *, title: str, content_view: Any) -> Any:
    window.setTitle_(title)
    window.setContentView_(content_view)
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
        stack.addView_inGravity_(button, 0)
    return stack


def create_settings_window(appkit: Any | None) -> Any | None:
    if appkit is None:
        return None
    text = "\n\n".join(
        f"{section.label}\n{section.description}" for section in setup_sections()
    )
    return _show_window(
        appkit.NSWindow.alloc().init(),
        title="Gaze Settings",
        content_view=_text_view(appkit, text),
    )


def create_developer_panel(
    appkit: Any | None,
    *,
    development_mode: bool,
    actions: DeveloperPanelActions | None = None,
) -> Any | None:
    if appkit is None or not development_mode or actions is None:
        return None
    controls = developer_controls()
    target = DeveloperPanelActionTarget(actions)
    content_view = _button_stack(appkit, controls=controls, target=target)
    if content_view is None:
        text = "\n".join(control.label for control in controls)
        action_names = [control.action for control in controls]
        content_view = _text_view(appkit, text, action_names=action_names)
    window = _show_window(
        appkit.NSWindow.alloc().init(),
        title="Gaze Developer Panel",
        content_view=content_view,
    )
    target_attribute = "_gaze_developer_target"
    setattr(window, target_attribute, target)
    return window
