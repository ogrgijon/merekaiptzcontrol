"""
Preset Manager

PyQt6 widget for managing camera position presets.
"""

import json
import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (QGridLayout, QLabel, QMessageBox, QInputDialog,
                             QPushButton, QVBoxLayout, QWidget)

from src.app_paths import app_data_dir
from src.camera.camera_manager import CameraManager
from src.config.settings import Settings
from .i18n import translate

logger = logging.getLogger(__name__)


class PresetButton(QPushButton):
    rename_requested = pyqtSignal()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.rename_requested.emit()
            event.accept()
        else:
            super().mousePressEvent(event)


class PresetManager(QWidget):
    """Preset matrix: arm "Save Preset", then click a slot to store it."""

    restore_controls = pyqtSignal(dict)
    MAX_PRESETS = 8
    PRESET_FILE = app_data_dir() / "camera_presets.json"
    POSITION_STEP = 655

    def __init__(self, camera_manager: CameraManager, settings: Settings):
        super().__init__()

        self.camera_manager = camera_manager
        self.settings = settings
        self.presets = {}
        self.positions: dict[str, dict[str, int]] = {}
        self.slot_buttons = []
        self.MAX_PRESETS = settings.get("max_presets", 8)
        self.active_camera_key: Optional[str] = None
        self.capabilities: dict[str, bool] = {}
        self._relative_moves: list[tuple[int, int, int]] = []
        self._pending_position: Optional[dict[str, int]] = None
        self._pending_camera_key: Optional[str] = None
        self._movement_failed = False
        self._move_timer = QTimer(self)
        self._move_timer.setSingleShot(True)
        self._move_timer.timeout.connect(self._run_next_relative_move)
        self._stop_timer = QTimer(self)
        self._stop_timer.setSingleShot(True)
        self._stop_timer.timeout.connect(self._stop_and_continue_relative_move)
        self._persist_timer = QTimer(self)
        self._persist_timer.setSingleShot(True)
        self._persist_timer.timeout.connect(self._save_presets)
        self.control_panel = None

        self._init_ui()
        self._load_presets()

        logger.info("Preset manager initialized")

    def _tr(self, text: str) -> str:
        return translate(text, self.settings.get("language", "en"))

    def _display_preset_name(self, name: str, slot: int) -> str:
        if name == f"Preset {slot + 1}":
            return self._tr("Preset {number}").format(number=slot + 1)
        return name

    def retranslate(self) -> None:
        """Refresh text that is generated dynamically from the selected language."""
        self._on_save_mode_toggled(self.save_mode_btn.isChecked())
        self._update_slot_buttons()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.save_mode_btn = QPushButton("Save Preset")
        self.save_mode_btn.setCheckable(True)
        self.save_mode_btn.setToolTip(
            "Activate, then click a slot to save the current camera state there"
        )
        self.save_mode_btn.toggled.connect(self._on_save_mode_toggled)
        layout.addWidget(self.save_mode_btn)
        self.position_label = QLabel("X 32768   Y 32768   Z 0")
        self.position_label.setToolTip(
            "Camera position: pan (X), tilt (Y), zoom (Z); estimated when unreadable"
        )
        layout.addWidget(self.position_label)

        slot_grid = QGridLayout()
        for slot in range(self.MAX_PRESETS):
            button = PresetButton(f"{slot + 1}\n{self._tr('Empty')}")
            button.setMinimumHeight(42)
            button.clicked.connect(
                lambda checked=False, value=slot: self._on_slot_clicked(value)
            )
            button.setToolTip(
                self._tr("Preset {number}. Right-click to rename.").format(
                    number=slot + 1
                )
            )
            button.rename_requested.connect(
                lambda value=slot: self._rename_preset(value)
            )
            self.slot_buttons.append(button)
            slot_grid.addWidget(button, slot // 2, slot % 2)
        layout.addLayout(slot_grid)
        layout.addStretch()

    def _on_save_mode_toggled(self, active: bool) -> None:
        text = "Click a slot to save..." if active else "Save Preset"
        self.save_mode_btn.setText(self._tr(text))

    def _current_camera_key(self) -> str:
        return self.active_camera_key or self.camera_manager.active_camera or "default"

    def _on_slot_clicked(self, slot: int) -> None:
        """Save or recall a software camera-state preset."""
        camera = self.camera_manager.get_active_camera()
        if not camera:
            QMessageBox.warning(
                self,
                self._tr("No Camera Connected"),
                self._tr("Connect a camera first."),
            )
            return

        camera_key = self._current_camera_key()
        slot_key = f"slot_{slot}"
        if self.save_mode_btn.isChecked():
            hardware_preset = self.capabilities.get("presets", False)
            if hardware_preset and not camera.save_preset(slot):
                QMessageBox.warning(
                    self,
                    self._tr("Preset Failed"),
                    self._tr("The camera rejected this preset."),
                )
                return
            entry = self.presets.setdefault(
                slot_key, {"name": f"Preset {slot + 1}", "slot": slot}
            )
            camera_names = entry.setdefault("camera_names", {})
            if not isinstance(camera_names, dict):
                logger.warning("Replacing invalid camera-specific preset names")
                camera_names = {}
                entry["camera_names"] = camera_names
            if camera_key not in camera_names:
                camera_names[camera_key] = entry.get("name", f"Preset {slot + 1}")
            camera_states = entry.setdefault("camera_states", {})
            state = {
                "hardware_preset": hardware_preset,
                "controls": (
                    self.control_panel.saved_control_state()
                    if self.control_panel is not None
                    else {}
                ),
            }
            if not hardware_preset:
                state["position"] = self._read_current_position(
                    camera, camera_key
                )
            camera_states[camera_key] = state
            self._update_slot_buttons()
            self._save_presets()
            self.save_mode_btn.setChecked(False)
        else:
            entry = self.presets.get(slot_key, {})
            state = entry.get("camera_states", {}).get(camera_key)
            if state:
                if state.get("hardware_preset"):
                    if not camera.goto_preset(slot):
                        QMessageBox.warning(
                            self,
                            self._tr("Preset Failed"),
                            self._tr("The camera rejected this preset."),
                        )
                    else:
                        self.restore_controls.emit(state.get("controls", {}))
                else:
                    self._recall_state(camera, camera_key, state)
            elif self.capabilities.get("presets", False):
                if not camera.goto_preset(slot):
                    QMessageBox.warning(
                        self,
                        self._tr("Preset Failed"),
                        self._tr("The camera rejected this preset."),
                    )
            else:
                QMessageBox.information(
                    self,
                    self._tr("Preset Empty"),
                    self._tr(
                        "Save a software preset to this slot before recalling it."
                    ),
                )

    def _update_slot_buttons(self) -> None:
        camera_key = self._current_camera_key()
        for slot, button in enumerate(self.slot_buttons):
            saved = self.presets.get(f"slot_{slot}", {})
            camera_names = saved.get("camera_names", {})
            name = (
                camera_names.get(camera_key)
                if isinstance(camera_names, dict)
                else None
            )
            if not isinstance(name, str) or not name.strip():
                name = saved.get("name", self._tr("Empty"))
            display_name = self._display_preset_name(name, slot)
            button.setText(f"{slot + 1}: {display_name}")
            button.setToolTip(
                self._tr("{name}. Right-click to rename.").format(
                    name=display_name
                )
            )

    def _rename_preset(self, slot: int) -> None:
        slot_key = f"slot_{slot}"
        entry = self.presets.setdefault(
            slot_key, {"name": f"Preset {slot + 1}", "slot": slot}
        )
        camera_key = self._current_camera_key()
        camera_names = entry.setdefault("camera_names", {})
        if not isinstance(camera_names, dict):
            logger.warning("Replacing invalid camera-specific preset names")
            camera_names = {}
            entry["camera_names"] = camera_names
        current_name = (
            camera_names.get(camera_key)
            if isinstance(camera_names, dict)
            else None
        )
        if not isinstance(current_name, str) or not current_name.strip():
            current_name = entry.get("name", f"Preset {slot + 1}")
        current_name = self._display_preset_name(current_name, slot)
        name, accepted = QInputDialog.getText(
            self,
            self._tr("Rename Preset"),
            self._tr("Preset name:"),
            text=current_name,
        )
        if not accepted:
            return
        name = name.strip()
        if not name:
            QMessageBox.warning(
                self,
                self._tr("Invalid Preset Name"),
                self._tr("The preset name cannot be empty."),
            )
            return
        camera_names[camera_key] = name
        self._update_slot_buttons()
        self._save_presets()

    def apply_capabilities(
        self, capabilities: dict[str, bool], camera_key: Optional[str] = None
    ) -> None:
        """Enable software presets when the selected camera can move."""
        next_camera_key = camera_key or self.camera_manager.active_camera
        if next_camera_key != self.active_camera_key:
            old_camera = (
                self.camera_manager.get_camera(self.active_camera_key)
                if self.active_camera_key
                else None
            )
            self._cancel_relative_moves(old_camera)
        self.capabilities = dict(capabilities)
        self.active_camera_key = next_camera_key
        if self.active_camera_key:
            self._read_current_position(
                self.camera_manager.get_active_camera(), self.active_camera_key
            )
        supported = any(
            capabilities.get(name, False)
            for name in ("pan_tilt", "zoom", "presets")
        )
        self.save_mode_btn.setEnabled(supported)
        for button in self.slot_buttons:
            button.setEnabled(supported)
        if not supported:
            self.save_mode_btn.setChecked(False)
        self._update_slot_buttons()

    def track_control_change(self, key: str, value: object) -> None:
        """Update the software estimate from commands sent by the control panel."""
        camera_key = self.active_camera_key
        if not camera_key:
            return
        if key in {"reset_ptz", "zoom_default"}:
            camera = self.camera_manager.get_active_camera()
            if not camera:
                return
            position = self._read_current_position(camera, camera_key)
            if key == "reset_ptz":
                axes = []
                if self.capabilities.get("pan_tilt", False):
                    axes.extend(("x", "y"))
                if self.capabilities.get("zoom", False):
                    axes.append("z")
                target_position = {
                    "x": 0x8000 if self.capabilities.get("pan_tilt", False) else position["x"],
                    "y": 0x8000 if self.capabilities.get("pan_tilt", False) else position["y"],
                    "z": 0 if self.capabilities.get("zoom", False) else position["z"],
                }
            else:
                axes = ["z"]
                target_position = {
                    **position,
                    "z": self._clamp_position(int(value or 0)),
                }
            self._recall_state(
                camera,
                camera_key,
                {"position": target_position, "controls": {}, "axes": axes},
            )
            return
        position = self.positions.setdefault(camera_key, self._center_position())
        if key == "ptz_delta" and isinstance(value, tuple) and len(value) == 2:
            x_direction, y_direction = value
            position["x"] = self._clamp_position(
                position["x"] + int(x_direction) * self.POSITION_STEP
            )
            position["y"] = self._clamp_position(
                position["y"] + int(y_direction) * self.POSITION_STEP
            )
        elif key == "ptz_home":
            position["x"] = 0x8000
            position["y"] = 0x8000
        elif key == "zoom_delta":
            position["z"] = self._clamp_position(
                position["z"] + int(value) * self.POSITION_STEP
            )
        elif key == "zoom":
            position["z"] = self._clamp_position(int(value))
        else:
            return
        self._persist_timer.start(500)

    def _read_current_position(
        self, camera, camera_key: str
    ) -> dict[str, int]:
        position = self.positions.setdefault(camera_key, self._center_position())
        getter = getattr(camera, "get_ptz_position", None) if camera else None
        if callable(getter):
            actual = getter()
            for axis, coordinate in (("pan", "x"), ("tilt", "y"), ("zoom", "z")):
                value = actual.get(axis)
                if value is not None:
                    position[coordinate] = self._clamp_position(int(value))
        self._update_position_label(position)
        return dict(position)

    @staticmethod
    def _center_position() -> dict[str, int]:
        return {"x": 0x8000, "y": 0x8000, "z": 0}

    @staticmethod
    def _clamp_position(value: int) -> int:
        return max(0, min(0xFFFF, value))

    def _update_position_label(self, position: dict[str, int]) -> None:
        self.position_label.setText(
            f"X {position['x']}   Y {position['y']}   Z {position['z']}"
        )

    def _recall_state(self, camera, camera_key: str, state: dict) -> None:
        self._cancel_relative_moves(camera)
        target = state.get("position", {})
        current = self._read_current_position(camera, camera_key)
        target_position = {
            axis: self._clamp_position(int(target.get(axis, current[axis])))
            for axis in ("x", "y", "z")
        }
        self.restore_controls.emit(state.get("controls", {}))
        self._movement_failed = False

        axes = set(state.get("axes", ("x", "y", "z")))
        pan_tilt_supported = self.capabilities.get("pan_tilt", False)
        move_pan_tilt = pan_tilt_supported and bool(axes & {"x", "y"})
        target_is_centered = (
            target_position["x"] == 0x8000 and target_position["y"] == 0x8000
        )
        centered_with_home = (
            move_pan_tilt
            and target_is_centered
            and self.capabilities.get("pan_tilt_home", False)
            and camera.pan_tilt_absolute(1, 1, 0, 0)
        )
        if centered_with_home:
            pass
        elif move_pan_tilt and self.capabilities.get(
            "pan_tilt_absolute", False
        ):
            pan = round(target_position["x"] * 4896 / 0xFFFF - 2448)
            tilt = round(target_position["y"] * 2592 / 0xFFFF - 1296)
            if not camera.pan_tilt_absolute(1, 1, pan, tilt):
                logger.warning("Absolute pan/tilt preset recall failed")
                self._movement_failed = True
        elif move_pan_tilt:
            x_steps = round(
                (target_position["x"] - current["x"]) / self.POSITION_STEP
            )
            y_steps = round(
                (target_position["y"] - current["y"]) / self.POSITION_STEP
            )
            self._queue_relative_steps(x_steps, y_steps, 0)

        zoom_supported = self.capabilities.get("zoom", False) and "z" in axes
        if zoom_supported and self.capabilities.get("zoom_absolute", False):
            if not camera.zoom_absolute(target_position["z"]):
                logger.warning("Absolute zoom preset recall failed")
                self._movement_failed = True
        elif zoom_supported:
            z_steps = round(
                (target_position["z"] - current["z"]) / self.POSITION_STEP
            )
            self._queue_relative_steps(0, 0, z_steps)

        if not self._relative_moves:
            if self._movement_failed:
                self._show_movement_failure()
            else:
                self.positions[camera_key] = target_position
                self._update_position_label(target_position)
                self._save_presets()
        else:
            if not self._movement_failed:
                self._pending_position = target_position
                self._pending_camera_key = camera_key
            self._move_timer.start(0)

    def _queue_relative_steps(self, x_steps: int, y_steps: int, z_steps: int) -> None:
        step_count = max(abs(x_steps), abs(y_steps), abs(z_steps))
        for step in range(step_count):
            self._relative_moves.append(
                (
                    (1 if x_steps > 0 else -1) if step < abs(x_steps) else 0,
                    (1 if y_steps > 0 else -1) if step < abs(y_steps) else 0,
                    (1 if z_steps > 0 else -1) if step < abs(z_steps) else 0,
                )
            )

    def _run_next_relative_move(self) -> None:
        if not self._relative_moves:
            if self._movement_failed:
                self._show_movement_failure()
            elif self._pending_position is not None and self._pending_camera_key:
                self.positions[self._pending_camera_key] = self._pending_position
                self._update_position_label(self._pending_position)
                self._pending_position = None
                self._pending_camera_key = None
                self._save_presets()
            return

        camera = self.camera_manager.get_active_camera()
        if not camera:
            self._relative_moves.clear()
            self._pending_position = None
            self._pending_camera_key = None
            return

        x_direction, y_direction, z_direction = self._relative_moves.pop(0)
        if x_direction or y_direction:
            speed = (
                self.control_panel.pan_tilt_speed_spin.value()
                if self.control_panel is not None
                else 15
            )
            if not camera.pan_tilt_relative(
                speed, speed, x_direction * 100, y_direction * 100
            ):
                logger.warning("Relative pan/tilt preset movement failed")
                self._movement_failed = True
        if z_direction > 0:
            if not camera.zoom_tele(7):
                logger.warning("Relative zoom-in preset movement failed")
                self._movement_failed = True
        elif z_direction < 0:
            if not camera.zoom_wide(7):
                logger.warning("Relative zoom-out preset movement failed")
                self._movement_failed = True
        self._stop_timer.start(100)

    def _stop_and_continue_relative_move(self) -> None:
        camera = self.camera_manager.get_active_camera()
        if camera:
            if self.capabilities.get("pan_tilt", False):
                camera.pan_tilt_stop()
            if self.capabilities.get("zoom", False):
                camera.zoom_stop()
        self._move_timer.start(50)

    def _cancel_relative_moves(self, camera) -> None:
        if (self._relative_moves or self._stop_timer.isActive()) and camera:
            if self.capabilities.get("pan_tilt", False):
                camera.pan_tilt_stop()
            if self.capabilities.get("zoom", False):
                camera.zoom_stop()
        self._move_timer.stop()
        self._stop_timer.stop()
        self._relative_moves.clear()
        self._pending_position = None
        self._pending_camera_key = None
        self._movement_failed = False

    def _show_movement_failure(self) -> None:
        self._movement_failed = False
        self._pending_position = None
        self._pending_camera_key = None
        QMessageBox.warning(
            self,
            self._tr("Preset Recall Incomplete"),
            self._tr("The camera rejected one or more position commands."),
        )

    def _load_presets(self) -> None:
        try:
            preset_file = Path(self.PRESET_FILE)
            if preset_file.exists():
                with open(preset_file, 'r') as f:
                    saved = json.load(f)
                if "presets" in saved:
                    self.presets = saved.get("presets", {})
                    self.positions = saved.get("positions", {})
                else:
                    self.presets = {
                        key: value
                        for key, value in saved.items()
                        if key.startswith("slot_")
                    }
                self._update_slot_buttons()
                logger.info(f"Loaded {len(self.presets)} preset(s)")
        except Exception as e:
            logger.error(f"Failed to load presets: {e}")

    def _save_presets(self) -> None:
        try:
            preset_file = Path(self.PRESET_FILE)
            preset_file.parent.mkdir(parents=True, exist_ok=True)
            with open(preset_file, 'w') as f:
                json.dump(
                    {"presets": self.presets, "positions": self.positions},
                    f,
                    indent=2,
                )
            logger.info(f"Saved {len(self.presets)} preset(s)")
        except Exception as e:
            logger.error(f"Failed to save presets: {e}")
