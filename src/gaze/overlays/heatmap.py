"""Heatmap overlay boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class HeatmapPoint:
    """Session-local scalar gaze point for an optional heatmap."""

    x: float
    y: float
    confidence: float


class HeatmapOverlay(Protocol):
    """Shows session-local gaze heatmap data."""

    def show(self) -> None:
        """Show the heatmap."""

    def hide(self) -> None:
        """Hide the heatmap."""

    def clear(self) -> None:
        """Clear session-local heatmap data."""

    def add_point(self, point: HeatmapPoint) -> None:
        """Add a scalar point to the current session."""


class RecordingHeatmapOverlay:
    """In-memory heatmap double with bounded session-local points."""

    def __init__(self, *, max_points: int = 256) -> None:
        self.visible = False
        self.max_points = max(1, max_points)
        self._points: list[HeatmapPoint] = []

    @property
    def points(self) -> tuple[HeatmapPoint, ...]:
        return tuple(self._points)

    def show(self) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def clear(self) -> None:
        self._points.clear()

    def add_point(self, point: HeatmapPoint) -> None:
        self._points.append(point)
        if len(self._points) > self.max_points:
            del self._points[: len(self._points) - self.max_points]
