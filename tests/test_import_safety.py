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
