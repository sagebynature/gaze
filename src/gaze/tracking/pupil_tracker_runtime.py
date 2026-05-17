"""Runtime PupilTracker bridge for real calibration and scalar gaze samples.

This module is import safe. It does not import PySide6, PupilTracker, open a
camera, or start a subprocess until an explicit calibration start.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Protocol

from gaze.core.display_geometry import DisplayLayoutSnapshot
from gaze.core.state import CalibrationStatus
from gaze.tracking.calibration import CalibrationResult
from gaze.tracking.gaze_pipeline import PupilTrackerGazeSample
from gaze.tracking.pupil_tracker_adapter import (
    editable_sibling_source_path,
    missing_pupil_tracker_guidance,
)

_BRIDGE_SCRIPT = r'''
from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QTimer

from desktop_demo.app import create_app, create_main_window

bridge_path = Path(sys.argv[1])
bridge_path.parent.mkdir(parents=True, exist_ok=True)

app = create_app(sys.argv)
window = create_main_window()


def bridge_gaze_samples(event_type, payload):
    if event_type != "gaze_sample":
        return
    safe_payload = {
        "timestamp": payload.get("timestamp"),
        "x": payload.get("x"),
        "y": payload.get("y"),
        "confidence": payload.get("confidence"),
        "valid": payload.get("valid"),
    }
    with bridge_path.open("a", encoding="utf-8") as bridge_file:
        bridge_file.write(
            json.dumps(
                {"event_type": event_type, "payload": safe_payload},
                sort_keys=True,
            )
        )
        bridge_file.write("\n")


def start_calibration():
    window.start_camera()
    window.start_calibration()


window.log_telemetry_event = bridge_gaze_samples
window.show()
QTimer.singleShot(0, start_calibration)
raise SystemExit(app.exec())
'''


class DisplayLayoutProvider(Protocol):
    def current_layout(self) -> DisplayLayoutSnapshot:
        """Return the active privacy-safe display layout."""
        ...


class ProcessLauncher(Protocol):
    def __call__(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> object:
        """Launch a subprocess and return its handle."""
        ...


@dataclass(frozen=True)
class PupilTrackerTelemetrySample(PupilTrackerGazeSample):
    """Scalar-only gaze sample bridged from PupilTracker telemetry."""

    timestamp: float
    x: float
    y: float
    confidence: float
    valid: bool


class PupilTrackerTelemetrySampleSource:
    """Tail a scalar-only bridge file for the newest PupilTracker gaze sample."""

    def __init__(self, bridge_path: Path) -> None:
        self._bridge_path = bridge_path
        self._offset = 0

    def current_sample(self) -> PupilTrackerTelemetrySample | None:
        if not self._bridge_path.is_file():
            return None
        latest: PupilTrackerTelemetrySample | None = None
        with self._bridge_path.open(encoding="utf-8") as bridge_file:
            bridge_file.seek(self._offset)
            for line in bridge_file:
                latest = _sample_from_bridge_line(line) or latest
            self._offset = bridge_file.tell()
        return latest


class PupilTrackerDesktopCalibrationSession:
    """Launch PupilTracker's desktop calibration flow just in time."""

    def __init__(
        self,
        *,
        display_provider: DisplayLayoutProvider,
        sibling_path: Path | None = None,
        bridge_path: Path | None = None,
        process_launcher: ProcessLauncher | None = None,
        python_executable: str | None = None,
    ) -> None:
        self._display_provider = display_provider
        self._sibling_path = sibling_path
        self._bridge_path = bridge_path or default_bridge_path()
        self._process_launcher = process_launcher or _launch_process
        self._python_executable = python_executable or sys.executable
        self._process: object | None = None

    @property
    def bridge_path(self) -> Path:
        return self._bridge_path

    def ignored_owner_process_ids(self) -> frozenset[int]:
        """Return launched PupilTracker demo PIDs that must not be gaze targets."""

        pid = getattr(self._process, "pid", None)
        if not isinstance(pid, int):
            return frozenset()
        return frozenset({pid})

    def start(self) -> CalibrationResult:
        display_layout = self._display_provider.current_layout()
        project_root = self._resolve_project_root()
        if project_root is None:
            guidance = missing_pupil_tracker_guidance(_default_sibling_path())
            return CalibrationResult.unavailable(guidance)

        self._bridge_path.parent.mkdir(parents=True, exist_ok=True)
        self._bridge_path.unlink(missing_ok=True)
        env = _bridge_environment(project_root, os.environ)
        self._process = self._process_launcher(
            [self._python_executable, "-c", _BRIDGE_SCRIPT, str(self._bridge_path)],
            cwd=str(project_root),
            env=env,
        )
        return CalibrationResult(
            status=CalibrationStatus.CALIBRATING,
            message="PupilTracker calibration launched",
            camera_available=True,
            tracker_available=True,
            display_layout=display_layout,
        )

    def _resolve_project_root(self) -> Path | None:
        for candidate in _candidate_project_roots(self._sibling_path):
            if _desktop_demo_available(candidate):
                return candidate
        return None


def default_bridge_path() -> Path:
    return (
        Path.home()
        / "Library"
        / "Application Support"
        / "Gaze"
        / "pupil-tracker-gaze-samples.jsonl"
    )


def _launch_process(
    args: list[str],
    *,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(args, cwd=cwd, env=env)


def _candidate_project_roots(configured_sibling: Path | None) -> tuple[Path, ...]:
    candidates: list[Path] = []
    if configured_sibling is not None:
        candidates.append(configured_sibling)
    env_path = os.environ.get("PUPIL_TRACKER_PATH")
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(_default_sibling_path())
    installed_root = _installed_editable_project_root()
    if installed_root is not None:
        candidates.append(installed_root)

    deduplicated: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved not in seen:
            seen.add(resolved)
            deduplicated.append(resolved)
    return tuple(deduplicated)


def _default_sibling_path() -> Path:
    return Path.cwd() / ".." / "pupil-tracker"


def _installed_editable_project_root() -> Path | None:
    spec = find_spec("pupil_tracker")
    if spec is None or spec.origin is None:
        return None
    package_init = Path(spec.origin)
    package_dir = package_init.parent
    source_dir = package_dir.parent
    project_root = source_dir.parent
    if source_dir.name != "src":
        return None
    return project_root


def _desktop_demo_available(project_root: Path) -> bool:
    source_path = editable_sibling_source_path(project_root)
    apps_path = project_root / "apps"
    desktop_demo_path = apps_path / "desktop_demo"
    return source_path is not None and desktop_demo_path.is_dir()


def _bridge_environment(project_root: Path, base_environment: Mapping[str, str]) -> dict[str, str]:
    env = dict(base_environment)
    import_paths = [str(project_root / "src"), str(project_root / "apps")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        import_paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(import_paths)
    return env


def _sample_from_bridge_line(line: str) -> PupilTrackerTelemetrySample | None:
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(event, Mapping) or event.get("event_type") != "gaze_sample":
        return None
    payload = event.get("payload")
    if not isinstance(payload, Mapping):
        return None
    timestamp = _float_value(payload.get("timestamp"))
    x = _float_value(payload.get("x"))
    y = _float_value(payload.get("y"))
    confidence = _float_value(payload.get("confidence"))
    valid = payload.get("valid")
    if (
        timestamp is None
        or x is None
        or y is None
        or confidence is None
        or not isinstance(valid, bool)
    ):
        return None
    return PupilTrackerTelemetrySample(
        timestamp=timestamp,
        x=x,
        y=y,
        confidence=confidence,
        valid=valid,
    )


def _float_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
