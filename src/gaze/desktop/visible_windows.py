"""CoreGraphics-backed visible-window provider.

The module is import safe: CoreGraphics/Quartz is imported only when the
provider enumerates the desktop at runtime. Tests should inject fixture records
rather than touching the real desktop.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any, cast

from gaze.desktop.window_candidates import WindowCandidateSummary

WindowRecord = Mapping[str, object]
VisibleRegion = tuple[float, float, float, float]

_NORMAL_WINDOW_LAYER = 0
_EXCLUDED_OWNER_NAMES = frozenset(
    {
        "Dock",
        "SystemUIServer",
        "Control Center",
        "Notification Center",
        "Window Server",
    }
)


class CoreGraphicsVisibleWindowProvider:
    """Enumerate current-Space visible app windows from CoreGraphics metadata."""

    def __init__(
        self,
        *,
        window_records: Callable[[], Iterable[WindowRecord]] | None = None,
        visible_regions: Sequence[VisibleRegion] = (),
    ) -> None:
        self._window_records = window_records or _core_graphics_window_records
        self._visible_regions = tuple(visible_regions)

    def current_candidates(self) -> tuple[WindowCandidateSummary, ...]:
        """Return visible candidates in CoreGraphics top-to-bottom order."""

        candidates: list[WindowCandidateSummary] = []
        for record in self._window_records():
            candidate = _candidate_from_record(record, visible_regions=self._visible_regions)
            if candidate is not None:
                candidates.append(candidate)
        return tuple(candidates)

    def current_candidate(self) -> WindowCandidateSummary | None:
        """Return the topmost visible candidate, if any."""

        candidates = self.current_candidates()
        return candidates[0] if candidates else None


def _core_graphics_window_records() -> Iterable[WindowRecord]:
    quartz: Any = __import__("Quartz")
    options = int(quartz.kCGWindowListOptionOnScreenOnly) | int(
        quartz.kCGWindowListExcludeDesktopElements
    )
    records = quartz.CGWindowListCopyWindowInfo(options, quartz.kCGNullWindowID)
    return tuple(records or ())


def _candidate_from_record(
    record: WindowRecord,
    *,
    visible_regions: Sequence[VisibleRegion],
) -> WindowCandidateSummary | None:
    owner = _string_value(record.get("kCGWindowOwnerName"))
    if owner is None or owner in _EXCLUDED_OWNER_NAMES:
        return None

    layer = _int_value(record.get("kCGWindowLayer"))
    if layer != _NORMAL_WINDOW_LAYER:
        return None

    if _bool_value(record.get("kCGWindowIsOnscreen")) is not True:
        return None

    alpha = _float_value(record.get("kCGWindowAlpha"))
    if alpha is None or alpha <= 0:
        return None

    bounds_record = record.get("kCGWindowBounds")
    if not isinstance(bounds_record, Mapping):
        return None

    bounds = cast(Mapping[str, object], bounds_record)
    x = _float_value(bounds.get("X"))
    y = _float_value(bounds.get("Y"))
    width = _float_value(bounds.get("Width"))
    height = _float_value(bounds.get("Height"))
    if x is None or y is None or width is None or height is None:
        return None
    if width <= 0 or height <= 0:
        return None
    if visible_regions and not _intersects_any_region((x, y, width, height), visible_regions):
        return None

    return WindowCandidateSummary(
        app_name=owner,
        bounds_x=x,
        bounds_y=y,
        bounds_width=width,
        bounds_height=height,
        confidence=1.0,
        owner_process_id=_int_value(record.get("kCGWindowOwnerPID")),
    )


def _intersects_any_region(
    bounds: VisibleRegion,
    visible_regions: Sequence[VisibleRegion],
) -> bool:
    return any(_rects_intersect(bounds, region) for region in visible_regions)


def _rects_intersect(first: VisibleRegion, second: VisibleRegion) -> bool:
    first_x, first_y, first_width, first_height = first
    second_x, second_y, second_width, second_height = second
    return not (
        first_x + first_width <= second_x
        or second_x + second_width <= first_x
        or first_y + first_height <= second_y
        or second_y + second_height <= first_y
    )


def _string_value(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


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
