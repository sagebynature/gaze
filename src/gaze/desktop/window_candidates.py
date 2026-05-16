"""Window candidate provider protocol boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class WindowCandidateSummary:
    """In-memory summary of a visible window candidate.

    Window titles and desktop contents stay out of this model. The owner process
    identifier is retained only as runtime activation identity for later AppKit
    activation and must not be serialized as diagnostics without privacy review.
    """

    app_name: str
    bounds_x: float
    bounds_y: float
    bounds_width: float
    bounds_height: float
    confidence: float = 0.0
    owner_process_id: int | None = None


class WindowCandidateProvider(Protocol):
    """Provides the current gaze-selected window candidate."""

    def current_candidate(self) -> WindowCandidateSummary | None:
        """Return the current candidate, if gaze is locked onto one."""
