"""Window candidate provider protocol boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WindowCandidateSummary:
    """UI-safe summary of a visible window candidate."""

    app_name: str
    bounds_x: float
    bounds_y: float
    bounds_width: float
    bounds_height: float
    confidence: float = 0.0


class WindowCandidateProvider(Protocol):
    """Provides the current gaze-selected window candidate."""

    def current_candidate(self) -> WindowCandidateSummary | None:
        """Return the current candidate, if gaze is locked onto one."""
