"""ctypes adapter for the native USB Extension Unit bridge."""

from __future__ import annotations

import ctypes
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from .camera_device import CameraStatus

logger = logging.getLogger(__name__)


class UvcBridge:
    """Load and call the Windows UVC camera bridge DLL."""

    def __init__(self) -> None:
        self._dll: Optional[ctypes.WinDLL] = None
        self._handle: Optional[int] = None
        self._zoom_absolute_fn = None
        self._get_ptz_position_fn = None
        self._set_pan_tilt_absolute_fn = None
        if sys.platform != "win32":
            return

        repo_root = Path(__file__).parents[2]
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.extend(
                [
                    Path(sys.executable).parent / "merekaiptzcontrol_camera.dll",
                    Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
                    / "merekaiptzcontrol_camera.dll",
                ]
            )
        candidates.extend(
            [
                repo_root / "dev" / "native-build" / "Release" / "merekaiptzcontrol_camera.dll",
                repo_root / "dev" / "native-build" / "Debug" / "merekaiptzcontrol_camera.dll",
                repo_root / "dev" / "native-build" / "merekaiptzcontrol_camera.dll",
            ]
        )
        for candidate in candidates:
            if not candidate.exists():
                continue
            try:
                self._dll = ctypes.WinDLL(str(candidate))
                self._configure_api()
                break
            except OSError:
                logger.exception("Unable to load USB camera bridge: %s", candidate)
                self._dll = None

        if self._dll is None:
            logger.debug(
                "Windows UVC bridge not found; build dev/native-build/Release/"
                "merekaiptzcontrol_camera.dll to enable UVC camera support"
            )

    @property
    def available(self) -> bool:
        return self._dll is not None

    def _configure_api(self) -> None:
        assert self._dll is not None
        self._dll.lc_list_devices.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        self._dll.lc_list_devices.restype = ctypes.c_int
        self._dll.lc_open.argtypes = [ctypes.c_int]
        self._dll.lc_open.restype = ctypes.c_void_p
        self._dll.lc_close.argtypes = [ctypes.c_void_p]
        self._dll.lc_close.restype = None
        for name in (
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
        ):
            function = getattr(self._dll, name)
            function.argtypes = [ctypes.c_void_p, ctypes.c_int]
            function.restype = ctypes.c_int
        self._zoom_absolute_fn = getattr(self._dll, "lc_zoom_absolute", None)
        if self._zoom_absolute_fn is not None:
            self._zoom_absolute_fn.argtypes = [ctypes.c_void_p, ctypes.c_int]
            self._zoom_absolute_fn.restype = ctypes.c_int
        self._get_ptz_position_fn = getattr(
            self._dll, "lc_get_ptz_position", None
        )
        if self._get_ptz_position_fn is not None:
            self._get_ptz_position_fn.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
            ]
            self._get_ptz_position_fn.restype = ctypes.c_int
        self._set_pan_tilt_absolute_fn = getattr(
            self._dll, "lc_set_pan_tilt_absolute", None
        )
        if self._set_pan_tilt_absolute_fn is not None:
            self._set_pan_tilt_absolute_fn.argtypes = [
                ctypes.c_void_p,
                ctypes.c_int,
                ctypes.c_int,
            ]
            self._set_pan_tilt_absolute_fn.restype = ctypes.c_int
        missing_exports = [
            name
            for name, function in (
                ("lc_zoom_absolute", self._zoom_absolute_fn),
                ("lc_get_ptz_position", self._get_ptz_position_fn),
                ("lc_set_pan_tilt_absolute", self._set_pan_tilt_absolute_fn),
            )
            if function is None
        ]
        if missing_exports:
            logger.warning(
                "Loaded an older camera bridge without %s; rebuild the native "
                "Release DLL to enable those operations",
                ", ".join(missing_exports),
            )
        self._dll.lc_video_proc_amp.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        self._dll.lc_video_proc_amp.restype = ctypes.c_int

    def list_devices(self) -> List[str]:
        if not self.available:
            return []
        buffer = ctypes.create_string_buffer(16384)
        count = self._dll.lc_list_devices(buffer, len(buffer))
        if count <= 0:
            return []
        return json.loads(buffer.value.decode("utf-8"))

    def open(self, index: int) -> bool:
        if not self.available:
            return False
        self._handle = self._dll.lc_open(index)
        return bool(self._handle)

    def close(self) -> None:
        if self._handle:
            self._dll.lc_close(self._handle)
            self._handle = None

    def command(self, name: str, value: int = 0) -> bool:
        if not self._handle or not self.available:
            return False
        return bool(getattr(self._dll, name)(self._handle, value))

    def capability_flags(self) -> int:
        if not self._handle or not self.available:
            return 0
        return int(self._dll.lc_capabilities(self._handle, 0))

    def get_ptz_position(self, axis: int) -> Optional[int]:
        if (
            not self._handle
            or not self.available
            or self._get_ptz_position_fn is None
        ):
            return None
        position = int(self._get_ptz_position_fn(self._handle, axis))
        return position if position >= 0 else None

    @property
    def supports_zoom_absolute(self) -> bool:
        return self._zoom_absolute_fn is not None

    @property
    def supports_pan_tilt_absolute(self) -> bool:
        return self._set_pan_tilt_absolute_fn is not None

    def set_zoom_absolute(self, position: int) -> bool:
        if not self._handle or self._zoom_absolute_fn is None:
            return False
        return bool(self._zoom_absolute_fn(self._handle, position))

    def set_pan_tilt_absolute(self, pan: int, tilt: int) -> bool:
        if not self._handle or self._set_pan_tilt_absolute_fn is None:
            return False
        return bool(self._set_pan_tilt_absolute_fn(self._handle, pan, tilt))


class UvcCameraDevice:
    """CameraDevice-compatible Windows UVC transport."""

    def __init__(self, index: int, name: Optional[str] = None) -> None:
        self.bridge = UvcBridge()
        self.index = index
        self.name = name or f"UVC camera {index}"
        self.status = CameraStatus.DISCONNECTED
        self._connected = False
        self.capabilities = {
            "pan_tilt": True,
            "zoom": True,
            "zoom_absolute": False,
            "focus": False,
            "iris": False,
            "white_balance": False,
            "exposure": False,
            "presets": True,
            "contrast": False,
            "brightness": False,
            "saturation": False,
            "sharpness": False,
            "gamma": False,
            "hue": False,
            "gain": False,
            "backlight": False,
            "color_enable": False,
            "uvc_standard": False,
        }

    @property
    def display_name(self) -> str:
        return self.name

    def connect(self) -> bool:
        self.status = CameraStatus.CONNECTING
        self._connected = self.bridge.open(self.index)
        if self._connected:
            flags = self.bridge.capability_flags()
            self.capabilities.update(
                {
                    "pan_tilt": bool(flags & 1),
                    "pan_tilt_absolute": (
                        bool(flags & 65536)
                        and getattr(
                            self.bridge, "supports_pan_tilt_absolute", False
                        )
                    ),
                    "pan_tilt_home": bool(flags & (1 | 65536)),
                    "uvc_standard": bool(flags & 131072),
                    "zoom": bool(flags & 2),
                    "zoom_absolute": (
                        bool(flags & 262144)
                        and getattr(self.bridge, "supports_zoom_absolute", False)
                    ),
                    "focus": bool(flags & 4),
                    "iris": bool(flags & 8),
                    "white_balance": bool(flags & 16),
                    "exposure": bool(flags & 32),
                    "contrast": bool(flags & 64),
                    "brightness": bool(flags & 256),
                    "saturation": bool(flags & 512),
                    "sharpness": bool(flags & 1024),
                    "gamma": bool(flags & 2048),
                    "hue": bool(flags & 4096),
                    "gain": bool(flags & 8192),
                    "backlight": bool(flags & 16384),
                    "color_enable": bool(flags & 32768),
                    "presets": bool(flags & 128),
                }
            )
        self.status = CameraStatus.CONNECTED if self._connected else CameraStatus.ERROR
        return self._connected

    def disconnect(self) -> None:
        self.bridge.close()
        self._connected = False
        self.status = CameraStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._connected

    def pan_tilt_relative(
        self, pan_speed: int, tilt_speed: int, pan_move: int, tilt_move: int
    ) -> bool:
        pan_direction = (pan_move > 0) - (pan_move < 0)
        tilt_direction = (tilt_move > 0) - (tilt_move < 0)
        if self.capabilities.get("uvc_standard"):
            success = True
            if pan_direction:
                pan_value = pan_direction * max(1, min(24, pan_speed))
                success = self.bridge.command("lc_move_pan", pan_value)
            if tilt_direction:
                tilt_value = -tilt_direction * max(1, min(24, tilt_speed))
                success = self.bridge.command("lc_move_tilt", tilt_value) and success
            return success if pan_direction or tilt_direction else self.pan_tilt_stop()

        # The USB XU packet contains both axes. Sending a zero second
        # axis as a separate command cancels the first axis immediately.
        if pan_direction:
            return self.bridge.command("lc_move_pan", pan_direction)
        if tilt_direction:
            return self.bridge.command("lc_move_tilt", tilt_direction)
        return self.pan_tilt_stop()

    def pan_tilt_stop(self) -> bool:
        return self.bridge.command("lc_stop")

    def zoom_tele(self, speed: int) -> bool:
        return self.bridge.command("lc_zoom", max(1, speed))

    def zoom_wide(self, speed: int) -> bool:
        return self.bridge.command("lc_zoom", -max(1, speed))

    def zoom_stop(self) -> bool:
        return self.bridge.command("lc_zoom", 0)

    def zoom_absolute(self, zoom_pos: int) -> bool:
        return self.bridge.set_zoom_absolute(
            max(0, min(0xFFFF, zoom_pos))
        )

    def get_ptz_position(self) -> dict[str, Optional[int]]:
        position: dict[str, Optional[int]] = {
            "pan": None,
            "tilt": None,
            "zoom": None,
        }
        for axis, key in ((0, "pan"), (1, "tilt")):
            value = self.bridge.get_ptz_position(axis)
            if value is not None:
                position[key] = value
        if self.capabilities.get("zoom_absolute"):
            value = self.bridge.get_ptz_position(2)
            if value is not None:
                position["zoom"] = value
        return position

    def focus_auto(self) -> bool:
        return self.bridge.command("lc_focus_auto")

    def focus_manual(self) -> bool:
        return self.bridge.command("lc_focus_manual")

    def focus_far(self, speed: int) -> bool:
        return self.bridge.command("lc_focus", max(1, speed))

    def focus_near(self, speed: int) -> bool:
        return self.bridge.command("lc_focus", -max(1, speed))

    def focus_stop(self) -> bool:
        return True

    def iris_open(self, speed: int) -> bool:
        return self.bridge.command("lc_iris", max(1, speed))

    def iris_close(self, speed: int) -> bool:
        return self.bridge.command("lc_iris", -max(1, speed))

    def iris_stop(self) -> bool:
        return True

    def white_balance_auto(self) -> bool:
        return self.bridge.command("lc_white_balance_auto")

    def white_balance_indoor(self) -> bool:
        return self.bridge.command("lc_white_balance_manual", 3200)

    def white_balance_outdoor(self) -> bool:
        return self.bridge.command("lc_white_balance_manual", 5600)

    def exposure(self, value: int) -> bool:
        return self.bridge.command("lc_exposure", value)

    def contrast(self, value: int) -> bool:
        return self.bridge.command("lc_contrast", value)

    def video_proc_amp(self, property_id: int, value: int) -> bool:
        """Set a standard DirectShow video-processing value from 0 to 100."""
        if not self.bridge._handle or not self.bridge.available:
            return False
        return bool(self.bridge._dll.lc_video_proc_amp(self.bridge._handle, property_id, value))

    def pan_tilt_absolute(
        self, pan_speed: int, tilt_speed: int, pan_pos: int, tilt_pos: int
    ) -> bool:
        if pan_pos == 0 and tilt_pos == 0:
            return self.home()
        if not self.capabilities.get("pan_tilt_absolute"):
            return False
        pan_normalized = round((pan_pos + 2448) * 0xFFFF / 4896)
        tilt_normalized = round((tilt_pos + 1296) * 0xFFFF / 2592)
        if not self.bridge._handle or not self.bridge.available:
            return False
        return self.bridge.set_pan_tilt_absolute(
            pan_normalized, tilt_normalized
        )

    def home(self) -> bool:
        return self.bridge.command("lc_home")

    def save_preset(self, index: int) -> bool:
        return self.bridge.command("lc_save_preset", index)

    def goto_preset(self, index: int) -> bool:
        return self.bridge.command("lc_goto_preset", index)
