"""Target border overlay boundary."""

from __future__ import annotations

from typing import Protocol

from gaze.desktop.window_candidates import WindowCandidateSummary


class TargetBorderOverlay(Protocol):
    """Draws a non-interactive border around the current target."""

    def show(self, candidate: WindowCandidateSummary) -> None:
        """Show the border for a candidate."""

    def hide(self) -> None:
        """Hide the border immediately."""
