"""CoreGraphics-backed display geometry provider.

This module is import safe: Quartz is imported only when the default provider
queries active displays at runtime. Tests should inject scalar display records.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from gaze.core.display_geometry import DisplayGeometry, DisplayLayoutSnapshot

DisplayRecord = Mapping[str, object]


class CoreGraphicsDisplayProvider:
    """Return active macOS display geometry as privacy-safe scalar snapshots."""

    def __init__(
        self,
        *,
        display_records: Callable[[], Iterable[DisplayRecord]] | None = None,
    ) -> None:
        self._display_records = display_records or _core_graphics_display_records

    def current_layout(self) -> DisplayLayoutSnapshot:
        """Return the active display layout."""

        displays = tuple(
            display
            for record in self._display_records()
            if (display := _display_from_record(record)) is not None
        )
        return DisplayLayoutSnapshot(displays=displays)


def _core_graphics_display_records() -> Iterable[DisplayRecord]:
    quartz: Any = __import__("Quartz")
    max_displays = 16
    err, active_displays, display_count = quartz.CGGetActiveDisplayList(max_displays, None, None)
    if err != 0:
        return ()
    records: list[DisplayRecord] = []
    for display_id in tuple(active_displays or ())[: int(display_count or 0)]:
        bounds = quartz.CGDisplayBounds(display_id)
        records.append(
            {
                "display_id": int(display_id),
                "x": float(bounds.origin.x),
                "y": float(bounds.origin.y),
                "width": float(bounds.size.width),
                "height": float(bounds.size.height),
                "scale": _display_scale(quartz, display_id),
                "built_in": bool(quartz.CGDisplayIsBuiltin(display_id)),
            }
        )
    return tuple(records)


def _display_scale(quartz: Any, display_id: object) -> float:
    pixel_width = float(quartz.CGDisplayPixelsWide(display_id) or 0)
    point_width = float(quartz.CGDisplayBounds(display_id).size.width or 0)
    if pixel_width <= 0 or point_width <= 0:
        return 1.0
    return pixel_width / point_width


def _display_from_record(record: DisplayRecord) -> DisplayGeometry | None:
    display_id = _int_value(record.get("display_id"))
    x = _float_value(record.get("x"))
    y = _float_value(record.get("y"))
    width = _float_value(record.get("width"))
    height = _float_value(record.get("height"))
    scale = _float_value(record.get("scale")) or 1.0
    built_in = _bool_value(record.get("built_in")) or False
    if display_id is None or x is None or y is None or width is None or height is None:
        return None
    if width <= 0 or height <= 0 or scale <= 0:
        return None
    return DisplayGeometry(
        display_id=display_id,
        x=x,
        y=y,
        width=width,
        height=height,
        scale=scale,
        built_in=built_in,
    )


def _float_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _bool_value(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    return None
