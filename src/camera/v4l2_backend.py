"""Control UVC/PTZ cameras through Linux V4L2 controls using v4l2-ctl."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .camera_device import CameraStatus

logger = logging.getLogger(__name__)

CONTROL_LINE = re.compile(
    r"^\s+([a-zA-Z0-9_]+)\s+0x[0-9a-fA-F]+\s+\(([^)]+)\)\s*:(.*)$"
)
INTEGER = re.compile(r"\b(min|max|step|value)=(-?\d+)")
CARD_NAME = re.compile(r"^\s*Card type\s*:\s*(.+?)\s*$", re.MULTILINE)


@dataclass
class V4L2Control:
    """A control reported by v4l2-ctl."""

    name: str
    minimum: int = 0
    maximum: int = 1
    step: int = 1
    value: int = 0
    flags: str = ""

    @property
    def usable(self) -> bool:
        """Whether this control can be read or written."""
        return not any(
            flag in self.flags
            for flag in ("disabled", "inactive", "read-only")
        )


@dataclass(frozen=True)
class V4L2Camera:
    """A V4L2 video node with pan and tilt controls."""

    path: str
    name: str

    @property
    def port(self) -> str:
        return f"v4l2://{self.path}|{self.name}"


def _parse_controls(output: str) -> Dict[str, V4L2Control]:
    controls: Dict[str, V4L2Control] = {}
    for line in output.splitlines():
        match = CONTROL_LINE.match(line)
        if not match:
            continue
        name, control_type, details = match.groups()
        values = {key: int(value) for key, value in INTEGER.findall(details)}
        flags_match = re.search(r"\bflags=([^ ]+)", details)
        default_match = re.search(r"\bdefault=(-?\d+)", details)
        default = int(default_match.group(1)) if default_match else 0
        controls[name] = V4L2Control(
            name=name,
            minimum=values.get("min", 0),
            maximum=values.get("max", 1 if control_type == "bool" else 0),
            step=max(1, values.get("step", 1)),
            value=values.get("value", default),
            flags=flags_match.group(1) if flags_match else "",
        )
    return controls


def _run_v4l2(arguments: List[str]) -> str:
    executable = shutil.which("v4l2-ctl")
    if executable is None:
        raise FileNotFoundError(
            "v4l2-ctl was not found; install v4l-utils to use V4L2 cameras"
        )
    result = subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        timeout=3,
        check=False,
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            message or f"v4l2-ctl exited with status {result.returncode}"
        )
    return result.stdout


def list_cameras(
    device_paths: Optional[Iterable[str]] = None,
) -> List[V4L2Camera]:
    """Find video nodes that expose usable pan and tilt controls."""
    paths = device_paths
    if paths is None:
        paths = (str(path) for path in sorted(Path("/dev").glob("video*")))

    cameras: List[V4L2Camera] = []
    for path in paths:
        try:
            controls_output = _run_v4l2(["--device", path, "--list-ctrls"])
        except FileNotFoundError:
            logger.warning(
                "V4L2 camera discovery unavailable: v4l2-ctl is not installed"
            )
            return []
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            logger.debug("Skipping V4L2 node %s: %s", path, error)
            continue

        controls = _parse_controls(controls_output)
        usable_names = {
            name for name, control in controls.items() if control.usable
        }
        if not (
            usable_names.intersection({"pan_relative", "pan_absolute"})
            and usable_names.intersection({"tilt_relative", "tilt_absolute"})
        ):
            continue

        try:
            info = _run_v4l2(["--device", path, "--info"])
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            logger.debug(
                "Could not read V4L2 camera name for %s: %s", path, error
            )
            info = ""
        match = CARD_NAME.search(info)
        name = match.group(1) if match else Path(path).name
        cameras.append(V4L2Camera(path=path, name=name))
    return cameras


class V4L2CameraDevice:
    """CameraDevice-compatible controller for standard V4L2 controls."""

    def __init__(self, camera: V4L2Camera) -> None:
        self.camera = camera
        self.status = CameraStatus.DISCONNECTED
        self._connected = False
        self._controls: Dict[str, V4L2Control] = {}
        self.capabilities: Dict[str, bool] = {}
        self._refresh_capabilities()

    @property
    def display_name(self) -> str:
        return self.camera.name

    def _refresh_capabilities(self) -> bool:
        try:
            output = _run_v4l2(["--device", self.camera.path, "--list-ctrls"])
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            logger.exception(
                "Could not list V4L2 controls for %s", self.camera.path
            )
            return False
        self._controls = _parse_controls(output)
        names = {
            name for name, control in self._controls.items() if control.usable
        }
        pan = bool(names.intersection({"pan_relative", "pan_absolute"}))
        tilt = bool(names.intersection({"tilt_relative", "tilt_absolute"}))
        pan_home = bool(names.intersection({"pan_absolute", "pan_reset"}))
        tilt_home = bool(names.intersection({"tilt_absolute", "tilt_reset"}))
        self.capabilities = {
            "pan_tilt": pan and tilt,
            "pan_tilt_absolute": (
                "pan_absolute" in names and "tilt_absolute" in names
            ),
            "pan_tilt_home": pan_home and tilt_home,
            "zoom": bool(
                names.intersection(
                    {"zoom_absolute", "zoom_relative", "zoom_continuous"}
                )
            ),
            "zoom_absolute": "zoom_absolute" in names,
            "focus": bool(
                names.intersection(
                    {"focus_absolute", "focus_relative", "focus_auto"}
                )
            ),
            "iris": bool(
                names.intersection({"iris_absolute", "iris_relative", "iris"})
            ),
            "white_balance": bool(
                names.intersection(
                    {"white_balance_automatic", "white_balance_temperature"}
                )
            ),
            "exposure": "exposure_absolute" in names,
            "presets": False,
            "contrast": "contrast" in names,
            "brightness": "brightness" in names,
            "saturation": "saturation" in names,
            "sharpness": "sharpness" in names,
            "gamma": "gamma" in names,
            "hue": "hue" in names,
            "gain": "gain" in names,
            "backlight": "backlight_compensation" in names,
            "color_enable": "colorfx" in names,
        }
        return True

    def connect(self) -> bool:
        self.status = CameraStatus.CONNECTING
        if not self._refresh_capabilities() or not self.capabilities.get(
            "pan_tilt"
        ):
            self.status = CameraStatus.ERROR
            return False
        self._connected = True
        self.status = CameraStatus.CONNECTED
        return True

    def disconnect(self) -> None:
        self._connected = False
        self.status = CameraStatus.DISCONNECTED

    def is_connected(self) -> bool:
        return self._connected

    def _set_control(self, name: str, value: int) -> bool:
        control = self._controls.get(name)
        if not self._connected or control is None or not control.usable:
            return False
        value = max(control.minimum, min(control.maximum, int(value)))
        if (value - control.minimum) % control.step:
            value = (
                control.minimum
                + round((value - control.minimum) / control.step)
                * control.step
            )
            value = max(control.minimum, min(control.maximum, value))
        try:
            _run_v4l2(
                ["--device", self.camera.path, f"--set-ctrl={name}={value}"]
            )
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            logger.exception(
                "Failed setting V4L2 control %s on %s", name, self.camera.path
            )
            return False
        control.value = value
        return True

    def _get_control(self, name: str) -> Optional[V4L2Control]:
        control = self._controls.get(name)
        if not self._connected or control is None or not control.usable:
            return None
        try:
            output = _run_v4l2(
                ["--device", self.camera.path, f"--get-ctrl={name}"]
            )
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            logger.exception(
                "Failed reading V4L2 control %s on %s", name, self.camera.path
            )
            return None
        match = re.search(rf"\b{re.escape(name)}\s*:\s*(-?\d+)", output)
        if match:
            control.value = int(match.group(1))
        return control

    def get_ptz_position(self) -> dict[str, Optional[int]]:
        position: dict[str, Optional[int]] = {
            "pan": None,
            "tilt": None,
            "zoom": None,
        }
        for axis in ("pan", "tilt"):
            control = self._get_control(f"{axis}_absolute")
            if control and control.maximum > control.minimum:
                position[axis] = round(
                    (control.value - control.minimum)
                    * 0xFFFF
                    / (control.maximum - control.minimum)
                )
        control = self._get_control("zoom_absolute")
        if control and control.maximum > control.minimum:
            position["zoom"] = round(
                (control.value - control.minimum)
                * 0xFFFF
                / (control.maximum - control.minimum)
            )
        return position

    @staticmethod
    def _speed(control: Optional[V4L2Control], speed: int) -> Optional[int]:
        if control is None:
            return None
        fraction = max(0.0, min(1.0, speed / 24.0))
        return round(
            control.minimum + fraction * (control.maximum - control.minimum)
        )

    def _move_axis(
        self, relative: str, absolute: str, move: int, speed: int
    ) -> bool:
        if not move:
            return True
        direction = 1 if move > 0 else -1
        amount = max(1, abs(move))
        speed_control = self._controls.get(
            relative.replace("_relative", "_speed")
        )
        speed_ok = True
        if speed_control and speed_control.usable:
            speed_ok = self._set_control(
                speed_control.name, self._speed(speed_control, speed)
            )

        relative_control = self._controls.get(relative)
        if relative_control and relative_control.usable:
            span = max(
                abs(relative_control.minimum), abs(relative_control.maximum)
            )
            units = max(
                relative_control.step,
                round(span * amount * max(1, speed) / 100.0 / 2400.0),
            )
            return self._set_control(relative, direction * units) and speed_ok

        current = self._get_control(absolute)
        if current is None:
            return False
        span = current.maximum - current.minimum
        delta = max(
            current.step, round(span * amount * max(1, speed) / 100.0 / 2400.0)
        )
        return (
            self._set_control(absolute, current.value + direction * delta)
            and speed_ok
        )

    def pan_tilt_relative(
        self, pan_speed: int, tilt_speed: int, pan_move: int, tilt_move: int
    ) -> bool:
        if not self._connected:
            return False
        pan_ok = self._move_axis(
            "pan_relative", "pan_absolute", pan_move, pan_speed
        )
        tilt_ok = self._move_axis(
            "tilt_relative", "tilt_absolute", tilt_move, tilt_speed
        )
        return pan_ok and tilt_ok

    def pan_tilt_stop(self) -> bool:
        if not self._connected:
            return False
        stopped = True
        for axis in ("pan", "tilt"):
            speed = self._controls.get(f"{axis}_speed")
            if speed and speed.usable:
                stopped = (
                    self._set_control(speed.name, speed.minimum) and stopped
                )
        return stopped

    def pan_tilt_absolute(
        self, pan_speed: int, tilt_speed: int, pan_pos: int, tilt_pos: int
    ) -> bool:
        if not self._connected:
            return False
        if pan_pos == 0 and tilt_pos == 0:
            success = True
            for axis in ("pan", "tilt"):
                control = self._controls.get(f"{axis}_absolute")
                if control and control.usable:
                    value = (control.minimum + control.maximum) // 2
                    success = (
                        self._set_control(control.name, value) and success
                    )
                else:
                    reset = self._controls.get(f"{axis}_reset")
                    if reset and reset.usable:
                        success = (
                            self._set_control(reset.name, reset.minimum)
                            and success
                        )
                    else:
                        success = False
            return success
        success = True
        for name, position, legacy_min, legacy_max in (
            ("pan_absolute", pan_pos, -2448, 2448),
            ("tilt_absolute", tilt_pos, -1296, 1296),
        ):
            control = self._controls.get(name)
            if control is None or not control.usable:
                success = False
                continue
            fraction = (position - legacy_min) / (legacy_max - legacy_min)
            value = round(
                control.minimum
                + fraction * (control.maximum - control.minimum)
            )
            success = self._set_control(name, value) and success
        return success

    def zoom_tele(self, speed: int) -> bool:
        return self._zoom_continuous(1, speed)

    def zoom_wide(self, speed: int) -> bool:
        return self._zoom_continuous(-1, speed)

    def _zoom_continuous(self, direction: int, speed: int) -> bool:
        speed_control = self._controls.get("zoom_speed")
        speed_ok = True
        if speed_control and speed_control.usable:
            speed_ok = self._set_control(
                speed_control.name, self._speed(speed_control, speed)
            )
        control = self._controls.get("zoom_continuous")
        if control and control.usable:
            return self._set_control(control.name, direction) and speed_ok
        relative = self._controls.get("zoom_relative")
        if relative and relative.usable:
            fraction = max(1, speed) / 24.0
            amount = max(
                relative.step,
                round(
                    max(abs(relative.minimum), abs(relative.maximum))
                    * fraction
                    / 24
                ),
            )
            return (
                self._set_control(relative.name, direction * amount)
                and speed_ok
            )
        return False

    def zoom_stop(self) -> bool:
        if not self._connected:
            return False
        control = self._controls.get("zoom_continuous")
        return (
            self._set_control(control.name, 0)
            if control and control.usable
            else True
        )

    def zoom_absolute(self, zoom_pos: int) -> bool:
        control = self._controls.get("zoom_absolute")
        if control is None:
            return False
        fraction = max(0, min(0xFFFF, zoom_pos)) / 0xFFFF
        value = round(
            control.minimum + fraction * (control.maximum - control.minimum)
        )
        return self._set_control(control.name, value)

    def focus_auto(self) -> bool:
        return self._set_control("focus_auto", 1)

    def focus_manual(self) -> bool:
        return self._set_control("focus_auto", 0)

    def focus_far(self, speed: int) -> bool:
        return self._move_axis(
            "focus_relative", "focus_absolute", speed, speed
        )

    def focus_near(self, speed: int) -> bool:
        return self._move_axis(
            "focus_relative", "focus_absolute", -speed, speed
        )

    def focus_stop(self) -> bool:
        return True

    def iris_open(self, speed: int) -> bool:
        return self._move_axis("iris_relative", "iris_absolute", speed, speed)

    def iris_close(self, speed: int) -> bool:
        return self._move_axis("iris_relative", "iris_absolute", -speed, speed)

    def iris_stop(self) -> bool:
        return True

    def white_balance_auto(self) -> bool:
        return self._set_control("white_balance_automatic", 1)

    def white_balance_indoor(self) -> bool:
        auto = self._controls.get("white_balance_automatic")
        auto_ok = (
            self._set_control(auto.name, 0) if auto and auto.usable else True
        )
        return self._set_control("white_balance_temperature", 3200) and auto_ok

    def white_balance_outdoor(self) -> bool:
        auto = self._controls.get("white_balance_automatic")
        auto_ok = (
            self._set_control(auto.name, 0) if auto and auto.usable else True
        )
        return self._set_control("white_balance_temperature", 5600) and auto_ok

    def exposure(self, value: int) -> bool:
        control = self._controls.get("exposure_absolute")
        if control is None:
            return False
        fraction = max(-12, min(12, value)) / 24.0 + 0.5
        return self._set_control(
            control.name,
            round(
                control.minimum
                + fraction * (control.maximum - control.minimum)
            ),
        )

    def contrast(self, value: int) -> bool:
        return self._set_normalized("contrast", value)

    def video_proc_amp(self, property_id: int, value: int) -> bool:
        name = {
            0: "brightness",
            1: "contrast",
            2: "hue",
            3: "saturation",
            4: "sharpness",
            5: "gamma",
            8: "backlight_compensation",
            9: "gain",
        }.get(property_id)
        return self._set_normalized(name, value) if name else False

    def _set_normalized(self, name: str, value: int) -> bool:
        control = self._controls.get(name)
        if control is None:
            return False
        fraction = max(0, min(100, value)) / 100.0
        return self._set_control(
            name,
            round(
                control.minimum
                + fraction * (control.maximum - control.minimum)
            ),
        )
