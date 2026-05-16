"""Tests for privacy-preserving real visible-window enumeration."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


def _record(
    *,
    owner: str = "Terminal",
    pid: int = 123,
    x: float = 10,
    y: float = 20,
    width: float = 800,
    height: float = 600,
    layer: int = 0,
    onscreen: bool = True,
    alpha: float = 1.0,
    title: str | None = "never expose this window title",
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "kCGWindowOwnerName": owner,
        "kCGWindowOwnerPID": pid,
        "kCGWindowBounds": {
            "X": x,
            "Y": y,
            "Width": width,
            "Height": height,
        },
        "kCGWindowLayer": layer,
        "kCGWindowIsOnscreen": onscreen,
        "kCGWindowAlpha": alpha,
    }
    if title is not None:
        record["kCGWindowName"] = title
    return record


def test_visible_window_provider_import_does_not_load_quartz_or_appkit(monkeypatch) -> None:
    sys.modules.pop("gaze.desktop.visible_windows", None)
    sys.modules.pop("Quartz", None)
    sys.modules.pop("AppKit", None)

    importlib.import_module("gaze.desktop.visible_windows")

    assert "Quartz" not in sys.modules
    assert "AppKit" not in sys.modules


def test_provider_returns_visible_candidate_bounds_and_activation_identity() -> None:
    from gaze.desktop.visible_windows import CoreGraphicsVisibleWindowProvider

    provider = CoreGraphicsVisibleWindowProvider(
        window_records=lambda: (
            _record(
                owner="Code",
                pid=456,
                x=100,
                y=200,
                width=1200,
                height=900,
                title="private repo issue title",
            ),
        )
    )

    candidates = provider.current_candidates()

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.app_name == "Code"
    assert candidate.owner_process_id == 456
    assert candidate.bounds_x == 100
    assert candidate.bounds_y == 200
    assert candidate.bounds_width == 1200
    assert candidate.bounds_height == 900
    assert not hasattr(candidate, "window_title")
    assert "private repo issue title" not in repr(candidate)


def test_provider_filters_non_targetable_window_records() -> None:
    from gaze.desktop.visible_windows import CoreGraphicsVisibleWindowProvider

    records: tuple[Mapping[str, object], ...] = (
        _record(owner="Terminal", pid=1),
        _record(owner="Hidden", pid=2, onscreen=False),
        _record(owner="Transparent", pid=3, alpha=0.0),
        _record(owner="Floating", pid=4, layer=3),
        _record(owner="ZeroWidth", pid=5, width=0),
        _record(owner="ZeroHeight", pid=6, height=0),
        _record(owner="Dock", pid=7),
        _record(owner="SystemUIServer", pid=8),
        _record(owner="Control Center", pid=9),
        _record(owner="Offscreen", pid=10, x=5000, y=5000),
    )
    provider = CoreGraphicsVisibleWindowProvider(
        window_records=lambda: records,
        visible_regions=((0, 0, 1920, 1080),),
    )

    assert [candidate.app_name for candidate in provider.current_candidates()] == ["Terminal"]


def test_provider_preserves_top_to_bottom_window_order() -> None:
    from gaze.desktop.visible_windows import CoreGraphicsVisibleWindowProvider

    records: Iterable[Mapping[str, object]] = (
        _record(owner="Top App", pid=11, x=20, y=20),
        _record(owner="Bottom App", pid=12, x=40, y=40),
    )
    provider = CoreGraphicsVisibleWindowProvider(window_records=lambda: records)

    assert [candidate.app_name for candidate in provider.current_candidates()] == [
        "Top App",
        "Bottom App",
    ]


def test_default_provider_imports_quartz_only_when_enumerating(monkeypatch) -> None:
    sys.modules.pop("gaze.desktop.visible_windows", None)
    sys.modules.pop("Quartz", None)
    module = importlib.import_module("gaze.desktop.visible_windows")

    class FakeQuartz:
        kCGWindowListOptionOnScreenOnly = 1
        kCGWindowListExcludeDesktopElements = 2
        kCGNullWindowID = 0

        @staticmethod
        def CGWindowListCopyWindowInfo(_options: int, _window_id: int):
            return [_record(owner="Safari", pid=321)]

    real_import = __import__

    def fake_import(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] | None = (),
        level: int = 0,
    ) -> Any:
        if name == "Quartz":
            return FakeQuartz
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)
    provider = module.CoreGraphicsVisibleWindowProvider()

    assert "Quartz" not in sys.modules
    assert [candidate.app_name for candidate in provider.current_candidates()] == ["Safari"]
