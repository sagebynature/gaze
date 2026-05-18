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
    create_local_app_readme,
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


def test_native_launcher_uses_bundled_model_and_no_local_pupil_tracker_path_by_default() -> None:
    config = AppBundleConfig(app_name="Gaze")

    launcher = create_app_launcher(config)

    assert "#!/bin/zsh" not in launcher
    assert "NSTask" in launcher
    assert "Resources/.venv/bin/python" in launcher
    assert "PUPIL_TRACKER_MEDIAPIPE_MODEL" in launcher
    assert "Resources/models/face_landmarker.task" in launcher
    assert "PUPIL_TRACKER_PATH" not in launcher
    assert "make app-bundle" in launcher
    assert "make app-bundle-pupil-dev" not in launcher
    assert "[[ ! -f \"$PUPIL_TRACKER_MEDIAPIPE_MODEL\" ]]" not in launcher
    assert "-m" in launcher
    assert "gaze" in launcher
    assert "$SOURCE_TREE" not in launcher


def test_default_local_app_readme_avoids_editable_tracker_guidance() -> None:
    readme = create_local_app_readme(AppBundleConfig(app_name="Gaze"))

    assert "make app-bundle" in readme
    assert "PUPIL_TRACKER_PATH" not in readme
    assert "app-bundle-pupil-dev" not in readme
    assert "editable" not in readme.lower()


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


def test_default_bundle_auto_installs_packaged_sibling_calibration_provider(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    project_root = workspace / "gaze"
    sibling = workspace / "pupil-tracker"
    project_root.mkdir(parents=True)
    (sibling / "src" / "pupil_tracker").mkdir(parents=True)
    (sibling / "apps" / "desktop_demo").mkdir(parents=True)
    (sibling / "pyproject.toml").write_text(
        '[project]\nname = "pupil-tracker"\n',
        encoding="utf-8",
    )

    commands = install_commands_for_config(
        AppBundleConfig(),
        project_root=project_root,
        venv_python=Path("/tmp/Gaze.app/Contents/Resources/.venv/bin/python"),
    )

    flat = "\n".join(" ".join(command) for command in commands)
    assert "--editable" not in flat
    assert "PUPIL_TRACKER_PATH" not in flat
    assert commands[-1] == [
        "uv",
        "pip",
        "install",
        "--python",
        "/tmp/Gaze.app/Contents/Resources/.venv/bin/python",
        str(sibling),
    ]


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
    launcher_bytes = launcher.read_bytes()
    assert not launcher_bytes.startswith(b"#!")
    assert os.access(launcher, os.X_OK)


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
    assert not launcher.read_bytes().startswith(b"#!")
    assert "Required permissions" in readme.read_text(encoding="utf-8")
    assert not model.exists()
    assert result.install_commands == ()


def test_makefile_exposes_local_app_bundle_targets() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")

    assert "app-bundle:" in makefile
    assert "app-bundle-pupil-dev:" in makefile
    assert "tools.build_app_bundle" in makefile
