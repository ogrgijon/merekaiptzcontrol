"""Tests for Windows UVC camera command mapping."""

from src.camera.camera_device import CameraStatus
from src.camera.usb_camera_backend import UvcBridge, UvcCameraDevice


class FakeBridge:
    def __init__(self, capability_flags):
        self.flags = capability_flags
        self.commands = []
        self.supports_zoom_absolute = bool(capability_flags & 262144)
        self.supports_pan_tilt_absolute = bool(capability_flags & 65536)

    def open(self, index):
        return True

    def capability_flags(self):
        return self.flags

    def command(self, name, value=0):
        self.commands.append((name, value))
        return True

    def set_zoom_absolute(self, value):
        self.commands.append(("lc_zoom_absolute", value))
        return True

    def close(self):
        pass


class FakeNativeFunction:
    def __call__(self, *args):
        return 0


class OlderNativeDll:
    exports = {
        "lc_list_devices",
        "lc_open",
        "lc_close",
        "lc_move_pan",
        "lc_move_tilt",
        "lc_stop",
        "lc_home",
        "lc_zoom",
        "lc_save_preset",
        "lc_goto_preset",
        "lc_capabilities",
        "lc_focus_auto",
        "lc_focus_manual",
        "lc_focus",
        "lc_iris",
        "lc_exposure",
        "lc_white_balance_auto",
        "lc_white_balance_manual",
        "lc_contrast",
        "lc_video_proc_amp",
    }

    def __init__(self):
        self.functions = {}

    def __getattr__(self, name):
        if name not in self.exports:
            raise AttributeError(name)
        return self.functions.setdefault(name, FakeNativeFunction())


def test_bridge_loads_when_optional_ptz_exports_are_missing():
    bridge = UvcBridge.__new__(UvcBridge)
    bridge._dll = OlderNativeDll()
    bridge._handle = 1

    bridge._configure_api()

    assert bridge.available
    assert not bridge.supports_zoom_absolute
    assert not bridge.supports_pan_tilt_absolute
    assert bridge.get_ptz_position(0) is None
    assert not bridge.set_zoom_absolute(123)
    assert not bridge.set_pan_tilt_absolute(123, 456)


def test_standard_uvc_tilt_up_uses_positive_relative_direction(monkeypatch):
    bridge = FakeBridge(131072)
    monkeypatch.setattr(
        "src.camera.usb_camera_backend.UvcBridge", lambda: bridge
    )
    camera = UvcCameraDevice(0)

    assert camera.connect()
    assert camera.status == CameraStatus.CONNECTED
    assert camera.pan_tilt_relative(15, 15, 0, -100)

    assert bridge.commands == [("lc_move_tilt", 15)]


def test_usb_xu_tilt_direction_is_unchanged(monkeypatch):
    bridge = FakeBridge(1)
    monkeypatch.setattr(
        "src.camera.usb_camera_backend.UvcBridge", lambda: bridge
    )
    camera = UvcCameraDevice(0)

    assert camera.connect()
    assert camera.pan_tilt_relative(15, 15, 0, -100)

    assert bridge.commands == [("lc_move_tilt", -1)]


def test_standard_uvc_zoom_release_sends_stop_value(monkeypatch):
    bridge = FakeBridge(131072 | 2)
    monkeypatch.setattr(
        "src.camera.usb_camera_backend.UvcBridge", lambda: bridge
    )
    camera = UvcCameraDevice(0)

    assert camera.connect()
    assert camera.capabilities["zoom"]
    assert camera.zoom_tele(7)
    assert camera.zoom_stop()

    assert bridge.commands == [("lc_zoom", 7), ("lc_zoom", 0)]


def test_standard_uvc_absolute_zoom_uses_bridge_command(monkeypatch):
    bridge = FakeBridge(131072 | 2 | 262144)
    monkeypatch.setattr(
        "src.camera.usb_camera_backend.UvcBridge", lambda: bridge
    )
    camera = UvcCameraDevice(0)

    assert camera.connect()
    assert camera.capabilities["zoom_absolute"]
    assert camera.zoom_absolute(1234)

    assert bridge.commands == [("lc_zoom_absolute", 1234)]
