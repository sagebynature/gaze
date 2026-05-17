from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path

from build_app_bundle import (
    AppBundleConfig,
    build_app_bundle,
    create_app_launcher,
    create_info_plist,
    install_commands_for_config,
)


def test_info_plist_contains_menu_bar_identity_permissions_and_signing_scope() -> None:
    config = AppBundleConfig(app_name="Gaze", bundle_identifier="com.sagebynature.gaze.local")

    plist = create_info_plist(config)

    assert plist["CFBundleName"] == "Gaze"
    assert plist["CFBundleExecutable"] == "Gaze"
    assert plist["CFBundleIdentifier"] == "com.sagebynature.gaze.local"
    assert plist["LSUIElement"] is True
    camera_usage = plist["NSCameraUsageDescription"]
    assert isinstance(camera_usage, str)
    assert "camera" in camera_usage.lower()
    assert plist["GazeDistributionScope"] == "local-unsigned"


def test_launcher_uses_bundled_model_and_no_local_pupil_tracker_path_by_default() -> None:
    config = AppBundleConfig(app_name="Gaze")

    launcher = create_app_launcher(config)

    assert "Resources/.venv/bin/python" in launcher
    assert "PUPIL_TRACKER_MEDIAPIPE_MODEL" in launcher
    assert 'DEFAULT_MODEL="$APP_ROOT/Resources/models/face_landmarker.task"' in launcher
    assert "PUPIL_TRACKER_PATH" not in launcher
    assert "make app-bundle" in launcher
    assert "make app-bundle-pupil-dev" not in launcher
    assert "[[ ! -f \"$PUPIL_TRACKER_MEDIAPIPE_MODEL\" ]]" not in launcher
    assert "exec \"$VENV_PYTHON\" -m gaze" in launcher
    assert "$SOURCE_TREE" not in launcher


def test_install_commands_include_project_and_optional_editable_pupil_tracker() -> None:
    project_root = Path("/tmp/gaze-project")
    pupil_tracker = Path("/tmp/pupil-tracker")
    config = AppBundleConfig(pupil_tracker_path=pupil_tracker)

    commands = install_commands_for_config(
        config,
        project_root=project_root,
        venv_python=Path("/tmp/Gaze.app/Contents/Resources/.venv/bin/python"),
    )

    assert commands[0] == [
        "uv",
        "venv",
        "--python",
        sys.executable,
        "/tmp/Gaze.app/Contents/Resources/.venv",
    ]
    assert commands[1] == [
        "uv",
        "pip",
        "install",
        "--python",
        "/tmp/Gaze.app/Contents/Resources/.venv/bin/python",
        str(project_root),
    ]
    assert commands[2] == [
        "uv",
        "pip",
        "install",
        "--python",
        "/tmp/Gaze.app/Contents/Resources/.venv/bin/python",
        "--editable",
        str(pupil_tracker),
    ]


def test_default_bundle_uses_release_dependency_not_editable_pupil_tracker() -> None:
    commands = install_commands_for_config(
        AppBundleConfig(),
        project_root=Path("/tmp/gaze-project"),
        venv_python=Path("/tmp/Gaze.app/Contents/Resources/.venv/bin/python"),
    )

    flat = "\n".join(" ".join(command) for command in commands)
    assert "--editable" not in flat
    assert "PUPIL_TRACKER_PATH" not in flat
    assert commands == (
        [
            "uv",
            "venv",
            "--python",
            sys.executable,
            "/tmp/Gaze.app/Contents/Resources/.venv",
        ],
        [
            "uv",
            "pip",
            "install",
            "--python",
            "/tmp/Gaze.app/Contents/Resources/.venv/bin/python",
            "/tmp/gaze-project",
        ],
    )


def test_build_app_bundle_copies_face_landmarker_into_resources(tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    project_root.mkdir()
    output_dir = tmp_path / "dist"
    source_model = tmp_path / "face_landmarker.task"
    source_model.write_bytes(b"fake mediapipe model")
    config = AppBundleConfig(
        app_name="Gaze",
        output_dir=output_dir,
        face_landmarker_model_path=source_model,
        skip_install=True,
    )

    result = build_app_bundle(config, project_root=project_root)

    bundled_model = (
        result.app_path / "Contents" / "Resources" / "models" / "face_landmarker.task"
    )
    assert bundled_model.read_bytes() == b"fake mediapipe model"
    launcher = result.app_path / "Contents" / "MacOS" / "Gaze"
    assert 'DEFAULT_MODEL="$APP_ROOT/Resources/models/face_landmarker.task"' in launcher.read_text(
        encoding="utf-8"
    )


def test_build_app_bundle_writes_plist_launcher_and_docs_in_dry_run(tmp_path: Path) -> None:
    project_root = tmp_path / "repo"
    project_root.mkdir()
    output_dir = tmp_path / "dist"
    config = AppBundleConfig(app_name="Gaze", output_dir=output_dir, skip_install=True)

    result = build_app_bundle(config, project_root=project_root)

    assert result.app_path == output_dir / "Gaze.app"
    info_plist = result.app_path / "Contents" / "Info.plist"
    launcher = result.app_path / "Contents" / "MacOS" / "Gaze"
    readme = result.app_path / "Contents" / "Resources" / "README-local-app.txt"
    model = result.app_path / "Contents" / "Resources" / "models" / "face_landmarker.task"
    assert info_plist.is_file()
    assert plistlib.loads(info_plist.read_bytes())["CFBundleName"] == "Gaze"
    assert launcher.is_file()
    assert os.access(launcher, os.X_OK)
    assert "PUPIL_TRACKER_MEDIAPIPE_MODEL" in launcher.read_text(encoding="utf-8")
    assert "Required permissions" in readme.read_text(encoding="utf-8")
    assert not model.exists()
    assert result.install_commands == ()


def test_makefile_exposes_local_app_bundle_targets() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "app-bundle:" in makefile
    assert "app-bundle-pupil-dev:" in makefile
    assert "tools.build_app_bundle" in makefile
