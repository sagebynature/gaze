"""Default and editable hotkey binding models."""

from __future__ import annotations

from dataclasses import dataclass

MANUAL_ACTIVATE_ACTION = "manual_activate"
GAZE_TOGGLE_ACTION = "toggle_gaze"
MANUAL_ACTIVATE_HOTKEY = "cmd+g"
GAZE_TOGGLE_HOTKEY = "option+cmd+g"


@dataclass(frozen=True)
class HotkeyBinding:
    """Editable hotkey binding for one command action."""

    action: str
    hotkey: str
    enabled: bool = True


@dataclass(frozen=True)
class HotkeySettings:
    """Hotkey settings as edited from the settings surface."""

    bindings: tuple[HotkeyBinding, ...]

    @classmethod
    def default(cls) -> HotkeySettings:
        return default_hotkey_settings()

    def binding_for(self, action: str) -> HotkeyBinding:
        for binding in self.bindings:
            if binding.action == action:
                return binding
        raise KeyError(action)

    def disable(self, action: str) -> HotkeySettings:
        return self._replace(action, enabled=False)

    def enable(self, action: str) -> HotkeySettings:
        return self._replace(action, enabled=True)

    def rebind(self, action: str, hotkey: str) -> HotkeySettings:
        return self._replace(action, hotkey=hotkey)

    def _replace(
        self,
        action: str,
        *,
        hotkey: str | None = None,
        enabled: bool | None = None,
    ) -> HotkeySettings:
        bindings = []
        for binding in self.bindings:
            if binding.action == action:
                bindings.append(
                    HotkeyBinding(
                        action=binding.action,
                        hotkey=binding.hotkey if hotkey is None else hotkey,
                        enabled=binding.enabled if enabled is None else enabled,
                    )
                )
            else:
                bindings.append(binding)
        return HotkeySettings(tuple(bindings))


def default_hotkey_settings() -> HotkeySettings:
    return HotkeySettings(
        (
            HotkeyBinding(MANUAL_ACTIVATE_ACTION, MANUAL_ACTIVATE_HOTKEY),
            HotkeyBinding(GAZE_TOGGLE_ACTION, GAZE_TOGGLE_HOTKEY),
        )
    )
