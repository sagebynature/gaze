# Gaze Fake Prototype Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build the first fake end-to-end Gaze trust loop: menu-bar utility shell, setup/settings shell, Developer panel, fake gaze/window/frontmost services, target lock policy, real non-interactive border overlay contract, and Cmd+G activation seam with fake activation outcomes.

**Architecture:** Keep the first slice deterministic and side-effect safe. Core behavior lives in pure Python modules with fakes and tests; AppKit/PyObjC UI code stays behind import-time-safe factory/seam functions. The app may use real AppKit objects only at runtime from `gaze.app:main`, never during test imports.

**Tech Stack:** Python 3.11+, PyObjC/AppKit for runtime UI, pytest, ruff, ty, uv, Makefile.

**Source specs:**
- `docs/superpowers/specs/2026-05-15-gaze-menu-bar-beta-design.md`
- `docs/plans/gaze-task-graphs.md`

**Non-negotiable constraints:**
- No camera access in this slice.
- No real window enumeration in this slice.
- No real app activation in this slice.
- No synthetic clicks.
- No import-time hotkey, overlay, camera, window, or activation side effects.
- Window titles must not appear in UI/log/test fixtures.
- Disable must clear target, hide overlays, and block activation.
- Cmd+G and Option+Cmd+G are modeled through command seams; actual global hotkey registration can remain a later runtime detail if needed.
- Fake prototype completion requires real runtime shells for menu bar, setup/settings, Developer panel, and a real AppKit border overlay, with manual validation for native side effects.

---

## Current Baseline

Existing files:
- `src/gaze/app.py`: side-effect-light AppKit bootstrap, currently regular app activation policy.
- `src/gaze/core/state.py`: basic feature flags/readiness and manual activation gating.
- `src/gaze/desktop/window_candidates.py`: `WindowCandidateSummary` and candidate provider protocol.
- `src/gaze/desktop/activation.py`: activation service protocol placeholder.
- `src/gaze/overlays/border.py`: border overlay protocol placeholder.
- `src/gaze/hotkeys/bindings.py`: manual hotkey constant only.
- `src/gaze/settings/defaults.py`: default flags and manual hotkey.
- `src/gaze/ui/setup_window.py`: setup window placeholder.
- `tests/test_core_state.py`: 4 core safety tests.

Project gate:

```bash
make check
```

Expected baseline: ruff passes, ty passes, pytest reports 4 passing tests.

---

## Task 1: Add UI-safe app state contracts

**Objective:** Define pure, testable state contracts for menu status, target summaries, and panic disable without AppKit.

**Files:**
- Modify: `src/gaze/core/state.py`
- Test: `tests/test_core_state.py`

**Step 1: Write failing tests**

Append tests:

```python
def test_menu_state_defaults_are_safe_and_off() -> None:
    state = GazeAppState.default()

    assert state.flags.gaze_enabled is False
    assert state.menu_status == "off"
    assert state.current_target is None
    assert state.overlay_visible is False
    assert state.activation_blocked is True


def test_disable_panic_clears_target_hides_overlay_and_blocks_activation() -> None:
    state = GazeAppState.default().with_target(
        TargetSummary(app_name="Terminal", confidence=0.91, locked=True)
    )

    disabled = state.disable_panic()

    assert disabled.flags.gaze_enabled is False
    assert disabled.current_target is None
    assert disabled.overlay_visible is False
    assert disabled.activation_blocked is True
    assert disabled.last_status_message == "Gaze disabled"


def test_target_summary_has_no_window_title_field() -> None:
    target = TargetSummary(app_name="Safari", confidence=0.8, locked=True)

    assert not hasattr(target, "window_title")


def test_target_summary_rejects_obvious_title_like_labels_as_extra_guard() -> None:
    with pytest.raises(ValueError, match="app name only"):
        TargetSummary(app_name="Safari - Bank Statement.pdf", confidence=0.8, locked=True)


def test_with_target_keeps_overlay_hidden_when_gaze_is_disabled() -> None:
    state = GazeAppState.default().with_target(
        TargetSummary(app_name="Terminal", confidence=0.91, locked=True)
    )

    assert state.current_target is not None
    assert state.overlay_visible is False
    assert state.activation_blocked is True
```

Also add `import pytest` if absent.

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_core_state.py -v
```

Expected: FAIL because `GazeAppState` and `TargetSummary` do not exist.

**Step 3: Implement minimal contracts**

Add to `src/gaze/core/state.py`:

```python
@dataclass(frozen=True)
class TargetSummary:
    """UI-safe target summary. App name only; never a window title."""

    app_name: str
    confidence: float
    locked: bool

    def __post_init__(self) -> None:
        if " - " in self.app_name:
            raise ValueError("target summary must use app name only")


@dataclass(frozen=True)
class GazeAppState:
    """Pure state snapshot for menu, overlay, and activation decisions."""

    flags: GazeFeatureFlags
    readiness: GazeReadiness
    current_target: TargetSummary | None = None
    overlay_visible: bool = False
    last_status_message: str = "Gaze off"

    @classmethod
    def default(cls) -> "GazeAppState":
        return cls(flags=GazeFeatureFlags(), readiness=GazeReadiness())

    @property
    def menu_status(self) -> str:
        if not self.flags.gaze_enabled:
            return "off"
        if self.readiness.calibration == CalibrationStatus.CALIBRATING:
            return "calibrating"
        if self.readiness.calibration == CalibrationStatus.DEGRADED:
            return "degraded"
        if manual_activation_allowed(self.flags, self.readiness):
            return "ready"
        return "not_ready"

    @property
    def activation_blocked(self) -> bool:
        return not (
            manual_activation_allowed(self.flags, self.readiness)
            and self.current_target is not None
            and self.current_target.locked
        )

    def with_target(self, target: TargetSummary | None) -> "GazeAppState":
        return replace(
            self,
            current_target=target,
            overlay_visible=(
                self.flags.gaze_enabled
                and self.flags.target_border_enabled
                and target is not None
                and target.locked
            ),
            last_status_message="Target locked" if target and target.locked else "No target",
        )

    def disable_panic(self) -> "GazeAppState":
        return replace(
            self,
            flags=replace(self.flags, gaze_enabled=False),
            current_target=None,
            overlay_visible=False,
            last_status_message="Gaze disabled",
        )
```

Add `replace` import:

```python
from dataclasses import dataclass, replace
```

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_core_state.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/core/state.py tests/test_core_state.py
git commit -m "feat: add Gaze app state contracts"
```

---

## Task 2: Add fake target source and scripted/manual controls model

**Objective:** Create deterministic fake target services that can power the Developer panel and tests without real gaze/window APIs.

**Files:**
- Create: `src/gaze/dev/fakes.py`
- Create: `src/gaze/dev/__init__.py`
- Test: `tests/test_fake_targets.py`

**Step 1: Write failing tests**

Create `tests/test_fake_targets.py`:

```python
from gaze.dev.fakes import FakeFrontmostApp, FakeTarget, FakeTargetController


def test_manual_fake_target_selection_returns_target_summary() -> None:
    controller = FakeTargetController()

    controller.set_manual_target(FakeTarget(app_name="Terminal", x=10, y=20, width=800, height=600, confidence=0.88))

    target = controller.current_target()
    assert target is not None
    assert target.app_name == "Terminal"
    assert target.confidence == 0.88


def test_fake_controller_can_report_no_target() -> None:
    controller = FakeTargetController()
    controller.set_manual_target(FakeTarget(app_name="Safari", x=0, y=0, width=500, height=400, confidence=0.9))

    controller.clear_target()

    assert controller.current_target() is None


def test_scripted_fake_sequence_advances_deterministically() -> None:
    controller = FakeTargetController.scripted_demo()

    assert controller.current_target().app_name == "Safari"
    controller.advance_script()
    assert controller.current_target().app_name == "Terminal"
    controller.advance_script()
    assert controller.current_target() is None


def test_fake_frontmost_app_is_simple_state() -> None:
    frontmost = FakeFrontmostApp()

    frontmost.set_frontmost("Terminal")

    assert frontmost.is_frontmost("Terminal") is True
    assert frontmost.is_frontmost("Safari") is False
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_fake_targets.py -v
```

Expected: FAIL because `gaze.dev.fakes` is missing.

**Step 3: Implement minimal code**

Create `src/gaze/dev/__init__.py` as empty or with module docstring.

Create `src/gaze/dev/fakes.py`:

```python
"""Deterministic fake services for the first Gaze prototype."""

from __future__ import annotations

from dataclasses import dataclass

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
    def scripted_demo(cls) -> "FakeTargetController":
        return cls(
            (
                FakeTarget("Safari", 100, 100, 900, 700, 0.86),
                FakeTarget("Terminal", 1200, 100, 900, 700, 0.91),
                None,
                FakeTarget("Discord", 300, 900, 800, 600, 0.62),
            )
        )

    def set_manual_target(self, target: FakeTarget) -> None:
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


class FakeFrontmostApp:
    def __init__(self) -> None:
        self._frontmost_app_name: str | None = None

    def set_frontmost(self, app_name: str | None) -> None:
        self._frontmost_app_name = app_name

    def is_frontmost(self, app_name: str) -> bool:
        return self._frontmost_app_name == app_name
```

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_fake_targets.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/dev/__init__.py src/gaze/dev/fakes.py tests/test_fake_targets.py
git commit -m "feat: add fake prototype target sources"
```

---

## Task 3: Add target lock policy

**Objective:** Implement the balanced 300-500 ms lock policy as pure code.

**Files:**
- Create: `src/gaze/core/target_lock.py`
- Test: `tests/test_target_lock.py`

**Step 1: Write failing tests**

Create `tests/test_target_lock.py`:

```python
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
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_target_lock.py -v
```

Expected: FAIL because `gaze.core.target_lock` is missing.

**Step 3: Implement minimal code**

Create `src/gaze/core/target_lock.py`:

```python
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
```

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_target_lock.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/core/target_lock.py tests/test_target_lock.py
git commit -m "feat: add target lock policy"
```

---

## Task 4: Add activation result model and fake activation service

**Objective:** Model activation outcomes precisely: disabled, no target, already frontmost, success, unavailable/failure.

**Files:**
- Modify: `src/gaze/desktop/activation.py`
- Test: `tests/test_activation_seam.py`

**Step 1: Write failing tests**

Create `tests/test_activation_seam.py`:

```python
from gaze.core.state import CalibrationStatus, GazeAppState, GazeFeatureFlags, GazeReadiness, TargetSummary
from gaze.desktop.activation import ActivationOutcome, FakeActivationService, request_manual_activation
from gaze.dev.fakes import FakeFrontmostApp


def ready_state_with_target(app_name: str = "Terminal") -> GazeAppState:
    return GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(
            calibration=CalibrationStatus.READY,
            camera_available=True,
            tracker_available=True,
        ),
    ).with_target(TargetSummary(app_name=app_name, confidence=0.9, locked=True))


def test_disabled_state_blocks_activation() -> None:
    service = FakeActivationService()

    outcome = request_manual_activation(GazeAppState.default(), service)

    assert outcome == ActivationOutcome.DISABLED
    assert service.calls == []


def test_no_locked_target_blocks_activation() -> None:
    service = FakeActivationService()
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(calibration=CalibrationStatus.READY, camera_available=True, tracker_available=True),
    )

    outcome = request_manual_activation(state, service)

    assert outcome == ActivationOutcome.NO_TARGET
    assert service.calls == []


def test_already_frontmost_suppresses_activation() -> None:
    frontmost = FakeFrontmostApp()
    frontmost.set_frontmost("Terminal")
    service = FakeActivationService(frontmost=frontmost)

    outcome = request_manual_activation(ready_state_with_target("Terminal"), service)

    assert outcome == ActivationOutcome.ALREADY_FRONTMOST
    assert service.calls == []


def test_locked_non_frontmost_target_activates_once() -> None:
    service = FakeActivationService()

    outcome = request_manual_activation(ready_state_with_target("Terminal"), service)

    assert outcome == ActivationOutcome.SUCCESS
    assert service.calls == ["Terminal"]


def test_activation_failure_returns_unavailable() -> None:
    service = FakeActivationService(should_succeed=False)

    outcome = request_manual_activation(ready_state_with_target("Terminal"), service)

    assert outcome == ActivationOutcome.UNAVAILABLE
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_activation_seam.py -v
```

Expected: FAIL because activation outcome helpers are missing.

**Step 3: Implement minimal code**

Extend `src/gaze/desktop/activation.py`:

```python
from enum import StrEnum

from gaze.core.state import GazeAppState
from gaze.dev.fakes import FakeFrontmostApp


class ActivationOutcome(StrEnum):
    DISABLED = "disabled"
    NO_TARGET = "no_target"
    ALREADY_FRONTMOST = "already_frontmost"
    SUCCESS = "success"
    UNAVAILABLE = "unavailable"


class TargetActivationService(Protocol):
    def activate_app(self, app_name: str) -> ActivationOutcome:
        """Activate the owning app by app name or return unavailable."""


class FakeActivationService:
    def __init__(self, *, frontmost: FakeFrontmostApp | None = None, should_succeed: bool = True) -> None:
        self._frontmost = frontmost or FakeFrontmostApp()
        self._should_succeed = should_succeed
        self.calls: list[str] = []

    def activate_app(self, app_name: str) -> ActivationOutcome:
        if self._frontmost.is_frontmost(app_name):
            return ActivationOutcome.ALREADY_FRONTMOST
        if not self._should_succeed:
            return ActivationOutcome.UNAVAILABLE
        self.calls.append(app_name)
        self._frontmost.set_frontmost(app_name)
        return ActivationOutcome.SUCCESS


def request_manual_activation(
    state: GazeAppState,
    service: TargetActivationService,
) -> ActivationOutcome:
    if not state.flags.gaze_enabled:
        return ActivationOutcome.DISABLED
    if state.activation_blocked or state.current_target is None:
        return ActivationOutcome.NO_TARGET
    return service.activate_app(state.current_target.app_name)
```

Keep the existing `ActivationService` protocol only if needed for compatibility; otherwise replace it with `TargetActivationService` if no callers use it.

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_activation_seam.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/desktop/activation.py tests/test_activation_seam.py
git commit -m "feat: add manual activation seam"
```

---

## Task 5: Add overlay style contract and recording fake overlay

**Objective:** Make overlay safety testable before building real AppKit drawing.

**Files:**
- Modify: `src/gaze/overlays/border.py`
- Test: `tests/test_border_overlay_contract.py`

**Step 1: Write failing tests**

Create `tests/test_border_overlay_contract.py`:

```python
from gaze.desktop.window_candidates import WindowCandidateSummary
from gaze.overlays.border import BorderOverlayStyle, RecordingBorderOverlay


def test_default_border_style_is_non_interactive() -> None:
    style = BorderOverlayStyle.default()

    assert style.ignores_mouse_events is True
    assert style.can_become_key is False
    assert style.activates_app is False
    assert style.opacity <= 0.35


def test_recording_overlay_tracks_show_and_hide_without_side_effects() -> None:
    overlay = RecordingBorderOverlay()
    candidate = WindowCandidateSummary("Terminal", 10, 20, 800, 600, confidence=0.9)

    overlay.show(candidate)
    overlay.hide()

    assert overlay.events == [("show", "Terminal"), ("hide", None)]
    assert overlay.visible is False
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_border_overlay_contract.py -v
```

Expected: FAIL because `BorderOverlayStyle` and `RecordingBorderOverlay` are missing.

**Step 3: Implement minimal code**

Extend `src/gaze/overlays/border.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class BorderOverlayStyle:
    ignores_mouse_events: bool
    can_become_key: bool
    activates_app: bool
    opacity: float
    line_width: float
    corner_radius: float

    @classmethod
    def default(cls) -> "BorderOverlayStyle":
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
```

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_border_overlay_contract.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/overlays/border.py tests/test_border_overlay_contract.py
git commit -m "feat: add border overlay safety contract"
```

---

## Task 6: Add prototype orchestrator for fake trust loop

**Objective:** Connect fake target source, lock policy, app state, overlay seam, and activation seam in pure code.

**Files:**
- Create: `src/gaze/core/prototype.py`
- Test: `tests/test_fake_prototype_controller.py`

**Step 1: Write failing tests**

Create `tests/test_fake_prototype_controller.py`:

```python
from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import ActivationOutcome, FakeActivationService
from gaze.dev.fakes import FakeTarget
from gaze.overlays.border import RecordingBorderOverlay


def test_locked_fake_target_shows_overlay_after_stability_threshold() -> None:
    overlay = RecordingBorderOverlay()
    controller = FakePrototypeController(overlay=overlay, activation=FakeActivationService())
    controller.enable_gaze()
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))

    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    assert controller.state.current_target is not None
    assert controller.state.current_target.locked is True
    assert overlay.visible is True


def test_disable_hides_overlay_and_blocks_activation() -> None:
    overlay = RecordingBorderOverlay()
    service = FakeActivationService()
    controller = FakePrototypeController(overlay=overlay, activation=service)
    controller.enable_gaze()
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))
    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    controller.disable_gaze()
    outcome = controller.activate()

    assert overlay.visible is False
    assert outcome == ActivationOutcome.DISABLED
    assert service.calls == []


def test_activation_success_updates_status() -> None:
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    controller.enable_gaze()
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))
    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    outcome = controller.activate()

    assert outcome == ActivationOutcome.SUCCESS
    assert controller.state.last_status_message == "Activated Terminal"


def test_no_target_activation_reports_no_target() -> None:
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    controller.enable_gaze()

    outcome = controller.activate()

    assert outcome == ActivationOutcome.NO_TARGET
    assert controller.state.last_status_message == "No target"


def test_tick_while_disabled_does_not_show_target_or_overlay() -> None:
    overlay = RecordingBorderOverlay()
    controller = FakePrototypeController(overlay=overlay, activation=FakeActivationService())
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))

    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    assert controller.state.current_target is None
    assert overlay.visible is False
    assert controller.activate() == ActivationOutcome.DISABLED
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_fake_prototype_controller.py -v
```

Expected: FAIL because `gaze.core.prototype` is missing.

**Step 3: Implement minimal code**

Create `src/gaze/core/prototype.py`:

```python
"""Pure fake prototype controller for the first Gaze trust loop."""

from __future__ import annotations

from dataclasses import replace

from gaze.core.state import CalibrationStatus, GazeAppState, GazeFeatureFlags, GazeReadiness
from gaze.core.target_lock import TargetLockPolicy, TargetObservation
from gaze.desktop.activation import ActivationOutcome, TargetActivationService, request_manual_activation
from gaze.dev.fakes import FakeTarget, FakeTargetController
from gaze.overlays.border import TargetBorderOverlay


class FakePrototypeController:
    def __init__(
        self,
        *,
        overlay: TargetBorderOverlay,
        activation: TargetActivationService,
        target_controller: FakeTargetController | None = None,
    ) -> None:
        self._overlay = overlay
        self._activation = activation
        self._targets = target_controller or FakeTargetController()
        self._lock = TargetLockPolicy(stability_ms=400)
        self.state = GazeAppState.default()

    def enable_gaze(self) -> None:
        self.state = replace(
            self.state,
            flags=replace(self.state.flags, gaze_enabled=True),
            readiness=GazeReadiness(
                calibration=CalibrationStatus.READY,
                camera_available=True,
                tracker_available=True,
            ),
            last_status_message="Gaze ready",
        )

    def disable_gaze(self) -> None:
        self.state = self.state.disable_panic()
        self._overlay.hide()

    def set_fake_target(self, target: FakeTarget) -> None:
        self._targets.set_manual_target(target)

    def clear_fake_target(self) -> None:
        self._targets.clear_target()

    def tick(self, *, now_ms: int) -> None:
        if not self.state.flags.gaze_enabled:
            self.state = self.state.with_target(None)
            self._overlay.hide()
            return

        fake_target = self._targets.current_fake_target()
        observation = None if fake_target is None else TargetObservation(fake_target.app_name, fake_target.confidence)
        lock = self._lock.update(observation, now_ms=now_ms)
        if fake_target is None or not lock.locked:
            self.state = self.state.with_target(None)
            self._overlay.hide()
            return

        target_summary = fake_target.as_target_summary(locked=True)
        self.state = self.state.with_target(target_summary)
        self._overlay.show(fake_target.as_window_candidate())

    def activate(self) -> ActivationOutcome:
        outcome = request_manual_activation(self.state, self._activation)
        message = {
            ActivationOutcome.DISABLED: "Gaze disabled",
            ActivationOutcome.NO_TARGET: "No target",
            ActivationOutcome.ALREADY_FRONTMOST: "Already frontmost",
            ActivationOutcome.SUCCESS: f"Activated {self.state.current_target.app_name if self.state.current_target else 'target'}",
            ActivationOutcome.UNAVAILABLE: "Activation unavailable",
        }[outcome]
        self.state = replace(self.state, last_status_message=message)
        return outcome
```

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_fake_prototype_controller.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/core/prototype.py tests/test_fake_prototype_controller.py
git commit -m "feat: wire fake prototype trust loop"
```

---

## Task 7: Add menu model, hotkey defaults, and command seams

**Objective:** Provide pure menu/dropdown items, default hotkeys, and callable command seams for Cmd+G / Option+Cmd+G without registering global hotkeys in tests.

**Files:**
- Modify: `src/gaze/hotkeys/bindings.py`
- Modify: `src/gaze/settings/defaults.py`
- Create: `src/gaze/hotkeys/commands.py`
- Create: `src/gaze/ui/menu_model.py`
- Test: `tests/test_menu_model.py`
- Test: `tests/test_hotkey_commands.py`

**Step 1: Write failing tests**

Create `tests/test_menu_model.py`:

```python
from gaze.core.state import CalibrationStatus, GazeAppState, GazeFeatureFlags, GazeReadiness, TargetSummary
from gaze.hotkeys.bindings import GAZE_TOGGLE_HOTKEY, MANUAL_ACTIVATE_HOTKEY
from gaze.ui.menu_model import menu_items_for_state


def test_default_hotkeys_match_design() -> None:
    assert MANUAL_ACTIVATE_HOTKEY == "cmd+g"
    assert GAZE_TOGGLE_HOTKEY == "option+cmd+g"


def test_menu_items_include_trust_controls_without_window_titles() -> None:
    state = GazeAppState(
        flags=GazeFeatureFlags(gaze_enabled=True),
        readiness=GazeReadiness(calibration=CalibrationStatus.READY, camera_available=True, tracker_available=True),
    ).with_target(TargetSummary(app_name="Terminal", confidence=0.91, locked=True))

    items = menu_items_for_state(state)
    labels = [item.label for item in items]

    assert "Status: ready" in labels
    assert "Target: Terminal" in labels
    assert "Calibration: ready" in labels
    assert "Confidence: 0.91" in labels
    assert "Lock: locked" in labels
    assert "Disable Gaze" in labels
    assert "Toggle Border" in labels
    assert "Toggle Heatmap" in labels
    assert "Recalibrate" in labels
    assert "Settings" in labels
    assert "Quit" in labels
    assert all(" - " not in label for label in labels)
```

Create `tests/test_hotkey_commands.py`:

```python
from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import ActivationOutcome, FakeActivationService
from gaze.dev.fakes import FakeTarget
from gaze.hotkeys.commands import GazeCommandController
from gaze.overlays.border import RecordingBorderOverlay


def test_toggle_gaze_command_enables_and_disables() -> None:
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    commands = GazeCommandController(controller)

    commands.toggle_gaze_command()
    assert controller.state.flags.gaze_enabled is True

    commands.toggle_gaze_command()
    assert controller.state.flags.gaze_enabled is False


def test_manual_activate_command_routes_to_fake_activation() -> None:
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    commands = GazeCommandController(controller)
    commands.toggle_gaze_command()
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.9))
    controller.tick(now_ms=1000)
    controller.tick(now_ms=1400)

    assert commands.manual_activate_command() == ActivationOutcome.SUCCESS
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_menu_model.py tests/test_hotkey_commands.py -v
```

Expected: FAIL because `GAZE_TOGGLE_HOTKEY`, `menu_model`, and `hotkeys.commands` are missing.

**Step 3: Implement minimal code**

Update `src/gaze/hotkeys/bindings.py`:

```python
MANUAL_ACTIVATE_HOTKEY = "cmd+g"
GAZE_TOGGLE_HOTKEY = "option+cmd+g"
```

Update `src/gaze/settings/defaults.py`:

```python
from gaze.hotkeys.bindings import GAZE_TOGGLE_HOTKEY, MANUAL_ACTIVATE_HOTKEY

DEFAULT_GAZE_TOGGLE_HOTKEY = GAZE_TOGGLE_HOTKEY
```

Create `src/gaze/hotkeys/commands.py`:

```python
"""Callable command seams for hotkeys and menu actions."""

from __future__ import annotations

from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import ActivationOutcome


class GazeCommandController:
    def __init__(self, prototype: FakePrototypeController) -> None:
        self._prototype = prototype

    def manual_activate_command(self) -> ActivationOutcome:
        return self._prototype.activate()

    def toggle_gaze_command(self) -> None:
        if self._prototype.state.flags.gaze_enabled:
            self._prototype.disable_gaze()
        else:
            self._prototype.enable_gaze()
```

Create `src/gaze/ui/menu_model.py`:

```python
"""Pure menu model for the menu-bar dropdown."""

from __future__ import annotations

from dataclasses import dataclass

from gaze.core.state import GazeAppState


@dataclass(frozen=True)
class MenuItem:
    label: str
    action: str | None = None


def menu_items_for_state(state: GazeAppState) -> list[MenuItem]:
    target_label = "No target"
    confidence_label = "Confidence: --"
    lock_label = "Lock: unlocked"
    if state.current_target is not None:
        target_label = state.current_target.app_name
        confidence_label = f"Confidence: {state.current_target.confidence:.2f}"
        lock_label = "Lock: locked" if state.current_target.locked else "Lock: unlocked"

    return [
        MenuItem(f"Status: {state.menu_status}"),
        MenuItem(f"Calibration: {state.readiness.calibration.value}"),
        MenuItem(f"Target: {target_label}"),
        MenuItem(confidence_label),
        MenuItem(lock_label),
        MenuItem("Disable Gaze" if state.flags.gaze_enabled else "Enable Gaze", "toggle_gaze"),
        MenuItem("Toggle Border", "toggle_border"),
        MenuItem("Toggle Heatmap", "toggle_heatmap"),
        MenuItem("Recalibrate", "recalibrate"),
        MenuItem("Settings", "settings"),
        MenuItem("Quit", "quit"),
    ]
```

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_menu_model.py tests/test_hotkey_commands.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/hotkeys/bindings.py src/gaze/settings/defaults.py src/gaze/hotkeys/commands.py src/gaze/ui/menu_model.py tests/test_menu_model.py tests/test_hotkey_commands.py
git commit -m "feat: add menu trust controls and command seams"
```

---

## Task 8: Add setup/settings and Developer panel models plus runtime factory seams

**Objective:** Define product settings and developer controls as pure view models, plus import-safe runtime factory seams for the setup/settings window and separate development-gated Developer panel.

**Files:**
- Modify: `src/gaze/core/prototype.py`
- Modify: `src/gaze/desktop/activation.py`
- Modify: `src/gaze/dev/fakes.py`
- Modify: `src/gaze/ui/setup_window.py`
- Create: `src/gaze/ui/developer_panel.py`
- Create: `src/gaze/ui/window_factories.py`
- Create: `src/gaze/ui/developer_actions.py`
- Test: `tests/test_setup_and_developer_models.py`

**Step 1: Write failing tests**

Create `tests/test_setup_and_developer_models.py`:

```python
from gaze.ui.developer_panel import developer_controls
from gaze.ui.setup_window import setup_sections


def test_setup_window_contains_mvp_essentials_only() -> None:
    sections = setup_sections()
    labels = [section.label for section in sections]

    assert labels == [
        "Privacy & Trust",
        "Calibration",
        "Hotkeys",
        "Border",
        "Heatmap",
        "Diagnostics",
    ]
    assert "Auto Activation" not in labels
    assert "Per-App Policy" not in labels


def test_developer_panel_controls_are_separate_from_setup() -> None:
    controls = developer_controls()
    labels = [control.label for control in controls]

    assert "Start Scripted Demo" in labels
    assert "Set Fake Target" in labels
    assert "Set Fake Target Bounds" in labels
    assert "Set Fake Confidence" in labels
    assert "Set Fake Lock State" in labels
    assert "Set Fake Frontmost App" in labels
    assert "Trigger Activation Success" in labels
    assert "Trigger Activation Failure" in labels
    assert "Trigger No Target" in labels
    assert "Trigger Degraded" in labels


def test_runtime_window_factories_are_import_safe_without_appkit() -> None:
    from gaze.ui.window_factories import create_developer_panel, create_settings_window

    assert create_settings_window(appkit=None) is None
    assert create_developer_panel(appkit=None, development_mode=True) is None


def test_developer_panel_is_development_gated() -> None:
    from gaze.ui.window_factories import create_developer_panel

    assert create_developer_panel(appkit=object(), development_mode=False) is None


def test_developer_actions_drive_fake_controller() -> None:
    from gaze.core.prototype import FakePrototypeController
    from gaze.desktop.activation import ActivationOutcome, FakeActivationService
    from gaze.overlays.border import RecordingBorderOverlay
    from gaze.ui.developer_actions import DeveloperPanelActions

    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    actions = DeveloperPanelActions(controller)

    actions.set_fake_target(app_name="Terminal", x=10, y=20, width=800, height=600, confidence=0.91)
    actions.enable_gaze()
    actions.tick(now_ms=1000)
    actions.tick(now_ms=1400)

    assert controller.state.current_target is not None
    assert controller.state.current_target.app_name == "Terminal"
    assert actions.manual_activate() == ActivationOutcome.SUCCESS


def test_developer_actions_cover_every_fake_control() -> None:
    from gaze.core.prototype import FakePrototypeController
    from gaze.desktop.activation import ActivationOutcome, FakeActivationService
    from gaze.overlays.border import RecordingBorderOverlay
    from gaze.ui.developer_actions import DeveloperPanelActions

    service = FakeActivationService()
    controller = FakePrototypeController(overlay=RecordingBorderOverlay(), activation=service)
    actions = DeveloperPanelActions(controller)

    actions.start_scripted_demo()
    actions.advance_scripted_demo(now_ms=1000)
    assert controller.state.last_status_message == "Scripted demo running"

    actions.stop_scripted_demo()
    assert controller.state.last_status_message == "Scripted demo stopped"

    actions.set_fake_target(app_name="Terminal", x=10, y=20, width=800, height=600, confidence=0.5)
    actions.set_fake_target_bounds(x=20, y=30, width=700, height=500)
    actions.set_fake_confidence(0.96)
    actions.set_fake_lock_state(True)
    assert controller.state.current_target is not None
    assert controller.state.current_target.confidence == 0.96
    assert controller.state.current_target.locked is True

    actions.set_fake_frontmost_app("Terminal")
    assert actions.manual_activate() == ActivationOutcome.ALREADY_FRONTMOST

    actions.trigger_activation_failure()
    actions.set_fake_frontmost_app(None)
    assert actions.manual_activate() == ActivationOutcome.UNAVAILABLE

    actions.trigger_activation_success()
    assert actions.manual_activate() == ActivationOutcome.SUCCESS

    actions.trigger_no_target()
    assert controller.state.current_target is None

    actions.trigger_degraded()
    assert controller.state.readiness.calibration.value == "degraded"
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_setup_and_developer_models.py -v
```

Expected: FAIL because functions/modules are missing.

**Step 3: Implement minimal code**

Update `src/gaze/ui/setup_window.py`:

```python
from dataclasses import dataclass

WINDOW_TITLE = "Gaze"


@dataclass(frozen=True)
class SetupSection:
    label: str
    description: str


def setup_sections() -> list[SetupSection]:
    return [
        SetupSection("Privacy & Trust", "No recording, no screenshots, no clicks, manual activation only."),
        SetupSection("Calibration", "Start or retry calibration just in time."),
        SetupSection("Hotkeys", "Edit Cmd+G activation and Option+Cmd+G toggle."),
        SetupSection("Border", "Control target border preview."),
        SetupSection("Heatmap", "Optional session-local diagnostic overlay."),
        SetupSection("Diagnostics", "Scalar-only diagnostics profile."),
    ]
```

Create `src/gaze/ui/developer_panel.py`:

```python
"""Development-only panel model for fake prototype controls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeveloperControl:
    label: str
    action: str


def developer_controls() -> list[DeveloperControl]:
    return [
        DeveloperControl("Start Scripted Demo", "start_scripted_demo"),
        DeveloperControl("Stop Scripted Demo", "stop_scripted_demo"),
        DeveloperControl("Set Fake Target", "set_fake_target"),
        DeveloperControl("Set Fake Target Bounds", "set_fake_target_bounds"),
        DeveloperControl("Set Fake Confidence", "set_fake_confidence"),
        DeveloperControl("Set Fake Lock State", "set_fake_lock_state"),
        DeveloperControl("Set Fake Frontmost App", "set_fake_frontmost_app"),
        DeveloperControl("Trigger Activation Success", "trigger_activation_success"),
        DeveloperControl("Trigger Activation Failure", "trigger_activation_failure"),
        DeveloperControl("Trigger No Target", "trigger_no_target"),
        DeveloperControl("Trigger Degraded", "trigger_degraded"),
    ]
```
Create `src/gaze/ui/developer_actions.py`:

```python
"""Development-only action wiring for fake prototype controls."""

from __future__ import annotations

from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import ActivationOutcome
from gaze.dev.fakes import FakeTarget


class DeveloperPanelActions:
    def __init__(self, controller: FakePrototypeController) -> None:
        self._controller = controller

    def enable_gaze(self) -> None:
        self._controller.enable_gaze()

    def tick(self, *, now_ms: int) -> None:
        self._controller.tick(now_ms=now_ms)

    def start_scripted_demo(self) -> None:
        self._controller.start_scripted_demo()

    def stop_scripted_demo(self) -> None:
        self._controller.stop_scripted_demo()

    def advance_scripted_demo(self, *, now_ms: int) -> None:
        self._controller.advance_scripted_demo(now_ms=now_ms)

    def set_fake_target(
        self,
        *,
        app_name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        confidence: float,
    ) -> None:
        self._controller.set_fake_target(FakeTarget(app_name, x, y, width, height, confidence))

    def set_fake_target_bounds(self, *, x: int, y: int, width: int, height: int) -> None:
        self._controller.set_fake_target_bounds(x=x, y=y, width=width, height=height)

    def set_fake_confidence(self, confidence: float) -> None:
        self._controller.set_fake_confidence(confidence)

    def set_fake_lock_state(self, locked: bool) -> None:
        self._controller.override_fake_lock_state(locked)

    def set_fake_frontmost_app(self, app_name: str | None) -> None:
        self._controller.set_fake_frontmost_app(app_name)

    def trigger_activation_success(self) -> None:
        self._controller.set_activation_success(True)

    def trigger_activation_failure(self) -> None:
        self._controller.set_activation_success(False)

    def trigger_no_target(self) -> None:
        self._controller.clear_fake_target()

    def trigger_degraded(self) -> None:
        self._controller.mark_calibration_degraded()

    def manual_activate(self) -> ActivationOutcome:
        return self._controller.activate()
```

Also extend the fake seams in `src/gaze/core/prototype.py`, `src/gaze/desktop/activation.py`, and `src/gaze/dev/fakes.py` to support these actions directly:
- `FakePrototypeController.start_scripted_demo()` / `stop_scripted_demo()` / `advance_scripted_demo(now_ms=...)`
- `FakePrototypeController.set_fake_target_bounds(...)`
- `FakePrototypeController.set_fake_confidence(...)`
- `FakePrototypeController.override_fake_lock_state(...)`
- `FakePrototypeController.set_fake_frontmost_app(app_name: str | None)`
- `FakePrototypeController.set_activation_success(success: bool)` backed by mutable `FakeActivationService`
- `FakePrototypeController.mark_calibration_degraded()`

These are fake-only development controls. They must not start camera access, enumerate real windows, or activate real apps.

Create `src/gaze/ui/window_factories.py`:

```python
"""Runtime AppKit window factory seams for settings and developer panels."""

from __future__ import annotations

from typing import Any


def create_settings_window(appkit: Any | None) -> Any | None:
    if appkit is None:
        return None
    # Real NSWindow construction belongs here during implementation.
    return appkit.NSWindow.alloc().init()


def create_developer_panel(
    appkit: Any | None,
    *,
    development_mode: bool,
    actions: DeveloperPanelActions | None = None,
) -> Any | None:
    if appkit is None or not development_mode or actions is None:
        return None
    # Build a real NSPanel/NSWindow with one control per developer_controls() item.
    # Every control must have a non-null action/target wired to DeveloperPanelActions.
    return appkit.NSWindow.alloc().init()
```

Runtime acceptance for this task:
- Settings window opens only from menu action.
- Developer panel is separate from settings.
- Developer panel is hidden when development mode is false.
- Developer panel controls are wired to fake controller/command seams before Gate 2 validation.
- `create_developer_panel(..., actions=DeveloperPanelActions(...))` builds a real runtime panel, not an empty window.
- Every `developer_controls()` item creates a runtime control with a non-null target/action.
- Developer panel actions include start/stop scripted sequence, target app, target bounds, confidence, lock state, fake frontmost app, activation success, activation failure, no target, and degraded state.


**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_setup_and_developer_models.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/core/prototype.py src/gaze/desktop/activation.py src/gaze/dev/fakes.py src/gaze/ui/setup_window.py src/gaze/ui/developer_panel.py src/gaze/ui/window_factories.py src/gaze/ui/developer_actions.py tests/test_setup_and_developer_models.py
git commit -m "feat: add setup and developer panel seams"
```

---

## Task 9: Add real menu-bar runtime shell without import-time side effects

**Objective:** Create the runtime menu bar status item and dropdown from pure menu/action models, with menu actions wired to command/window seams, while keeping imports side-effect free and avoiding a dashboard window at launch.

**Files:**
- Modify: `src/gaze/app.py`
- Create: `src/gaze/ui/appkit_shell.py`
- Modify: `src/gaze/ui/window_factories.py`
- Test: `tests/test_import_safety.py`
- Test: `tests/test_appkit_shell_model.py`

**Step 1: Write failing tests**

Create `tests/test_import_safety.py`:

```python
import importlib
import sys


def test_importing_app_does_not_import_appkit() -> None:
    sys.modules.pop("AppKit", None)

    importlib.import_module("gaze.app")

    assert "AppKit" not in sys.modules


def test_importing_appkit_shell_does_not_import_appkit() -> None:
    sys.modules.pop("AppKit", None)

    shell = importlib.import_module("gaze.ui.appkit_shell")

    assert "AppKit" not in sys.modules
    assert hasattr(shell, "build_menu_bar_app")
```

Create `tests/test_appkit_shell_model.py` with fake AppKit objects, not real AppKit:

```python
from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import FakeActivationService
from gaze.overlays.border import RecordingBorderOverlay
from gaze.ui.appkit_shell import build_menu_bar_app


class FakeStatusItem:
    def __init__(self) -> None:
        self.menu = None

    def button(self):
        return self

    def setTitle_(self, title: str) -> None:
        self.title = title

    def setMenu_(self, menu) -> None:
        self.menu = menu


class FakeStatusBar:
    def __init__(self) -> None:
        self.item = FakeStatusItem()

    def statusItemWithLength_(self, length: float) -> FakeStatusItem:
        self.length = length
        return self.item


class FakeApplication:
    def __init__(self) -> None:
        self.policy = None

    def setActivationPolicy_(self, policy: int) -> None:
        self.policy = policy


class FakeMenu:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.raw_items = []

    def addItem_(self, item) -> None:
        self.items.append(item.title)
        self.raw_items.append(item)


class FakeMenuItem:
    def __init__(self) -> None:
        self.title = ""
        self.action = None
        self.target = None

    @classmethod
    def alloc(cls):
        return cls()

    def initWithTitle_action_keyEquivalent_(self, title: str, action, key: str):
        self.title = title
        self.action = action
        return self

    def setTarget_(self, target) -> None:
        self.target = target

    def setAction_(self, action) -> None:
        self.action = action


class FakeAppKit:
    NSApplicationActivationPolicyAccessory = 1
    NSSquareStatusItemLength = -2.0
    NSMenuItem = FakeMenuItem

    def __init__(self) -> None:
        self.application = FakeApplication()
        self.status_bar = FakeStatusBar()

    def NSApplication(self):
        raise AssertionError("Use sharedApplication shape below")

    class NSApplication:
        _app = FakeApplication()

        @classmethod
        def sharedApplication(cls):
            return cls._app

    class NSStatusBar:
        _bar = FakeStatusBar()

        @classmethod
        def systemStatusBar(cls):
            return cls._bar

    NSMenu = FakeMenu


def test_build_menu_bar_app_creates_status_item_and_menu() -> None:
    appkit = FakeAppKit()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )

    runtime = build_menu_bar_app(appkit=appkit, controller=controller, development_mode=True)

    assert runtime.app.policy == appkit.NSApplicationActivationPolicyAccessory
    assert runtime.status_item.menu is not None
    assert "Status: off" in runtime.status_item.menu.items
    assert "Settings" in runtime.status_item.menu.items
    assert "Open Developer Panel" in runtime.status_item.menu.items
    action_items = {item.title: item for item in runtime.status_item.menu.raw_items if item.action is not None}
    assert "Settings" in action_items
    assert "Open Developer Panel" in action_items
    assert "Enable Gaze" in action_items
    assert "Toggle Border" in action_items
    assert "Toggle Heatmap" in action_items
    assert "Recalibrate" in action_items
    assert "Quit" in action_items


def test_every_menu_model_action_has_runtime_selector() -> None:
    from gaze.core.state import GazeAppState
    from gaze.ui.appkit_shell import selector_for_menu_action
    from gaze.ui.menu_model import menu_items_for_state

    actions = [item.action for item in menu_items_for_state(GazeAppState.default()) if item.action]

    assert actions
    assert all(selector_for_menu_action(action) is not None for action in actions)
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_import_safety.py tests/test_appkit_shell_model.py -v
```

Expected: FAIL because `gaze.ui.appkit_shell` and/or `build_menu_bar_app(appkit=..., controller=...)` is missing.

**Step 3: Implement minimal runtime shell**

Create `src/gaze/ui/appkit_shell.py`:

```python
"""Runtime AppKit shell builders.

Importing this module must not import AppKit. Call `build_menu_bar_app()` only from runtime launch code.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, cast

from gaze.core.prototype import FakePrototypeController
from gaze.hotkeys.commands import GazeCommandController
from gaze.ui.menu_model import MenuItem, menu_items_for_state
from gaze.ui.window_factories import create_developer_panel, create_settings_window


@dataclass(frozen=True)
class MenuBarRuntime:
    app: Any
    status_item: Any
    menu: Any
    action_dispatcher: MenuActionDispatcher


class MenuActionDispatcher:
    """Runtime target for menu item actions."""

    def __init__(self, *, appkit: Any, controller: FakePrototypeController, development_mode: bool) -> None:
        self._appkit = appkit
        self._controller = controller
        self._commands = GazeCommandController(controller)
        self._development_mode = development_mode
        self.settings_window: Any | None = None
        self.developer_panel: Any | None = None

    def toggle_gaze_(self, sender: Any | None = None) -> None:
        self._commands.toggle_gaze_command()

    def settings_(self, sender: Any | None = None) -> None:
        self.settings_window = create_settings_window(self._appkit)

    def developer_panel_(self, sender: Any | None = None) -> None:
        self.developer_panel = create_developer_panel(
            self._appkit,
            development_mode=self._development_mode,
            actions=self._controller.developer_actions(),
        )

    def toggle_border_(self, sender: Any | None = None) -> None:
        self._controller.toggle_border_enabled()

    def toggle_heatmap_(self, sender: Any | None = None) -> None:
        self._controller.toggle_heatmap_enabled()

    def recalibrate_(self, sender: Any | None = None) -> None:
        self._controller.start_fake_recalibration()

    def quit_(self, sender: Any | None = None) -> None:
        self._appkit.NSApplication.sharedApplication().terminate_(sender)


def _load_appkit() -> Any:
    return cast(Any, import_module("AppKit"))


def selector_for_menu_action(action_name: str) -> str | None:
    selectors = {
        "toggle_gaze": "toggle_gaze:",
        "toggle_border": "toggle_border:",
        "toggle_heatmap": "toggle_heatmap:",
        "recalibrate": "recalibrate:",
        "settings": "settings:",
        "developer_panel": "developer_panel:",
        "quit": "quit:",
    }
    return selectors.get(action_name)


def _menu_item(appkit: Any, item: MenuItem, dispatcher: MenuActionDispatcher) -> Any:
    action = selector_for_menu_action(item.action) if item.action is not None else None
    menu_item = appkit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        item.label,
        action,
        "",
    )
    if action is not None:
        menu_item.setTarget_(dispatcher)
    return menu_item


def build_menu_bar_app(
    *,
    appkit: Any | None = None,
    controller: FakePrototypeController,
    development_mode: bool,
) -> MenuBarRuntime:
    appkit = appkit or _load_appkit()
    app = appkit.NSApplication.sharedApplication()
    app.setActivationPolicy_(appkit.NSApplicationActivationPolicyAccessory)

    status_item = appkit.NSStatusBar.systemStatusBar().statusItemWithLength_(
        appkit.NSSquareStatusItemLength
    )
    status_item.button().setTitle_("◉")

    dispatcher = MenuActionDispatcher(
        appkit=appkit,
        controller=controller,
        development_mode=development_mode,
    )

    menu = appkit.NSMenu()
    items = menu_items_for_state(controller.state)
    if development_mode:
        items.append(MenuItem("Open Developer Panel", "developer_panel"))
    for item in items:
        menu.addItem_(_menu_item(appkit, item, dispatcher))
    status_item.setMenu_(menu)
    return MenuBarRuntime(app=app, status_item=status_item, menu=menu, action_dispatcher=dispatcher)
```

Update `src/gaze/app.py` so `main()` constructs the fake prototype runtime and calls `build_menu_bar_app()` at runtime only. Keep the `AppKit` import inside runtime code. Do not call `activateIgnoringOtherApps_`; the menu-bar utility must not steal focus at launch.

Also extend `FakePrototypeController` with menu-safe fake actions used above:
- `toggle_border_enabled()` hides the overlay immediately when disabling border.
- `toggle_heatmap_enabled()` only toggles state; it does not start capture/logging.
- `start_fake_recalibration()` changes fake calibration/status only; it does not request camera permission.
- `developer_actions()` returns `DeveloperPanelActions(self)` for runtime panel wiring.

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_import_safety.py tests/test_appkit_shell_model.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/app.py src/gaze/ui/appkit_shell.py tests/test_import_safety.py tests/test_appkit_shell_model.py
git commit -m "feat: add menu bar runtime shell"
```

Runtime/manual acceptance:
- App launches as menu-bar accessory utility.
- No persistent dashboard window opens by default.
- Menu includes status, target/no target, confidence, enable/disable, border, heatmap, recalibrate, settings, Developer panel in development mode, and quit.
- Menu labels never include window titles.
- Settings menu action opens settings window only on request.
- Developer panel menu action opens Developer panel only in development mode.
- Enable/disable menu action calls the same `GazeCommandController` seam tested by hotkey command tests.
- Border, heatmap, recalibrate, settings, Developer panel, and quit menu actions all have runtime selectors and fake-safe dispatcher methods.

---

## Task 10: Add real AppKit border overlay implementation behind runtime import

**Objective:** Implement the real non-interactive AppKit border overlay for fake candidate bounds, including visible thin outline + soft glow drawing, while keeping tests headless and import-safe.

**Files:**
- Modify: `src/gaze/overlays/border.py`
- Modify: `src/gaze/app.py`
- Test: `tests/test_border_overlay_contract.py`

**Step 1: Write failing tests**

Append to `tests/test_border_overlay_contract.py`:

```python
def test_appkit_overlay_factory_is_import_safe() -> None:
    from gaze.overlays.border import create_appkit_border_overlay

    overlay = create_appkit_border_overlay(appkit=None)

    assert overlay is None


def test_appkit_overlay_uses_non_interactive_style_contract() -> None:
    from gaze.overlays.border import BorderOverlayStyle, appkit_overlay_window_config

    config = appkit_overlay_window_config(BorderOverlayStyle.default())

    assert config["ignores_mouse_events"] is True
    assert config["can_become_key"] is False
    assert config["activates_app"] is False
    assert config["draws_thin_outline"] is True
    assert config["draws_soft_glow"] is True
```

**Step 2: Verify RED**

Run:

```bash
uv run pytest tests/test_border_overlay_contract.py -v
```

Expected: FAIL because `create_appkit_border_overlay` and `appkit_overlay_window_config` are missing.

**Step 3: Implement real runtime overlay behind seam**

Extend `src/gaze/overlays/border.py`. Type runtime AppKit objects as `Any` so `ty` does not reject dynamic PyObjC attribute access.

```python
from typing import Any


def appkit_overlay_window_config(style: BorderOverlayStyle) -> dict[str, bool | float]:
    return {
        "ignores_mouse_events": style.ignores_mouse_events,
        "can_become_key": style.can_become_key,
        "activates_app": style.activates_app,
        "opacity": style.opacity,
        "line_width": style.line_width,
        "corner_radius": style.corner_radius,
        "draws_thin_outline": True,
        "draws_soft_glow": True,
    }


class AppKitBorderOverlay:
    def __init__(self, appkit: Any, *, style: BorderOverlayStyle | None = None) -> None:
        self._appkit = appkit
        self._style = style or BorderOverlayStyle.default()
        self._window: Any | None = None

    def _make_content_view(self, frame: Any) -> Any:
        """Create the visible border/glow view.

        Minimal implementation requirement:
        - transparent background
        - CALayer or drawRect path for rounded thin outline
        - soft glow/shadow outside the outline
        - no mouse/key handling
        """
        appkit = self._appkit
        view = appkit.NSView.alloc().initWithFrame_(frame)
        view.setWantsLayer_(True)
        layer = view.layer()
        layer.setBorderWidth_(self._style.line_width)
        layer.setCornerRadius_(self._style.corner_radius)
        layer.setShadowOpacity_(self._style.opacity)
        layer.setShadowRadius_(10.0)
        return view

    def _make_window(self, candidate: WindowCandidateSummary) -> Any:
        appkit = self._appkit
        rect = appkit.NSMakeRect(
            candidate.bounds_x,
            candidate.bounds_y,
            candidate.bounds_width,
            candidate.bounds_height,
        )
        window = appkit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect,
            appkit.NSWindowStyleMaskBorderless,
            appkit.NSBackingStoreBuffered,
            False,
        )
        window.setOpaque_(False)
        window.setBackgroundColor_(appkit.NSColor.clearColor())
        window.setIgnoresMouseEvents_(self._style.ignores_mouse_events)
        window.setCanHide_(False)
        window.setLevel_(appkit.NSStatusWindowLevel)
        window.setCollectionBehavior_(
            appkit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | appkit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        window.setContentView_(self._make_content_view(rect))
        return window

    def show(self, candidate: WindowCandidateSummary) -> None:
        rect = self._appkit.NSMakeRect(
            candidate.bounds_x,
            candidate.bounds_y,
            candidate.bounds_width,
            candidate.bounds_height,
        )
        if self._window is None:
            self._window = self._make_window(candidate)
        else:
            self._window.setFrame_display_(rect, True)
        self._window.orderFrontRegardless()

    def hide(self) -> None:
        if self._window is not None:
            self._window.orderOut_(None)


def create_appkit_border_overlay(appkit: Any | None = None) -> TargetBorderOverlay | None:
    if appkit is None:
        return None
    return AppKitBorderOverlay(appkit)
```

Update `src/gaze/app.py` so runtime construction uses `create_appkit_border_overlay(appkit)` for the fake prototype when AppKit is available, falling back to `RecordingBorderOverlay` only in tests/headless mode. This task must wire the real overlay into the runtime fake prototype; creating the factory alone is not enough.

**Step 4: Verify GREEN**

Run:

```bash
uv run pytest tests/test_border_overlay_contract.py -v
make check
```

Expected: focused tests pass; full gate passes.

**Step 5: Commit**

```bash
git add src/gaze/app.py src/gaze/overlays/border.py tests/test_border_overlay_contract.py
git commit -m "feat: add AppKit border overlay runtime"
```

Runtime/manual acceptance:
- Border appears around fake candidate bounds.
- Border visibly renders thin outline and soft glow.
- Border is click-through.
- Border does not become key/main window.
- Border does not activate the app or steal focus.
- Border hides on no-target and disable.

---

## Task 11: Add fake prototype manual validation checklist

**Objective:** Capture manual evidence required before moving to real camera/window APIs.

**Files:**
- Create: `docs/validation/fake-prototype-checklist.md`

**Step 1: Create checklist**

Create `docs/validation/fake-prototype-checklist.md`:

```markdown
# Gaze Fake Prototype Validation Checklist

Date:
Operator: Sage
Commit:

## Automated Gate

- [ ] `make check` passes.

## Import Safety

- [ ] Importing `gaze.app` does not start camera access.
- [ ] Importing `gaze.app` does not enumerate windows.
- [ ] Importing `gaze.app` does not register hotkeys.
- [ ] Importing `gaze.app` does not draw overlays.
- [ ] Importing `gaze.app` does not activate apps.

## Menu-Bar Utility Shape

- [ ] App launches as menu-bar utility.
- [ ] No persistent dashboard window opens by default.
- [ ] Menu includes status, target app/no target, confidence, enable/disable, border, heatmap, recalibrate, settings, Developer panel in development mode, quit.
- [ ] Menu actions call the same command seams used by tests.
- [ ] Menu shows app names only; no window titles.

## Setup and Developer Panel

- [ ] Settings window opens only from menu action.
- [ ] Developer panel is separate from setup/settings.
- [ ] Developer panel is development-gated.
- [ ] Scripted fake sequence can run.
- [ ] Manual fake target can be selected.
- [ ] Fake frontmost app can be set.
- [ ] No-target state can be triggered.
- [ ] Activation failure state can be triggered.
- [ ] Degraded state can be triggered.

## Border Overlay

- [ ] Border appears around fake target bounds after lock.
- [ ] Border hides on no-target.
- [ ] Border hides on disable.
- [ ] Border does not intercept mouse clicks.
- [ ] Border does not steal key focus.

## Activation Seam

- [ ] Cmd+G/activation command does nothing while disabled.
- [ ] Cmd+G/activation command reports no target when no target is locked.
- [ ] Cmd+G/activation command reports Already frontmost when fake target is frontmost.
- [ ] Cmd+G/activation command reports success for non-frontmost locked fake target.
- [ ] Activation failure shows subtle status/toast, not a modal.

## Panic Disable

- [ ] Disable clears target.
- [ ] Disable hides overlay.
- [ ] Disable blocks activation.

## Privacy

- [ ] No screenshots are saved.
- [ ] No camera frames are saved.
- [ ] No window titles are shown or logged.
- [ ] No raw desktop content is logged/exported.
```

**Step 2: Verify docs path**

Run:

```bash
git diff --check
make check
```

Expected: no whitespace errors; full gate passes.

**Step 3: Commit**

```bash
git add docs/validation/fake-prototype-checklist.md
git commit -m "docs: add fake prototype validation checklist"
```

---

## Task 12: Final fake-prototype implementation review gate

**Objective:** Verify the first implementation slice is complete and safe before real tracking work.

**Files:**
- Modify if needed: `docs/plans/gaze-task-graphs.md` only to mark notes/discoveries; do not change product scope without approval.

**Step 1: Run full gate**

```bash
make check
```

Expected: ruff passes, ty passes, pytest passes.

**Step 2: Inspect git state and recent commits**

```bash
git status --short
git log --oneline -12
```

Expected: clean tree, task commits present.

**Step 3: Confirm fake prototype acceptance criteria**

Check against `docs/plans/gaze-task-graphs.md` GAZE-001 through GAZE-010:

- Safe foundation.
- Runtime menu-bar shell manually validated.
- Safety/privacy policies.
- Setup/settings runtime shell opens only when requested.
- Separate Developer panel opens in development mode and drives fake states.
- Fake gaze/candidate/frontmost services.
- Target lock policy.
- Real AppKit border overlay appears around fake bounds and is click-through.
- Cmd+G and Option+Cmd+G command seams work through fake activation/toggle.
- Disable/panic clears target, hides overlay, and blocks activation.
- Manual validation checklist exists and is ready to run.

Do not start GAZE-020 or any real camera/window work until this gate passes.

**Step 4: Report outcome**

Report:
- Files changed.
- Commits created.
- RED/GREEN evidence for each task.
- `make check` result.
- Any manual validation still required.
- Whether Gate 2, Fake prototype safe, is ready for user-run manual validation.

---

## Execution Rules

For each task:

1. Inspect current file state before editing.
2. Write the failing test first.
3. Run the focused test and verify RED.
4. Implement minimal production code.
5. Run the focused test and verify GREEN.
6. Run `make check`.
7. Run `git diff --check`.
8. Inspect `git status --short`.
9. Commit with the task commit message.
10. Do not start the next task with uncommitted changes unless the current task is intentionally docs-only and explicitly staged/committed.

If implementation reveals that a planned API is awkward, pause and update this plan before continuing. Do not silently drift from the approved spec.

## Handoff After Plan

When this plan is complete and committed, execution can proceed task-by-task. Recommended execution style:

- One fresh implementation subagent per task.
- TDD enforced in the task prompt.
- Spec compliance review after each task.
- Code quality review after spec passes.
- Commit after every approved task.
