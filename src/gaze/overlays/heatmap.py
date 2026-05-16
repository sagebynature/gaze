"""Heatmap overlay boundary."""

from __future__ import annotations

from typing import Protocol


class HeatmapOverlay(Protocol):
    """Shows session-local gaze heatmap data."""

    def show(self) -> None:
        """Show the heatmap."""

    def hide(self) -> None:
        """Hide the heatmap."""

    def clear(self) -> None:
        """Clear session-local heatmap data."""
