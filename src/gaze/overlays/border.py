"""Target border overlay boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from gaze.desktop.window_candidates import WindowCandidateSummary


class TargetBorderOverlay(Protocol):
    """Draws a non-interactive border around the current target."""

    def show(self, candidate: WindowCandidateSummary) -> None:
        """Show the border for a candidate."""

    def hide(self) -> None:
        """Hide the border immediately."""


@dataclass(frozen=True)
class BorderOverlayStyle:
    ignores_mouse_events: bool
    can_become_key: bool
    activates_app: bool
    opacity: float
    line_width: float
    corner_radius: float

    @classmethod
    def default(cls) -> BorderOverlayStyle:
        return cls(
            ignores_mouse_events=True,
            can_become_key=False,
            activates_app=False,
            opacity=0.24,
            line_width=2.0,
            corner_radius=12.0,
        )


class RecordingBorderOverlay:
    def __init__(self) -> None:
        self.visible = False
        self.events: list[tuple[str, str | None]] = []

    def show(self, candidate: WindowCandidateSummary) -> None:
        self.visible = True
        self.events.append(("show", candidate.app_name))

    def hide(self) -> None:
        self.visible = False
        self.events.append(("hide", None))
