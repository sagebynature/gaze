from gaze.core.target_lock import TargetLockPolicy, TargetObservation


def test_target_does_not_lock_before_stability_threshold() -> None:
    policy = TargetLockPolicy(stability_ms=400)

    result = policy.update(TargetObservation(app_name="Terminal", confidence=0.9), now_ms=1000)
    result = policy.update(TargetObservation(app_name="Terminal", confidence=0.9), now_ms=1299)

    assert result.locked is False


def test_target_locks_after_balanced_stability_threshold() -> None:
    policy = TargetLockPolicy(stability_ms=400)

    policy.update(TargetObservation(app_name="Terminal", confidence=0.9), now_ms=1000)
    result = policy.update(TargetObservation(app_name="Terminal", confidence=0.9), now_ms=1400)

    assert result.locked is True
    assert result.app_name == "Terminal"


def test_target_change_restarts_stability_timer() -> None:
    policy = TargetLockPolicy(stability_ms=400)

    policy.update(TargetObservation(app_name="Terminal", confidence=0.9), now_ms=1000)
    policy.update(TargetObservation(app_name="Safari", confidence=0.9), now_ms=1300)
    result = policy.update(TargetObservation(app_name="Safari", confidence=0.9), now_ms=1500)

    assert result.locked is False


def test_no_target_clears_lock() -> None:
    policy = TargetLockPolicy(stability_ms=400)

    policy.update(TargetObservation(app_name="Terminal", confidence=0.9), now_ms=1000)
    policy.update(TargetObservation(app_name="Terminal", confidence=0.9), now_ms=1400)
    result = policy.update(None, now_ms=1450)

    assert result.app_name is None
    assert result.locked is False
