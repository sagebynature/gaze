"""Privacy-safe display geometry models for calibration validation."""

from __future__ import annotations

from dataclasses import dataclass

VisibleRegion = tuple[float, float, float, float]


@dataclass(frozen=True)
class DisplayGeometry:
    """Scalar geometry for one active display.

    The model intentionally contains only display identity and geometry. It never
    includes screenshots, desktop contents, window titles, or app names.
    """

    display_id: int
    x: float
    y: float
    width: float
    height: float
    scale: float = 1.0
    built_in: bool = False

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            msg = "display width and height must be positive"
            raise ValueError(msg)
        if self.scale <= 0:
            msg = "display scale must be positive"
            raise ValueError(msg)

    @property
    def visible_region(self) -> VisibleRegion:
        """Return the display rectangle in global desktop coordinates."""

        return (
            float(self.x),
            float(self.y),
            float(self.width),
            float(self.height),
        )

    @property
    def signature_part(self) -> str:
        """Return a stable scalar signature fragment for this display."""

        kind = "built-in" if self.built_in else "external"
        return (
            f"{self.display_id}:{kind}:"
            f"{float(self.x):.1f},{float(self.y):.1f},"
            f"{float(self.width):.1f},{float(self.height):.1f}"
            f"@{float(self.scale):.1f}"
        )


@dataclass(frozen=True)
class DisplayLayoutSnapshot:
    """Scalar snapshot of the active display layout."""

    displays: tuple[DisplayGeometry, ...]

    def __post_init__(self) -> None:
        if not self.displays:
            msg = "display layout must include at least one display"
            raise ValueError(msg)

    @property
    def signature(self) -> str:
        """Return deterministic geometry signature for layout-change detection."""

        ordered = sorted(self.displays, key=lambda display: display.display_id)
        return "|".join(display.signature_part for display in ordered)

    @property
    def visible_regions(self) -> tuple[VisibleRegion, ...]:
        """Return visible regions in the provided display order."""

        return tuple(display.visible_region for display in self.displays)

    @property
    def has_built_in_display(self) -> bool:
        """Return whether the layout includes a built-in display."""

        return any(display.built_in for display in self.displays)

    @property
    def has_external_display(self) -> bool:
        """Return whether the layout includes at least one external display."""

        return any(not display.built_in for display in self.displays)
