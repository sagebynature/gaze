from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import FakeActivationService
from gaze.dev.fakes import FakeTarget
from gaze.overlays.border import RecordingBorderOverlay
from gaze.ui.appkit_shell import build_menu_bar_app
from gaze.ui.developer_panel import developer_controls


class FakeStatusItem:
    def __init__(self) -> None:
        self.menu = None

    def button(self):
        return self

    def setTitle_(self, title: str) -> None:
        self.title = title

    def setMenu_(self, menu) -> None:
        self.menu = menu


class FakeStatusBar:
    def __init__(self) -> None:
        self.item = FakeStatusItem()

    def statusItemWithLength_(self, length: float) -> FakeStatusItem:
        self.length = length
        return self.item


class FakeApplication:
    def __init__(self) -> None:
        self.policy = None
        self.activated_ignoring_other_apps = None

    def setActivationPolicy_(self, policy: int) -> None:
        self.policy = policy

    def activateIgnoringOtherApps_(self, value: bool) -> None:
        self.activated_ignoring_other_apps = value

    def terminate_(self, sender) -> None:
        self.terminated_by = sender


class FakeWindow:
    __slots__ = (
        "action_names",
        "backing",
        "content_rect",
        "content_text",
        "defer",
        "shown",
        "style_mask",
        "title",
    )

    def __init__(self) -> None:
        self.title = ""
        self.content_text = ""
        self.action_names: list[str] = []
        self.shown = False
        self.content_rect = None
        self.style_mask = None
        self.backing = None
        self.defer = None

    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self

    def initWithContentRect_styleMask_backing_defer_(self, rect, style_mask, backing, defer):
        self.content_rect = rect
        self.style_mask = style_mask
        self.backing = backing
        self.defer = defer
        return self

    def setTitle_(self, title: str) -> None:
        self.title = title

    def setContentView_(self, view) -> None:
        self.content_text = getattr(view, "string", "")
        self.action_names = getattr(view, "action_names", [])

    def makeKeyAndOrderFront_(self, sender) -> None:
        self.shown = True


class FakeTextView:
    def __init__(self) -> None:
        self.string = ""
        self.editable = True
        self.selectable = False
        self.action_names: list[str] = []

    @classmethod
    def alloc(cls):
        return cls()

    def init(self):
        return self

    def setString_(self, value: str) -> None:
        self.string = value

    def setEditable_(self, value: bool) -> None:
        self.editable = value

    def setSelectable_(self, value: bool) -> None:
        self.selectable = value

    def setActionNames_(self, names: list[str]) -> None:
        self.action_names = names


class FakeMenu:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.raw_items = []

    def addItem_(self, item) -> None:
        self.items.append(item.title)
        self.raw_items.append(item)

    def removeAllItems(self) -> None:
        self.items = []
        self.raw_items = []


class FakeMenuItem:
    def __init__(self) -> None:
        self.title = ""
        self.action = None
        self.key = ""
        self.modifier_mask = None
        self.target = None

    @classmethod
    def alloc(cls):
        return cls()

    def initWithTitle_action_keyEquivalent_(self, title: str, action, key: str):
        self.title = title
        self.action = action
        self.key = key
        return self

    def setTarget_(self, target) -> None:
        self.target = target

    def setAction_(self, action) -> None:
        self.action = action

    def setKeyEquivalentModifierMask_(self, mask: int) -> None:
        self.modifier_mask = mask


class FakeAppKit:
    NSApplicationActivationPolicyAccessory = 1
    NSVariableStatusItemLength = -1.0
    NSSquareStatusItemLength = -2.0
    NSEventModifierFlagCommand = 1
    NSEventModifierFlagOption = 2
    NSWindowStyleMaskTitled = 4
    NSWindowStyleMaskClosable = 8
    NSBackingStoreBuffered = 2
    NSMenuItem = FakeMenuItem
    NSWindow = FakeWindow
    NSTextView = FakeTextView

    @staticmethod
    def NSMakeRect(x, y, width, height):
        return (x, y, width, height)

    class NSApplication:
        _app = FakeApplication()

        @classmethod
        def sharedApplication(cls):
            return cls._app

    class NSStatusBar:
        _bar = FakeStatusBar()

        @classmethod
        def systemStatusBar(cls):
            return cls._bar

    NSMenu = FakeMenu


def test_build_menu_bar_app_creates_status_item_and_menu() -> None:
    appkit = FakeAppKit()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )

    runtime = build_menu_bar_app(appkit=appkit, controller=controller, development_mode=True)

    assert runtime.app.policy == appkit.NSApplicationActivationPolicyAccessory
    assert appkit.NSStatusBar._bar.length == appkit.NSVariableStatusItemLength
    assert runtime.status_item.title == "Gaze"
    assert runtime.status_item.menu is not None
    assert "Status: off" in runtime.status_item.menu.items
    assert "Settings" in runtime.status_item.menu.items
    assert "Open Developer Panel" in runtime.status_item.menu.items
    action_items = {
        item.title: item
        for item in runtime.status_item.menu.raw_items
        if item.action is not None
    }
    assert "Activate Target" in action_items
    assert "Settings" in action_items
    assert "Open Developer Panel" in action_items
    assert "Enable Gaze" in action_items
    assert "Toggle Border" in action_items
    assert "Toggle Heatmap" not in action_items
    assert "Recalibrate" in action_items
    assert "Quit" in action_items


def test_build_menu_bar_app_shows_launch_setup_window_by_default() -> None:
    appkit = FakeAppKit()
    appkit.NSApplication._app = FakeApplication()
    appkit.NSStatusBar._bar = FakeStatusBar()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )

    runtime = build_menu_bar_app(appkit=appkit, controller=controller, development_mode=False)

    assert runtime.launch_window is not None
    assert runtime.launch_window.shown is True
    assert runtime.launch_window.title == "Gaze Setup"
    assert runtime.launch_window.content_rect == (0, 0, 460, 360)
    assert "Gaze Calibration" in runtime.launch_window.content_text
    assert "Privacy" in runtime.launch_window.content_text
    assert "Readiness" in runtime.launch_window.content_text
    assert "Calibration Targets" in runtime.launch_window.content_text
    assert "Result" in runtime.launch_window.content_text
    assert "camera access starts only when you ask" in runtime.launch_window.content_text.lower()
    assert "recalibrate" in runtime.launch_window.action_names
    assert appkit.NSApplication._app.activated_ignoring_other_apps is True
    assert controller.state.flags.gaze_enabled is False


def test_recalibrate_menu_opens_gaze_owned_wizard_before_refresh() -> None:
    appkit = FakeAppKit()
    appkit.NSApplication._app = FakeApplication()
    appkit.NSStatusBar._bar = FakeStatusBar()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    runtime = build_menu_bar_app(
        appkit=appkit,
        controller=controller,
        development_mode=False,
        show_launch_window=False,
    )

    runtime.action_dispatcher.recalibrate_()

    assert runtime.action_dispatcher.calibration_window is not None
    assert runtime.action_dispatcher.calibration_window.title == "Gaze Calibration"
    assert "Gaze Calibration" in runtime.action_dispatcher.calibration_window.content_text
    assert "No recording" in runtime.action_dispatcher.calibration_window.content_text


def test_build_menu_bar_app_can_skip_launch_setup_window_for_headless_tests() -> None:
    appkit = FakeAppKit()
    appkit.NSApplication._app = FakeApplication()
    appkit.NSStatusBar._bar = FakeStatusBar()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )

    runtime = build_menu_bar_app(
        appkit=appkit,
        controller=controller,
        development_mode=False,
        show_launch_window=False,
    )

    assert runtime.launch_window is None
    assert appkit.NSApplication._app.activated_ignoring_other_apps is None


def test_every_menu_model_action_has_runtime_selector() -> None:
    from gaze.core.state import GazeAppState
    from gaze.ui.appkit_shell import selector_for_menu_action
    from gaze.ui.menu_model import menu_items_for_state

    actions = [item.action for item in menu_items_for_state(GazeAppState.default()) if item.action]

    assert actions
    assert all(selector_for_menu_action(action) is not None for action in actions)


def test_settings_and_developer_panel_windows_are_shown_and_populated() -> None:
    appkit = FakeAppKit()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    runtime = build_menu_bar_app(appkit=appkit, controller=controller, development_mode=True)

    runtime.action_dispatcher.settings_()
    runtime.action_dispatcher.developer_panel_()

    settings = runtime.action_dispatcher.settings_window
    developer = runtime.action_dispatcher.developer_panel
    assert settings is not None
    assert settings.shown is True
    assert settings.title == "Gaze Settings"
    assert settings.content_rect == (0, 0, 420, 320)
    assert (
        "No recording, no screenshots, no clicks, manual activation by default."
        in settings.content_text
    )
    assert "Auto-Activate" in settings.content_text
    assert "Activation Delay" in settings.content_text
    assert "Heatmap" not in settings.content_text
    assert "recalibrate" in settings.action_names
    assert "toggle_auto_activate" in settings.action_names
    assert "set_auto_activate_debounce" in settings.action_names
    assert developer is not None
    assert developer.shown is True
    assert developer.title == "Gaze Developer Panel"
    assert developer.content_rect == (0, 0, 460, 480)
    assert "Start Scripted Demo" in developer.content_text
    assert {control.action for control in developer_controls()} <= set(developer.action_names)


def test_menu_refreshes_after_commands_and_surfaces_status_feedback() -> None:
    appkit = FakeAppKit()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    runtime = build_menu_bar_app(appkit=appkit, controller=controller, development_mode=True)

    runtime.action_dispatcher.toggle_gaze_()

    assert "Status: ready" in runtime.status_item.menu.items
    assert "Message: Gaze ready" in runtime.status_item.menu.items
    assert "Disable Gaze" in runtime.status_item.menu.items

    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.91))
    controller.override_fake_lock_state(True)
    runtime.refresh_menu()
    runtime.action_dispatcher.manual_activate_()

    assert "Target: Terminal" in runtime.status_item.menu.items
    assert "Message: Activated Terminal" in runtime.status_item.menu.items


def test_runtime_hotkeys_trigger_same_command_seams_and_refresh_menu() -> None:
    appkit = FakeAppKit()
    controller = FakePrototypeController(
        overlay=RecordingBorderOverlay(),
        activation=FakeActivationService(),
    )
    runtime = build_menu_bar_app(appkit=appkit, controller=controller, development_mode=True)

    runtime.hotkeys.trigger("option+cmd+g")
    controller.set_fake_target(FakeTarget("Terminal", 10, 20, 800, 600, 0.91))
    controller.override_fake_lock_state(True)
    runtime.hotkeys.trigger("cmd+g")

    assert controller.state.flags.gaze_enabled is True
    assert controller.state.last_status_message == "Activated Terminal"
    assert "Message: Activated Terminal" in runtime.status_item.menu.items
