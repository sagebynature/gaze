from gaze.dev.fakes import FakeFrontmostApp, FakeTarget, FakeTargetController


def test_manual_fake_target_selection_returns_target_summary() -> None:
    controller = FakeTargetController()

    controller.set_manual_target(
        FakeTarget(app_name="Terminal", x=10, y=20, width=800, height=600, confidence=0.88)
    )

    target = controller.current_target()
    assert target is not None
    assert target.app_name == "Terminal"
    assert target.confidence == 0.88


def test_fake_controller_can_report_no_target() -> None:
    controller = FakeTargetController()
    controller.set_manual_target(
        FakeTarget(app_name="Safari", x=0, y=0, width=500, height=400, confidence=0.9)
    )

    controller.clear_target()

    assert controller.current_target() is None


def test_scripted_fake_sequence_advances_deterministically() -> None:
    controller = FakeTargetController.scripted_demo()

    target = controller.current_target()
    assert target is not None
    assert target.app_name == "Safari"
    controller.advance_script()
    target = controller.current_target()
    assert target is not None
    assert target.app_name == "Terminal"
    controller.advance_script()
    assert controller.current_target() is None
    controller.advance_script()
    assert controller.current_target() is None


def test_fake_frontmost_app_is_simple_state() -> None:
    frontmost = FakeFrontmostApp()

    frontmost.set_frontmost("Terminal")

    assert frontmost.is_frontmost("Terminal") is True
    assert frontmost.is_frontmost("Safari") is False
