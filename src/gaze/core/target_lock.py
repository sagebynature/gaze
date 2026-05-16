"""Pure target stability and lock policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TargetObservation:
    app_name: str
    confidence: float


@dataclass(frozen=True)
class TargetLockResult:
    app_name: str | None
    confidence: float
    locked: bool


class TargetLockPolicy:
    def __init__(self, *, stability_ms: int = 400) -> None:
        self._stability_ms = stability_ms
        self._candidate: TargetObservation | None = None
        self._candidate_since_ms: int | None = None

    def update(self, observation: TargetObservation | None, *, now_ms: int) -> TargetLockResult:
        if observation is None:
            self._candidate = None
            self._candidate_since_ms = None
            return TargetLockResult(app_name=None, confidence=0.0, locked=False)

        if self._candidate is None or self._candidate.app_name != observation.app_name:
            self._candidate = observation
            self._candidate_since_ms = now_ms
            return TargetLockResult(
                app_name=observation.app_name,
                confidence=observation.confidence,
                locked=False,
            )

        since_ms = self._candidate_since_ms if self._candidate_since_ms is not None else now_ms
        return TargetLockResult(
            app_name=observation.app_name,
            confidence=observation.confidence,
            locked=now_ms - since_ms >= self._stability_ms,
        )
