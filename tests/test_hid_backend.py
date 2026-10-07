"""Tests for the USB HID transport without requiring a camera."""

from src.camera.hid_backend import HidCamera, HidCameraDevice, list_cameras


class FakeHidDevice:
    def __init__(self):
        self.opened_path = None
        self.reports = []
        self.closed = False

    def open_path(self, path):
        self.opened_path = path

    def write(self, report):
        self.reports.append(report)
        return len(report)

    def close(self):
        self.closed = True


def test_list_cameras_filters_to_ptz_usage_page(monkeypatch):
    entries = [
        {"path": b"ptz", "product_string": "Logi Group Camera", "usage_page": 0x0C},
        {"path": b"keyboard", "product_string": "Other", "usage_page": 0x01},
    ]
    monkeypatch.setattr("src.camera.hid_backend.hid.enumerate", lambda *_: entries)

    cameras = list_cameras()

    assert len(cameras) == 2
    assert cameras[0].identity == "70747a"
    assert cameras[0].name == "Logi Group Camera"


def test_hid_commands_use_ptz_report_format(monkeypatch):
    fake_device = FakeHidDevice()
    monkeypatch.setattr("src.camera.hid_backend.hid.device", lambda: fake_device)
    camera = HidCamera(0, "Test Camera", b"test-path")
    transport = HidCameraDevice(camera)

    assert transport.connect()
    assert transport.pan_tilt_relative(15, 15, -100, 0)
    assert transport.zoom_tele(7)

    assert fake_device.opened_path == b"test-path"
    assert fake_device.reports[0][0:2] == [0x0B, 0x03]
    assert fake_device.reports[1][0:2] == [0x0B, 0x04]
    assert all(len(report) == 32 for report in fake_device.reports)


def test_hid_capabilities_reflect_supported_controls():
    transport = HidCameraDevice(HidCamera(0, "Test Camera", b"test-path"))

    assert transport.capabilities == {
        "pan_tilt": True,
        "pan_tilt_absolute": False,
        "zoom": True,
        "zoom_absolute": False,
        "focus": False,
        "iris": False,
        "white_balance": False,
        "exposure": False,
        "presets": False,
    }
