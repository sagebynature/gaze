"""Subtle trust-surface feedback events."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from gaze.desktop.activation import ActivationOutcome


class FeedbackKind(StrEnum):
    """Small non-modal feedback categories."""

    SUCCESS = "success"
    FAILURE = "failure"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class FeedbackEvent:
    """A short-lived feedback event that never captures input."""

    kind: FeedbackKind
    message: str
    ttl_ms: int
    non_modal: bool = True
    intercepts_input: bool = False


def feedback_for_activation(outcome: ActivationOutcome) -> FeedbackEvent:
    """Map activation outcomes to subtle content-safe feedback."""

    if outcome == ActivationOutcome.SUCCESS:
        return FeedbackEvent(
            kind=FeedbackKind.SUCCESS,
            message="Activation sent",
            ttl_ms=1200,
        )
    if outcome == ActivationOutcome.ALREADY_FRONTMOST:
        return FeedbackEvent(
            kind=FeedbackKind.NEUTRAL,
            message="Already focused",
            ttl_ms=1000,
        )
    if outcome == ActivationOutcome.UNAVAILABLE:
        return FeedbackEvent(
            kind=FeedbackKind.FAILURE,
            message="Activation unavailable",
            ttl_ms=1600,
        )
    if outcome == ActivationOutcome.DISABLED:
        return FeedbackEvent(
            kind=FeedbackKind.NEUTRAL,
            message="Gaze disabled",
            ttl_ms=1200,
        )
    return FeedbackEvent(
        kind=FeedbackKind.NEUTRAL,
        message="No target",
        ttl_ms=1000,
    )
