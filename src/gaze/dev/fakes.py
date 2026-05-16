"""Deterministic fake services for the first Gaze prototype."""

from __future__ import annotations

from dataclasses import dataclass, replace

from gaze.core.state import TargetSummary
from gaze.desktop.window_candidates import WindowCandidateSummary


@dataclass(frozen=True)
class FakeTarget:
    app_name: str
    x: float
    y: float
    width: float
    height: float
    confidence: float

    def as_window_candidate(self) -> WindowCandidateSummary:
        return WindowCandidateSummary(
            app_name=self.app_name,
            bounds_x=self.x,
            bounds_y=self.y,
            bounds_width=self.width,
            bounds_height=self.height,
            confidence=self.confidence,
        )

    def as_target_summary(self, *, locked: bool = True) -> TargetSummary:
        return TargetSummary(app_name=self.app_name, confidence=self.confidence, locked=locked)


class FakeTargetController:
    def __init__(self, script: tuple[FakeTarget | None, ...] = ()) -> None:
        self._manual_target: FakeTarget | None = None
        self._script = script
        self._script_index = 0

    @classmethod
    def scripted_demo(cls) -> FakeTargetController:
        return cls(
            (
                FakeTarget("Safari", 100, 100, 900, 700, 0.86),
                FakeTarget("Terminal", 1200, 100, 900, 700, 0.91),
                None,
            )
        )

    def set_script(self, script: tuple[FakeTarget | None, ...]) -> None:
        self._script = script
        self._script_index = 0
        self._manual_target = None

    def set_manual_target(self, target: FakeTarget) -> None:
        self._manual_target = target

    def update_manual_target(self, target: FakeTarget) -> None:
        self._manual_target = target

    def clear_target(self) -> None:
        self._manual_target = None
        self._script = ()
        self._script_index = 0

    def advance_script(self) -> None:
        if self._script:
            self._script_index = min(self._script_index + 1, len(self._script) - 1)

    def current_fake_target(self) -> FakeTarget | None:
        if self._manual_target is not None:
            return self._manual_target
        if not self._script:
            return None
        return self._script[self._script_index]

    def current_target(self) -> TargetSummary | None:
        target = self.current_fake_target()
        return None if target is None else target.as_target_summary()

    def update_current_bounds(self, *, x: float, y: float, width: float, height: float) -> None:
        target = self.current_fake_target()
        if target is not None:
            self._manual_target = replace(target, x=x, y=y, width=width, height=height)

    def update_current_confidence(self, confidence: float) -> None:
        target = self.current_fake_target()
        if target is not None:
            self._manual_target = replace(target, confidence=confidence)


class FakeFrontmostApp:
    def __init__(self) -> None:
        self._frontmost_app_name: str | None = None

    def set_frontmost(self, app_name: str | None) -> None:
        self._frontmost_app_name = app_name

    def is_frontmost(self, app_name: str) -> bool:
        return self._frontmost_app_name == app_name
