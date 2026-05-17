from __future__ import annotations

from pathlib import Path

from smoke_app_bundle_status_item import (
    StatusItemGeometry,
    find_bundle_processes,
    is_native_bundle_executable,
    status_item_is_visible_in_menu_bar,
)


def test_native_executable_guard_rejects_shell_launcher_and_accepts_mach_o(tmp_path: Path) -> None:
    shell_launcher = tmp_path / "ShellGaze"
    shell_launcher.write_bytes(b"#!/bin/zsh\nexec python -m gaze\n")
    native_launcher = tmp_path / "NativeGaze"
    native_launcher.write_bytes(b"\xcf\xfa\xed\xfe" + b"native bytes")

    assert is_native_bundle_executable(shell_launcher) is False
    assert is_native_bundle_executable(native_launcher) is True


def test_process_tree_parser_finds_native_parent_and_python_child_without_titles() -> None:
    bundle_path = "/Applications/Gaze.app"
    lines = [
        "31765     1 S    /Applications/Gaze.app/Contents/MacOS/Gaze",
        "31817 31765 R    /Applications/Gaze.app/Contents/Resources/.venv/bin/python -m gaze",
        "99999     1 S    /Applications/Other.app/Contents/MacOS/Other",
    ]

    result = find_bundle_processes(bundle_path=bundle_path, ps_lines=lines)

    assert result.parent_pid == 31765
    assert result.child_pid == 31817
    assert repr(result) == "BundleProcessTree(parent_pid=31765, child_pid=31817)"


def test_process_tree_parser_ignores_shell_wrappers_that_mention_bundle_path() -> None:
    bundle_path = "/Applications/Gaze.app"
    lines = [
        "30000 29999 /bin/bash -c grep /Applications/Gaze.app/Contents/MacOS/Gaze",
        "31765     1 /Applications/Gaze.app/Contents/MacOS/Gaze",
        "31817 31765 /Applications/Gaze.app/Contents/Resources/.venv/bin/python -m gaze",
    ]

    result = find_bundle_processes(bundle_path=bundle_path, ps_lines=lines)

    assert result.parent_pid == 31765
    assert result.child_pid == 31817


def test_status_item_visibility_requires_top_menu_bar_geometry() -> None:
    visible = StatusItemGeometry(
        title="Gaze",
        description="status menu",
        x=4373,
        y=3,
        width=53,
        height=24,
    )
    offscreen = StatusItemGeometry(
        title="Gaze",
        description="status menu",
        x=-1,
        y=1428,
        width=53,
        height=24,
    )

    assert status_item_is_visible_in_menu_bar(visible) is True
    assert status_item_is_visible_in_menu_bar(offscreen) is False


def test_makefile_exposes_local_app_status_item_smoke() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "smoke-app-status-item" in makefile
    assert "tools.smoke_app_bundle_status_item" in makefile
    assert "make smoke-app-status-item" in readme
