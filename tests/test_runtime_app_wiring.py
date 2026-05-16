from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gaze.core.display_geometry import DisplayGeometry, DisplayLayoutSnapshot
from gaze.core.prototype import FakePrototypeController
from gaze.core.state import CalibrationStatus
from gaze.desktop.activation import FakeActivationService
from gaze.overlays.border import RecordingBorderOverlay
from gaze.tracking.calibration import CalibrationResult
from gaze.ui.appkit_shell import build_menu_bar_app


class RecordingCalibrationSession:
    def __init__(self) -> None:
        self.starts = 0

    def start(self) -> CalibrationResult:
        self.starts += 1
        return CalibrationResult.ready(display_layout=display_layout())


class NullSampleSource:
    def current_sample(self) -> None:
        return None


class EmptyWindowProvider:
    def current_candidates(self) -> tuple[()]:
        return ()


class StaticDisplayProvider:
    def current_layout(self) -> DisplayLayoutSnapshot:
        return display_layout()


def display_layout() -> DisplayLayoutSnapshot:
    return DisplayLayoutSnapshot(
        displays=(
            DisplayGeometry(
                display_id=1,
                x=0,
                y=0,
                width=1440,
                height=900,
                scale=2.0,
                built_in=True,
            ),
        )
    )


class FakeStatusItem:
    def __init__(self) -> None:
        self.menu = None

    def button(self) -> FakeStatusItem:
        return self

    def setTitle_(self, title: str) -> None:
        self.title = title

    def setMenu_(self, menu: Any) -> None:
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

    def terminate_(self, sender: object) -> None:
        self.terminated_by = sender


class FakeMenu:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.raw_items: list[FakeMenuItem] = []

    def addItem_(self, item: FakeMenuItem) -> None:
        self.items.append(item.title)
        self.raw_items.append(item)

    def removeAllItems(self) -> None:
        self.items = []
        self.raw_items = []


class FakeMenuItem:
    def __init__(self) -> None:
        self.title = ""
        self.action = None
        self.key = ""
        self.target = None
        self.modifier_mask = None

    @classmethod
    def alloc(cls) -> FakeMenuItem:
        return cls()

    def initWithTitle_action_keyEquivalent_(
        self,
        title: str,
        action: Any,
        key: str,
    ) -> FakeMenuItem:
        self.title = title
        self.action = action
        self.key = key
        return self

    def setTarget_(self, target: object) -> None:
        self.target = target

    def setKeyEquivalentModifierMask_(self, mask: int) -> None:
        self.modifier_mask = mask


class FakeAppKit:
    NSApplicationActivationPolicyAccessory = 1
    NSSquareStatusItemLength = -2.0
    NSEventModifierFlagCommand = 1
    NSEventModifierFlagOption = 2
    NSMenuItem = FakeMenuItem

    class NSApplication:
        _app = FakeApplication()

        @classmethod
        def sharedApplication(cls) -> FakeApplication:
            return cls._app

    class NSStatusBar:
        _bar = FakeStatusBar()

        @classmethod
        def systemStatusBar(cls) -> FakeStatusBar:
            return cls._bar

    NSMenu = FakeMenu


def test_runtime_factory_wires_recalibrate_to_real_preview_session() -> None:
    from gaze.app import create_runtime_controller

    session = RecordingCalibrationSession()
    controller = create_runtime_controller(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
        calibration_session=session,
        sample_source=NullSampleSource(),
        window_provider=EmptyWindowProvider(),
        display_provider=StaticDisplayProvider(),
    )
    runtime = build_menu_bar_app(
        appkit=FakeAppKit(),
        controller=controller,
        development_mode=False,
    )

    runtime.action_dispatcher.recalibrate_()

    assert not isinstance(runtime.controller, FakePrototypeController)
    assert session.starts == 1
    assert runtime.controller.state.readiness.calibration is CalibrationStatus.READY
    assert runtime.controller.state.calibration_display_layout == display_layout()


@dataclass
class LaunchCall:
    args: list[str]
    cwd: str | None
    env: dict[str, str]


class RecordingLauncher:
    def __init__(self) -> None:
        self.calls: list[LaunchCall] = []

    def __call__(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> object:
        self.calls.append(LaunchCall(args=args, cwd=cwd, env=dict(env or {})))
        return object()


def make_pupil_tracker_checkout(path: Path) -> None:
    (path / "src" / "pupil_tracker").mkdir(parents=True)
    (path / "apps" / "desktop_demo").mkdir(parents=True)
    (path / "pyproject.toml").write_text('[project]\nname = "pupil-tracker"\n', encoding="utf-8")


def test_pupil_tracker_calibration_session_launches_desktop_demo_only_on_start(
    tmp_path: Path,
) -> None:
    from gaze.tracking.pupil_tracker_runtime import PupilTrackerDesktopCalibrationSession

    checkout = tmp_path / "pupil-tracker"
    make_pupil_tracker_checkout(checkout)
    bridge_path = tmp_path / "bridge" / "gaze-samples.jsonl"
    launcher = RecordingLauncher()
    session = PupilTrackerDesktopCalibrationSession(
        sibling_path=checkout,
        display_provider=StaticDisplayProvider(),
        bridge_path=bridge_path,
        process_launcher=launcher,
        python_executable="python-test",
    )

    assert launcher.calls == []

    result = session.start()

    assert result.status is CalibrationStatus.CALIBRATING
    assert result.display_layout == display_layout()
    assert result.message == "PupilTracker calibration launched"
    assert len(launcher.calls) == 1
    call = launcher.calls[0]
    assert call.args[:2] == ["python-test", "-c"]
    assert call.cwd == str(checkout)
    assert str(checkout / "src") in call.env["PYTHONPATH"]
    assert str(checkout / "apps") in call.env["PYTHONPATH"]
    assert str(bridge_path) in call.args
