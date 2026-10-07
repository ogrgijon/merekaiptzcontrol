"""Direct HID transport for USB PTZ cameras."""

from __future__ import annotations

import logging
from typing import List, NamedTuple

import hid

from .camera_device import CameraStatus

logger = logging.getLogger(__name__)

SUPPORTED_VENDOR_ID = 0x046D
SUPPORTED_PRODUCT_IDS = (0x086E, 0x085F)
PTZ_REPORT_ID = 0x0B
REPORT_SIZE = 32


class HidCamera(NamedTuple):
    """A supported USB HID camera interface."""

    index: int
    name: str
    path: bytes

    @property
    def identity(self) -> str:
        """Stable identifier for this HID interface."""
        if isinstance(self.path, bytes):
            return self.path.hex()
        return str(self.path)


def list_cameras() -> List[HidCamera]:
    """Find USB PTZ HID interfaces."""
    cameras: List[HidCamera] = []
    for product_id in SUPPORTED_PRODUCT_IDS:
        for device in hid.enumerate(SUPPORTED_VENDOR_ID, product_id):
            if device.get("usage_page") != 0x0C:
                continue
            cameras.append(
                HidCamera(
                    len(cameras),
                    device.get("product_string") or "USB PTZ Camera",
                    device["path"],
                )
            )
    return cameras


class HidCameraDevice:
    """CameraDevice-compatible HID transport used by PyPTZPro."""

    def __init__(self, camera: HidCamera) -> None:
        self.camera = camera
        self.device = hid.device()
        self.status = CameraStatus.DISCONNECTED
        self._connected = False
        self.capabilities = {
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

    @property
    def display_name(self) -> str:
        return self.camera.name

    def connect(self) -> bool:
        try:
            self.status = CameraStatus.CONNECTING
            self.device.open_path(self.camera.path)
            self._connected = True
            self.status = CameraStatus.CONNECTED
            return True
        except Exception:
            logger.exception("Could not open USB HID camera")
            self.status = CameraStatus.ERROR
            return False

    def disconnect(self) -> None:
        if self._connected:
            self.device.close()
        self._connected = False
        self.status = CameraStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._connected

    def _send(self, value: int) -> bool:
        if not self._connected:
            return False
        report = [0] * REPORT_SIZE
        report[0] = PTZ_REPORT_ID
        report[1] = value & 0xFF
        try:
            return self.device.write(report) >= 0
        except Exception:
            logger.exception("Failed to send USB HID command 0x%02x", value)
            self.status = CameraStatus.ERROR
            return False

    def pan_tilt_relative(self, pan_speed: int, tilt_speed: int, pan_move: int, tilt_move: int) -> bool:
        success = True
        if tilt_move < 0:
            success = self._send(0x00) and success
        elif tilt_move > 0:
            success = self._send(0x01) and success
        if pan_move > 0:
            success = self._send(0x02) and success
        elif pan_move < 0:
            success = self._send(0x03) and success
        return success

    def pan_tilt_stop(self) -> bool:
        return True

    def zoom_tele(self, speed: int) -> bool:
        return self._send(0x04)

    def zoom_wide(self, speed: int) -> bool:
        return self._send(0x05)

    def zoom_stop(self) -> bool:
        return True

    def pan_tilt_absolute(self, pan_speed: int, tilt_speed: int, pan_pos: int, tilt_pos: int) -> bool:
        return False

    def zoom_absolute(self, zoom_pos: int) -> bool:
        return False

    def focus_auto(self) -> bool:
        return False

    def focus_manual(self) -> bool:
        return False

    def focus_far(self, speed: int) -> bool:
        return False

    def focus_near(self, speed: int) -> bool:
        return False

    def focus_stop(self) -> bool:
        return False

    def iris_open(self, speed: int) -> bool:
        return False

    def iris_close(self, speed: int) -> bool:
        return False

    def iris_stop(self) -> bool:
        return False

    def white_balance_auto(self) -> bool:
        return False

    def white_balance_indoor(self) -> bool:
        return False

    def white_balance_outdoor(self) -> bool:
        return False
