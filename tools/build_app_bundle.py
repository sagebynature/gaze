from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppBundleConfig:
    """Configuration for a local unsigned macOS Gaze app bundle."""

    app_name: str = "Gaze"
    bundle_identifier: str = "com.sagebynature.gaze.local"
    output_dir: Path = Path("dist")
    python_executable: str = sys.executable
    pupil_tracker_path: Path | None = None
    skip_install: bool = False


@dataclass(frozen=True)
class AppBundleBuildResult:
    """Result of creating the local app bundle skeleton and optional venv install."""

    app_path: Path
    install_commands: tuple[tuple[str, ...], ...]


def create_info_plist(config: AppBundleConfig) -> dict[str, object]:
    """Return the Info.plist payload for the local unsigned app bundle."""

    return {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleExecutable": config.app_name,
        "CFBundleIdentifier": config.bundle_identifier,
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": config.app_name,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.1.0-local",
        "CFBundleVersion": "0.1.0-local",
        "LSMinimumSystemVersion": "13.0",
        "LSUIElement": True,
        "NSCameraUsageDescription": (
            "Gaze uses the camera only when you explicitly start calibration."
        ),
        "GazeDistributionScope": "local-unsigned",
    }


def create_app_launcher(config: AppBundleConfig) -> str:
    """Create the shell launcher embedded in Contents/MacOS."""

    default_model_path = (
        "$HOME/Library/Application Support/Gaze/models/face_landmarker.task"
    )
    return f"""#!/bin/zsh
set -euo pipefail

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="$APP_ROOT/Resources/.venv/bin/python"
DEFAULT_MODEL="{default_model_path}"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Gaze local app bundle is missing its embedded Python environment." >&2
  echo "Rebuild it from the repo with: make app-bundle-pupil-dev" >&2
  exit 70
fi

if [[ -z "${{PUPIL_TRACKER_MEDIAPIPE_MODEL:-}}" ]]; then
  export PUPIL_TRACKER_MEDIAPIPE_MODEL="$DEFAULT_MODEL"
fi

# The launcher intentionally does not verify the model file at app start.
# Missing-model guidance belongs at explicit calibration time so opening the app
# does not request camera/model prerequisites before the user asks to calibrate.

if [[ -z "${{PUPIL_TRACKER_PATH:-}}" ]]; then
  export PUPIL_TRACKER_PATH="$HOME/workspace/sagebynature/pupil-tracker"
fi

exec "$VENV_PYTHON" -m gaze
"""


def create_local_app_readme(config: AppBundleConfig) -> str:
    """Create operator-facing local bundle guidance without storing private content."""

    return f"""Gaze local app bundle
=====================

This is a local unsigned development bundle for {config.app_name}. It is not signed or notarized.

Required permissions
--------------------
- Camera: requested only when calibration explicitly starts.
- Accessibility/Input Monitoring: not required for the current MVP path.

Required runtime inputs
-----------------------
- PUPIL_TRACKER_MEDIAPIPE_MODEL must point at face_landmarker.task.
- PUPIL_TRACKER_PATH should point at the local pupil-tracker checkout when using editable dev mode.

Recommended rebuild command
---------------------------
make app-bundle-pupil-dev

Privacy posture
---------------
The bundle launcher stores no screenshots, frames, window titles, document names,
URLs, or raw desktop content.
"""


def install_commands_for_config(
    config: AppBundleConfig,
    *,
    project_root: Path,
    venv_python: Path,
) -> tuple[list[str], ...]:
    """Return install commands needed for a local bundle environment."""

    venv_dir = venv_python.parent.parent
    commands: list[list[str]] = [
        ["uv", "venv", "--python", config.python_executable, str(venv_dir)],
        ["uv", "pip", "install", "--python", str(venv_python), str(project_root)],
    ]
    if config.pupil_tracker_path is not None:
        commands.append(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(venv_python),
                "--editable",
                str(config.pupil_tracker_path),
            ]
        )
    return tuple(commands)


def build_app_bundle(
    config: AppBundleConfig,
    *,
    project_root: Path,
) -> AppBundleBuildResult:
    """Build a local unsigned `.app` bundle for development validation."""

    app_path = config.output_dir / f"{config.app_name}.app"
    contents_dir = app_path / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    venv_python = resources_dir / ".venv" / "bin" / "python"

    if app_path.exists():
        shutil.rmtree(app_path)
    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    (contents_dir / "Info.plist").write_bytes(plistlib.dumps(create_info_plist(config)))
    launcher_path = macos_dir / config.app_name
    launcher_path.write_text(create_app_launcher(config), encoding="utf-8")
    launcher_path.chmod(launcher_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    (resources_dir / "README-local-app.txt").write_text(
        create_local_app_readme(config),
        encoding="utf-8",
    )

    if config.skip_install:
        return AppBundleBuildResult(app_path=app_path, install_commands=())

    commands = install_commands_for_config(
        config,
        project_root=project_root,
        venv_python=venv_python,
    )
    for command in commands:
        subprocess.run(command, cwd=project_root, check=True)
    return AppBundleBuildResult(
        app_path=app_path,
        install_commands=tuple(tuple(command) for command in commands),
    )


def _parse_args(argv: list[str]) -> AppBundleConfig:
    parser = argparse.ArgumentParser(description="Build a local unsigned Gaze.app bundle.")
    parser.add_argument("--app-name", default="Gaze")
    parser.add_argument("--bundle-identifier", default="com.sagebynature.gaze.local")
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    parser.add_argument("--pupil-tracker-path", type=Path)
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args(argv)
    return AppBundleConfig(
        app_name=args.app_name,
        bundle_identifier=args.bundle_identifier,
        output_dir=args.output_dir,
        pupil_tracker_path=args.pupil_tracker_path,
        skip_install=args.skip_install,
    )


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(list(sys.argv[1:] if argv is None else argv))
    result = build_app_bundle(config, project_root=Path.cwd())
    print(f"Built {result.app_path}")
    if config.skip_install:
        print("Skipped embedded environment install")
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
