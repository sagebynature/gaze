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
