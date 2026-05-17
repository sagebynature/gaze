"""macOS global hotkey registration boundary.

This module is import-safe: it does not load Carbon/ApplicationServices until the
runtime registry is created without an injected API.
"""

from __future__ import annotations

import ctypes
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

_CMD_MODIFIER = 1 << 8
_OPTION_MODIFIER = 1 << 11
_KEY_CODES = {"g": 5}
_MODIFIER_CODES = {"cmd": _CMD_MODIFIER, "option": _OPTION_MODIFIER}
_EVENT_CLASS_KEYBOARD = 0x6B657962  # b"keyb"
_EVENT_HOTKEY_PRESSED = 5
_EVENT_PARAM_DIRECT_OBJECT = 0x2D2D2D2D  # b"----"
_TYPE_EVENT_HOTKEY_ID = 0x686B6964  # b"hkid"
_HOTKEY_SIGNATURE = 0x475A4548  # b"GZEH"
_NO_ERR = 0


class HotkeyRegistrationError(RuntimeError):
    """Raised when the platform refuses a global hotkey registration."""


class CarbonHotkeyAPI(Protocol):
    """Small platform API used by the Carbon registry."""

    def register_event_hotkey(self, key_code: int, modifiers: int, hotkey_id: int) -> object:
        """Register one global hotkey and return an opaque platform reference."""
        ...


@dataclass(frozen=True)
class ParsedHotkey:
    key_code: int
    modifiers: int


class CarbonGlobalHotkeyRegistry:
    """Register and dispatch Carbon global hotkeys for the menu-bar runtime."""

    def __init__(self, *, carbon: CarbonHotkeyAPI | None = None) -> None:
        self._carbon = carbon or CTypesCarbonHotkeyAPI(self.dispatch_hotkey_id)
        self._handlers: dict[int, Callable[[], None]] = {}
        self._registered_hotkeys: dict[str, int] = {}
        self._refs: list[object] = []
        self.feedback_messages: list[str] = []

    def register(self, hotkey: str, handler: Callable[[], None], *, label: str) -> None:
        if hotkey in self._registered_hotkeys:
            self.feedback_messages.append(f"conflict {hotkey} for {label}")
            return
        parsed = parse_hotkey(hotkey)
        if parsed is None:
            self.feedback_messages.append(f"unavailable {hotkey} for {label}")
            return
        hotkey_id = len(self._handlers) + 1
        try:
            hotkey_ref = self._carbon.register_event_hotkey(
                parsed.key_code,
                parsed.modifiers,
                hotkey_id,
            )
        except HotkeyRegistrationError:
            self.feedback_messages.append(f"unavailable {hotkey} for {label}")
            return
        self._registered_hotkeys[hotkey] = hotkey_id
        self._handlers[hotkey_id] = handler
        self._refs.append(hotkey_ref)

    def trigger(self, hotkey: str) -> None:
        """Test seam matching the in-memory registry."""
        hotkey_id = self._registered_hotkeys.get(hotkey)
        if hotkey_id is not None:
            self.dispatch_hotkey_id(hotkey_id)

    def dispatch_hotkey_id(self, hotkey_id: int) -> None:
        handler = self._handlers.get(hotkey_id)
        if handler is not None:
            handler()


def parse_hotkey(hotkey: str) -> ParsedHotkey | None:
    parts = hotkey.split("+")
    if len(parts) < 2:
        return None
    key_name = parts[-1]
    key_code = _KEY_CODES.get(key_name)
    if key_code is None:
        return None
    modifier_mask = 0
    for modifier in parts[:-1]:
        modifier_code = _MODIFIER_CODES.get(modifier)
        if modifier_code is None:
            return None
        modifier_mask |= modifier_code
    return ParsedHotkey(key_code=key_code, modifiers=modifier_mask)


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


class CTypesCarbonHotkeyAPI:
    """ctypes wrapper for Carbon RegisterEventHotKey."""

    def __init__(self, dispatch: Callable[[int], None]) -> None:
        self._dispatch = dispatch
        self._framework = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
        self._event_handler_type = ctypes.CFUNCTYPE(
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        self._configure_function_signatures()
        self._event_handler = self._event_handler_type(self._handle_event)
        self._install_event_handler()

    def _configure_function_signatures(self) -> None:
        self._framework.GetApplicationEventTarget.restype = ctypes.c_void_p
        self._framework.RegisterEventHotKey.argtypes = [
            ctypes.c_uint32,
            ctypes.c_uint32,
            _EventHotKeyID,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._framework.RegisterEventHotKey.restype = ctypes.c_int
        self._framework.InstallEventHandler.argtypes = [
            ctypes.c_void_p,
            self._event_handler_type,
            ctypes.c_uint32,
            ctypes.POINTER(_EventTypeSpec),
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self._framework.InstallEventHandler.restype = ctypes.c_int
        self._framework.GetEventParameter.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.POINTER(_EventHotKeyID),
        ]
        self._framework.GetEventParameter.restype = ctypes.c_int

    def register_event_hotkey(self, key_code: int, modifiers: int, hotkey_id: int) -> object:
        hotkey_ref = ctypes.c_void_p()
        event_id = _EventHotKeyID(_HOTKEY_SIGNATURE, hotkey_id)
        status = self._framework.RegisterEventHotKey(
            ctypes.c_uint32(key_code),
            ctypes.c_uint32(modifiers),
            event_id,
            self._framework.GetApplicationEventTarget(),
            ctypes.c_uint32(0),
            ctypes.byref(hotkey_ref),
        )
        if status != _NO_ERR:
            raise HotkeyRegistrationError(f"RegisterEventHotKey failed with status {status}")
        return hotkey_ref

    def _install_event_handler(self) -> None:
        event_type = _EventTypeSpec(_EVENT_CLASS_KEYBOARD, _EVENT_HOTKEY_PRESSED)
        status = self._framework.InstallEventHandler(
            self._framework.GetApplicationEventTarget(),
            self._event_handler,
            ctypes.c_uint32(1),
            ctypes.byref(event_type),
            None,
            None,
        )
        if status != _NO_ERR:
            raise HotkeyRegistrationError(f"InstallEventHandler failed with status {status}")

    def _handle_event(self, _next_handler: Any, event: Any, _user_data: Any) -> int:
        event_id = _EventHotKeyID()
        status = self._framework.GetEventParameter(
            event,
            ctypes.c_uint32(_EVENT_PARAM_DIRECT_OBJECT),
            ctypes.c_uint32(_TYPE_EVENT_HOTKEY_ID),
            None,
            ctypes.c_uint32(ctypes.sizeof(event_id)),
            None,
            ctypes.byref(event_id),
        )
        if status == _NO_ERR and event_id.signature == _HOTKEY_SIGNATURE:
            self._dispatch(int(event_id.id))
        return _NO_ERR
