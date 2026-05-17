from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FACE_LANDMARKER_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)


@dataclass(frozen=True)
class AppBundleConfig:
    """Configuration for a local unsigned macOS Gaze app bundle."""

    app_name: str = "Gaze"
    bundle_identifier: str = "com.sagebynature.gaze.local"
    output_dir: Path = Path("dist")
    python_executable: str = sys.executable
    pupil_tracker_path: Path | None = None
    face_landmarker_model_path: Path | None = None
    face_landmarker_model_url: str = FACE_LANDMARKER_MODEL_URL
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
    """Create the native launcher source embedded in Contents/MacOS."""

    app_name = _objc_string_literal(config.app_name)
    return f"""#import <Foundation/Foundation.h>

// Embedded Python path: Contents/Resources/.venv/bin/python
// Bundled default model path: Contents/Resources/models/face_landmarker.task

int main(int argc, const char * argv[]) {{
    @autoreleasepool {{
        NSBundle *bundle = [NSBundle mainBundle];
        NSString *resourcesPath = [bundle resourcePath];
        NSString *venvPython = [resourcesPath stringByAppendingPathComponent:@".venv/bin/python"];
        NSString *defaultModel = [resourcesPath
            stringByAppendingPathComponent:@"models/face_landmarker.task"];

        if (![[NSFileManager defaultManager] isExecutableFileAtPath:venvPython]) {{
            NSLog(@"{app_name} local app bundle is missing its embedded Python environment.");
            NSLog(@"Rebuild it from the repo with: make app-bundle");
            return 70;
        }}

        NSMutableDictionary *environment = [[[NSProcessInfo processInfo] environment] mutableCopy];
        NSString *modelOverride = environment[@"PUPIL_TRACKER_MEDIAPIPE_MODEL"];
        if (modelOverride == nil || [modelOverride length] == 0) {{
            environment[@"PUPIL_TRACKER_MEDIAPIPE_MODEL"] = defaultModel;
        }}

        NSTask *task = [[NSTask alloc] init];
        task.executableURL = [NSURL fileURLWithPath:venvPython];
        task.arguments = @[@"-m", @"gaze"];
        task.environment = environment;

        NSError *error = nil;
        if (![task launchAndReturnError:&error]) {{
            NSLog(@"{app_name} failed to launch embedded Python runtime: %@", error);
            return 70;
        }}

        [task waitUntilExit];
        return [task terminationStatus];
    }}
}}
"""


def _objc_string_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


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
- The default MediaPipe FaceLandmarker model is bundled under Contents/Resources/models.
- The default app bundle uses the PyPI/release `pupil-tracker` dependency declared by Gaze.
- Editable PupilTracker mode is available only through the explicit app-bundle-pupil-dev target.

Recommended rebuild command
---------------------------
make app-bundle

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
    launcher_source_path = macos_dir / f"{config.app_name}.m"
    launcher_source_path.write_text(create_app_launcher(config), encoding="utf-8")
    _compile_native_launcher(
        source_path=launcher_source_path,
        output_path=launcher_path,
        project_root=project_root,
    )
    launcher_source_path.unlink()
    (resources_dir / "README-local-app.txt").write_text(
        create_local_app_readme(config),
        encoding="utf-8",
    )
    model_path = resources_dir / "models" / "face_landmarker.task"
    if config.face_landmarker_model_path is not None:
        _copy_face_landmarker_model(config.face_landmarker_model_path, model_path)

    if config.skip_install:
        return AppBundleBuildResult(app_path=app_path, install_commands=())

    if config.face_landmarker_model_path is None:
        _download_face_landmarker_model(
            model_path,
            url=config.face_landmarker_model_url,
            project_root=project_root,
        )

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
    parser.add_argument("--face-landmarker-model-path", type=Path)
    parser.add_argument("--face-landmarker-model-url", default=FACE_LANDMARKER_MODEL_URL)
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args(argv)
    return AppBundleConfig(
        app_name=args.app_name,
        bundle_identifier=args.bundle_identifier,
        output_dir=args.output_dir,
        pupil_tracker_path=args.pupil_tracker_path,
        face_landmarker_model_path=args.face_landmarker_model_path,
        face_landmarker_model_url=args.face_landmarker_model_url,
        skip_install=args.skip_install,
    )


def _copy_face_landmarker_model(source: Path, destination: Path) -> None:
    if not source.is_file():
        msg = f"FaceLandmarker model not found: {source}"
        raise FileNotFoundError(msg)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _compile_native_launcher(
    *,
    source_path: Path,
    output_path: Path,
    project_root: Path,
) -> None:
    subprocess.run(
        [
            "clang",
            "-fobjc-arc",
            "-framework",
            "Foundation",
            str(source_path),
            "-o",
            str(output_path),
        ],
        cwd=project_root,
        check=True,
    )


def _download_face_landmarker_model(
    destination: Path,
    *,
    url: str,
    project_root: Path,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_destination = destination.with_suffix(destination.suffix + ".tmp")
    subprocess.run(
        ["curl", "-L", "--fail", "--output", str(temporary_destination), url],
        cwd=project_root,
        check=True,
    )
    temporary_destination.replace(destination)


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(list(sys.argv[1:] if argv is None else argv))
    result = build_app_bundle(config, project_root=Path.cwd())
    print(f"Built {result.app_path}")
    if config.skip_install:
        print("Skipped embedded environment install")
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
