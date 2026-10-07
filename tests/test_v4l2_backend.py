"""Tests for generic V4L2 PTZ cameras without requiring Linux hardware."""

from src.camera import v4l2_backend
from src.camera.camera_device import CameraStatus
from src.camera.camera_manager import CameraManager

PTZ_CONTROLS = (
    "                     pan_relative 0x009a0903 (int) : "
    "min=-100 max=100 step=1 default=0 value=0\n"
    "                     tilt_relative 0x009a0904 (int) : "
    "min=-100 max=100 step=1 default=0 value=0\n"
    "                     zoom_continuous 0x009a090f (int) : "
    "min=-1 max=1 step=1 default=0 value=0\n"
    "                     focus_auto 0x009a090c (bool) : "
    "default=1 value=1\n"
    "                     brightness 0x00980900 (int) : "
    "min=0 max=255 step=1 default=128 value=128\n"
)


def test_parse_controls_includes_ranges_values_and_flags():
    controls = v4l2_backend._parse_controls(
        " pan_absolute 0x009a0908 (int) : "
        "min=-20 max=20 step=2 default=0 value=4 flags=inactive\n"
    )

    control = controls["pan_absolute"]
    assert (control.minimum, control.maximum, control.step, control.value) == (
        -20,
        20,
        2,
        4,
    )
    assert not control.usable


def test_discovery_only_returns_nodes_with_usable_pan_and_tilt(monkeypatch):
    def fake_run(arguments):
        if "--list-ctrls" in arguments:
            if arguments[1] == "/dev/video0":
                return PTZ_CONTROLS
            return (
                "brightness 0x00980900 (int) : "
                "min=0 max=255 step=1 value=128\n"
            )
        return "Driver name : uvcvideo\nCard type : Generic UVC PTZ\n"

    monkeypatch.setattr(v4l2_backend, "_run_v4l2", fake_run)

    cameras = v4l2_backend.list_cameras(["/dev/video0", "/dev/video1"])

    assert cameras == [
        v4l2_backend.V4L2Camera("/dev/video0", "Generic UVC PTZ")
    ]
    assert cameras[0].port == "v4l2:///dev/video0|Generic UVC PTZ"


def test_v4l2_camera_uses_relative_controls_and_reports_capabilities(
    monkeypatch,
):
    commands = []

    def fake_run(arguments):
        commands.append(arguments)
        if "--list-ctrls" in arguments:
            return PTZ_CONTROLS
        return ""

    monkeypatch.setattr(v4l2_backend, "_run_v4l2", fake_run)
    camera = v4l2_backend.V4L2CameraDevice(
        v4l2_backend.V4L2Camera("/dev/video0", "Generic PTZ")
    )

    assert camera.capabilities["pan_tilt"]
    assert camera.capabilities["zoom"]
    assert camera.capabilities["focus"]
    assert camera.capabilities["brightness"]
    assert camera.connect()
    assert camera.status is CameraStatus.CONNECTED
    assert camera.pan_tilt_relative(24, 24, 100, -100)
    assert ["--device", "/dev/video0", "--set-ctrl=pan_relative=1"] in commands
    assert [
        "--device",
        "/dev/video0",
        "--set-ctrl=tilt_relative=-1",
    ] in commands
    assert camera.zoom_tele(7)
    assert [
        "--device",
        "/dev/video0",
        "--set-ctrl=zoom_continuous=1",
    ] in commands
    assert camera.zoom_stop()
    assert [
        "--device",
        "/dev/video0",
        "--set-ctrl=zoom_continuous=0",
    ] in commands


def test_v4l2_camera_moves_absolute_controls_and_maps_zoom(monkeypatch):
    commands = []
    controls = (
        "                     pan_absolute 0x009a0908 (int) : "
        "min=-100 max=100 step=1 default=0 value=0\n"
        "                     tilt_absolute 0x009a0909 (int) : "
        "min=-50 max=50 step=1 default=0 value=0\n"
        "                     zoom_absolute 0x009a090d (int) : "
        "min=10 max=110 step=1 default=10 value=10\n"
    )

    def fake_run(arguments):
        commands.append(arguments)
        if "--list-ctrls" in arguments:
            return controls
        if "--get-ctrl=pan_absolute" in arguments:
            return "pan_absolute: 0\n"
        return ""

    monkeypatch.setattr(v4l2_backend, "_run_v4l2", fake_run)
    camera = v4l2_backend.V4L2CameraDevice(
        v4l2_backend.V4L2Camera("/dev/video2", "Absolute PTZ")
    )

    assert camera.connect()
    assert camera.pan_tilt_relative(24, 24, 100, -100)
    assert ["--device", "/dev/video2", "--get-ctrl=pan_absolute"] in commands
    assert ["--device", "/dev/video2", "--set-ctrl=pan_absolute=2"] in commands
    assert [
        "--device",
        "/dev/video2",
        "--set-ctrl=tilt_absolute=-1",
    ] in commands
    assert camera.zoom_absolute(0)
    assert [
        "--device",
        "/dev/video2",
        "--set-ctrl=zoom_absolute=10",
    ] in commands
    assert camera.zoom_absolute(0xFFFF)
    assert [
        "--device",
        "/dev/video2",
        "--set-ctrl=zoom_absolute=110",
    ] in commands


def test_manager_adds_v4l2_camera_from_discovered_port(monkeypatch):
    class UnavailableBridge:
        available = False

    monkeypatch.setattr(
        "src.camera.camera_manager.list_v4l2_cameras",
        lambda: [v4l2_backend.V4L2Camera("/dev/video0", "Generic PTZ")],
    )
    monkeypatch.setattr("src.camera.camera_manager.sys.platform", "linux")
    monkeypatch.setattr(
        "src.camera.camera_manager.UvcBridge", UnavailableBridge
    )

    manager = CameraManager()
    ports = manager.get_available_ports()

    assert "v4l2:///dev/video0|Generic PTZ" in ports
    assert manager.add_camera("generic", ports[0])
    assert isinstance(
        manager.get_camera("generic"), v4l2_backend.V4L2CameraDevice
    )
