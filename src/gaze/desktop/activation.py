"""Window activation protocol boundary.

Real activation must use AppKit application activation, not synthetic clicks.
"""

from __future__ import annotations

from typing import Protocol


class ActivationService(Protocol):
    """Activates a gaze-selected window candidate."""

    def activate_current_target(self) -> bool:
        """Return whether activation succeeded."""
