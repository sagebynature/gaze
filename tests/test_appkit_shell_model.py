from gaze.core.prototype import FakePrototypeController
from gaze.desktop.activation import FakeActivationService
from gaze.overlays.border import RecordingBorderOverlay
from gaze.ui.appkit_shell import build_menu_bar_app


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

    def setActivationPolicy_(self, policy: int) -> None:
        self.policy = policy

    def terminate_(self, sender) -> None:
        self.terminated_by = sender


class FakeMenu:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.raw_items = []

    def addItem_(self, item) -> None:
        self.items.append(item.title)
        self.raw_items.append(item)


class FakeMenuItem:
    def __init__(self) -> None:
        self.title = ""
        self.action = None
        self.target = None

    @classmethod
    def alloc(cls):
        return cls()

    def initWithTitle_action_keyEquivalent_(self, title: str, action, key: str):
        self.title = title
        self.action = action
        return self

    def setTarget_(self, target) -> None:
        self.target = target

    def setAction_(self, action) -> None:
        self.action = action


class FakeAppKit:
    NSApplicationActivationPolicyAccessory = 1
    NSSquareStatusItemLength = -2.0
    NSMenuItem = FakeMenuItem

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
    assert runtime.status_item.menu is not None
    assert "Status: off" in runtime.status_item.menu.items
    assert "Settings" in runtime.status_item.menu.items
    assert "Open Developer Panel" in runtime.status_item.menu.items
    action_items = {
        item.title: item
        for item in runtime.status_item.menu.raw_items
        if item.action is not None
    }
    assert "Settings" in action_items
    assert "Open Developer Panel" in action_items
    assert "Enable Gaze" in action_items
    assert "Toggle Border" in action_items
    assert "Toggle Heatmap" in action_items
    assert "Recalibrate" in action_items
    assert "Quit" in action_items


def test_every_menu_model_action_has_runtime_selector() -> None:
    from gaze.core.state import GazeAppState
    from gaze.ui.appkit_shell import selector_for_menu_action
    from gaze.ui.menu_model import menu_items_for_state

    actions = [item.action for item in menu_items_for_state(GazeAppState.default()) if item.action]

    assert actions
    assert all(selector_for_menu_action(action) is not None for action in actions)
