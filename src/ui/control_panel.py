"""
Camera Control Panel

PyQt6 widget for controlling camera functions.
"""

import logging
from typing import Optional

from PyQt6.QtCore import QSignalBlocker, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import (QButtonGroup, QDial, QDoubleSpinBox, QGridLayout,
                             QGroupBox, QHBoxLayout, QInputDialog, QLabel,
                             QMessageBox, QMenu, QPushButton, QRadioButton,
                             QSizePolicy, QSlider, QSpinBox, QStackedWidget,
                             QVBoxLayout, QWidget)

from src.camera.camera_manager import CameraManager
from src.config.settings import Settings
from .i18n import translate

from .auto_repeat_button import AutoRepeatButton

logger = logging.getLogger(__name__)

_DEFAULT_SUMMARY_LABELS = {
    "iris": "Iris",
    "white_balance": "WB",
    "exposure": "Exposure",
    "contrast": "Contrast",
    "brightness": "Brightness",
    "saturation": "Saturation",
    "sharpness": "Sharpness",
    "gamma": "Gamma",
    "hue": "Hue",
    "gain": "Gain",
    "backlight": "Backlight",
}


class PanTiltJoystick(QWidget):
    """Mouse-driven joystick that emits normalized pan/tilt movement."""

    movement_changed = pyqtSignal(int, int)
    released = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(88, 88)
        self.setMaximumSize(100, 100)
        self.setEnabled(False)
        self._position = (0, 0)

    def _update_position(self, event: QMouseEvent) -> None:
        center = self.rect().center()
        radius = min(self.width(), self.height()) / 2 - 12
        dx = event.position().x() - center.x()
        dy = event.position().y() - center.y()
        distance = min((dx * dx + dy * dy) ** 0.5, radius)
        if distance:
            scale = distance / (dx * dx + dy * dy) ** 0.5
            dx *= scale
            dy *= scale
        pan = round(dx / radius * 100)
        tilt = round(-dy / radius * 100)
        self._position = (pan, tilt)
        self.movement_changed.emit(pan, tilt)
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._update_position(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._update_position(event)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._position = (0, 0)
            self.released.emit()
            self.update()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = self.rect().center()
        radius = min(self.width(), self.height()) / 2 - 12
        painter.setPen(QPen(Qt.GlobalColor.gray, 2))
        painter.setBrush(Qt.GlobalColor.lightGray)
        painter.drawEllipse(center, int(radius), int(radius))
        painter.setPen(QPen(Qt.GlobalColor.darkGray, 1))
        painter.drawLine(center.x() - int(radius), center.y(), center.x() + int(radius), center.y())
        painter.drawLine(center.x(), center.y() - int(radius), center.x(), center.y() + int(radius))
        pan, tilt = self._position
        knob_x = center.x() + round(pan * radius / 100)
        knob_y = center.y() - round(tilt * radius / 100)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        painter.setBrush(Qt.GlobalColor.darkCyan)
        painter.drawEllipse(knob_x - 12, knob_y - 12, 24, 24)


class SettingSummaryButton(QPushButton):
    context_menu_requested = pyqtSignal(object)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.context_menu_requested.emit(event.globalPosition().toPoint())
            event.accept()
        elif self.property("matrix_disabled"):
            event.accept()
        else:
            super().mousePressEvent(event)


class ControlPanel(QWidget):
    """Camera control panel widget."""
    
    # Signals
    control_changed = pyqtSignal(str, object)
    
    def __init__(self, camera_manager: CameraManager, settings: Settings):
        """
        Initialize control panel.
        
        Args:
            camera_manager: Camera manager instance
            settings: Settings manager instance
        """
        super().__init__()
        
        self.camera_manager = camera_manager
        self.settings = settings
        self.enabled = False
        
        self._init_ui()
        self._connect_signals()
        self._apply_settings()
        self.retranslate()
        
        logger.info("Control panel initialized")

    def _tr(self, text: str) -> str:
        return translate(text, self.settings.get("language", "en"))

    def _display_summary_label(self, key: str) -> str:
        label = self._summary_labels.get(key, _DEFAULT_SUMMARY_LABELS.get(key, key))
        if label == _DEFAULT_SUMMARY_LABELS.get(key):
            return self._tr(label)
        return label

    def retranslate(self) -> None:
        """Refresh dynamic setting names after a language change."""
        self.settings_group.setTitle(self._tr("Camera Settings"))
        for key in self._summary_buttons:
            self._refresh_summary(key)
        selected = getattr(self, "_selected_setting", None)
        if selected:
            self._select_setting(selected)

    def _init_ui(self) -> None:
        """Initialize user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Pan/Tilt Control
        pan_tilt_group = self._create_pan_tilt_group()
        layout.addWidget(pan_tilt_group)
        
        # Zoom Control
        zoom_group = self._create_zoom_group()
        layout.addWidget(zoom_group)
        
        # Focus Control
        focus_group = self._create_focus_group()
        layout.addWidget(focus_group)
        
        # Iris Control
        iris_group = self._create_iris_group()
        layout.addWidget(iris_group)
        
        # White Balance Control
        wb_group = self._create_white_balance_group()
        layout.addWidget(wb_group)
        
        # Exposure Control
        exposure_group = self._create_exposure_group()
        layout.addWidget(exposure_group)

        image_group = self._create_image_group()
        layout.addWidget(image_group)
        
        layout.addStretch()
    
    def _create_pan_tilt_group(self) -> QGroupBox:
        """Create pan/tilt control group."""
        group = QGroupBox("Pan/Tilt Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout(group)
        
        # Speed controls
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.pan_tilt_speed_spin = QSpinBox()
        self.pan_tilt_speed_spin.setRange(1, 24)
        self.pan_tilt_speed_spin.setValue(15)
        speed_layout.addWidget(self.pan_tilt_speed_spin)
        speed_layout.addStretch()
        layout.addLayout(speed_layout, 0, 0, 1, 3)
        
        self.pan_tilt_joystick = PanTiltJoystick()
        self.pan_home_btn = self._create_control_button("HOME", 24)
        layout.addWidget(self.pan_tilt_joystick, 1, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.pan_home_btn, 2, 1)
        
        self.pan_home_btn.clicked.connect(
            lambda: self._send_pan_tilt_home()
        )
        self.pan_tilt_joystick.movement_changed.connect(self._send_pan_tilt)
        self.pan_tilt_joystick.released.connect(self._send_pan_tilt_stop)
        
        return group

    def _create_image_group(self) -> QGroupBox:
        """Create standard DirectShow image controls."""
        group = QGroupBox("Image Controls")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout = QGridLayout(group)
        self.image_dials = {}
        controls = (
            ("Brightness", "brightness"),
            ("Color intensity", "saturation"),
            ("Sharpness", "sharpness"),
            ("Gamma", "gamma"),
            ("Hue", "hue"),
            ("Gain", "gain"),
            ("Backlight", "backlight"),
        )
        for row, (label, capability) in enumerate(controls):
            dial = QDial()
            dial.setMinimumSize(72, 72)
            dial.setMaximumSize(82, 82)
            dial.setRange(0, 100)
            dial.setValue(50)
            dial.setNotchesVisible(True)
            dial.valueChanged.connect(
                lambda value, name=capability: self._send_video_control(name, value)
            )
            self.image_dials[capability] = dial
            layout.addWidget(QLabel(f"{label}:"), row // 2, (row % 2) * 2)
            layout.addWidget(dial, row // 2, (row % 2) * 2 + 1)
        return group
    
    def _create_zoom_group(self) -> QGroupBox:
        """Create zoom control group."""
        group = QGroupBox("Zoom Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout(group)
        
        self.zoom_wide_btn = self._create_auto_repeat_button("◄ WIDE (Out)")
        self.zoom_tele_btn = self._create_auto_repeat_button("TELE (In) ►")
        self.zoom_stop_btn = self._create_control_button("STOP")
        
        layout.addWidget(QLabel("Zoom:"), 0, 0)
        layout.addWidget(self.zoom_wide_btn, 0, 1)
        
        layout.addWidget(QLabel("Zoom Position:"), 1, 0)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(0, 0xFFFF)
        self.zoom_slider.setValue(0)
        self.zoom_slider.sliderMoved.connect(
            lambda: self._send_zoom_absolute(self.zoom_slider.value())
        )
        layout.addWidget(self.zoom_slider, 1, 1)
        
        layout.addWidget(self.zoom_tele_btn, 2, 0)
        layout.addWidget(self.zoom_stop_btn, 2, 1)
        
        # Connect signals
        self.zoom_wide_btn.pressed.connect(
            lambda: self._send_zoom_wide(7)
        )
        self.zoom_wide_btn.repeating.connect(
            lambda: self._send_zoom_wide(7)
        )
        self.zoom_wide_btn.released.connect(self._send_zoom_stop)
        
        self.zoom_tele_btn.pressed.connect(
            lambda: self._send_zoom_tele(7)
        )
        self.zoom_tele_btn.repeating.connect(
            lambda: self._send_zoom_tele(7)
        )
        self.zoom_tele_btn.released.connect(self._send_zoom_stop)
        
        self.zoom_stop_btn.clicked.connect(
            lambda: self._send_zoom_stop()
        )
        
        return group
    
    def _create_focus_group(self) -> QGroupBox:
        """Create focus control group."""
        group = QGroupBox("Focus Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout(group)
        
        self.focus_auto_btn = self._create_control_button("Auto Focus")
        self.focus_manual_btn = self._create_control_button("Manual Focus")
        self.focus_near_btn = self._create_auto_repeat_button("◄ NEAR")
        self.focus_far_btn = self._create_auto_repeat_button("FAR ►")
        self.focus_stop_btn = self._create_control_button("STOP")
        
        layout.addWidget(QLabel("Focus:"), 0, 0, 1, 2)
        layout.addWidget(self.focus_auto_btn, 1, 0)
        layout.addWidget(self.focus_manual_btn, 1, 1)
        layout.addWidget(self.focus_near_btn, 2, 0)
        layout.addWidget(self.focus_far_btn, 2, 1)
        layout.addWidget(self.focus_stop_btn, 3, 0, 1, 2)
        
        # Connect signals
        self.focus_auto_btn.clicked.connect(
            lambda: self._send_focus_auto()
        )
        self.focus_manual_btn.clicked.connect(
            lambda: self._send_focus_manual()
        )
        
        self.focus_near_btn.clicked.connect(
            lambda: self._send_focus_near(5)
        )
        self.focus_near_btn.repeating.connect(
            lambda: self._send_focus_near(5)
        )
        self.focus_near_btn.released.connect(self._send_focus_stop)
        
        self.focus_far_btn.clicked.connect(
            lambda: self._send_focus_far(5)
        )
        self.focus_far_btn.repeating.connect(
            lambda: self._send_focus_far(5)
        )
        self.focus_far_btn.released.connect(self._send_focus_stop)
        
        self.focus_stop_btn.clicked.connect(
            lambda: self._send_focus_stop()
        )
        
        return group
    
    def _create_iris_group(self) -> QGroupBox:
        """Create iris control group."""
        group = QGroupBox("Iris Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout(group)
        
        self.iris_open_btn = self._create_auto_repeat_button("◄ OPEN (Bright)")
        self.iris_close_btn = self._create_auto_repeat_button("CLOSE (Dark) ►")
        self.iris_stop_btn = self._create_control_button("STOP")
        
        layout.addWidget(QLabel("Iris:"), 0, 0)
        layout.addWidget(self.iris_open_btn, 0, 1)
        
        layout.addWidget(QLabel("Iris Level:"), 1, 0)
        self.iris_slider = QSlider(Qt.Orientation.Horizontal)
        self.iris_slider.setRange(0, 100)
        self.iris_slider.setValue(50)
        layout.addWidget(self.iris_slider, 1, 1)
        
        layout.addWidget(self.iris_close_btn, 2, 0)
        layout.addWidget(self.iris_stop_btn, 2, 1)
        
        # Connect signals
        self.iris_open_btn.clicked.connect(
            lambda: self._send_iris_open(5)
        )
        self.iris_open_btn.repeating.connect(
            lambda: self._send_iris_open(5)
        )
        self.iris_open_btn.released.connect(self._send_iris_stop)
        
        self.iris_close_btn.clicked.connect(
            lambda: self._send_iris_close(5)
        )
        self.iris_close_btn.repeating.connect(
            lambda: self._send_iris_close(5)
        )
        self.iris_close_btn.released.connect(self._send_iris_stop)
        
        self.iris_stop_btn.clicked.connect(
            lambda: self._send_iris_stop()
        )
        
        return group
    
    def _create_white_balance_group(self) -> QGroupBox:
        """Create white balance control group."""
        group = QGroupBox("White Balance")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout(group)
        
        layout.addWidget(QLabel("Mode:"), 0, 0, 1, 3)
        
        self.wb_auto_btn = self._create_control_button("Auto")
        self.wb_indoor_btn = self._create_control_button("Indoor")
        self.wb_outdoor_btn = self._create_control_button("Outdoor")
        
        layout.addWidget(self.wb_auto_btn, 1, 0)
        layout.addWidget(self.wb_indoor_btn, 1, 1)
        layout.addWidget(self.wb_outdoor_btn, 1, 2)
        
        # Connect signals
        self.wb_auto_btn.clicked.connect(
            lambda: self._send_white_balance_auto()
        )
        self.wb_indoor_btn.clicked.connect(
            lambda: self._send_white_balance_indoor()
        )
        self.wb_outdoor_btn.clicked.connect(
            lambda: self._send_white_balance_outdoor()
        )
        
        return group
    
    def _create_exposure_group(self) -> QGroupBox:
        """Create exposure control group."""
        group = QGroupBox("Exposure Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout(group)
        
        layout.addWidget(QLabel("Exposure:"), 0, 0)
        
        self.exposure_dial = QDial()
        self.exposure_dial.setMinimumSize(72, 72)
        self.exposure_dial.setMaximumSize(82, 82)
        self.exposure_dial.setRange(-12, 12)
        self.exposure_dial.setValue(0)
        self.exposure_dial.setNotchesVisible(True)
        layout.addWidget(self.exposure_dial, 1, 0)
        
        self.exposure_value_label = QLabel("0.0")
        layout.addWidget(self.exposure_value_label, 2, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(QLabel("Contrast:"), 0, 1)
        self.contrast_dial = QDial()
        self.contrast_dial.setMinimumSize(72, 72)
        self.contrast_dial.setMaximumSize(82, 82)
        self.contrast_dial.setRange(0, 100)
        self.contrast_dial.setValue(50)
        self.contrast_dial.setNotchesVisible(True)
        layout.addWidget(self.contrast_dial, 1, 1)
        
        self.exposure_dial.valueChanged.connect(
            lambda: self.exposure_value_label.setText(
                f"{self.exposure_dial.value() * 0.5:.1f}"
            )
        )
        self.exposure_dial.valueChanged.connect(
            lambda value: self._send_exposure(value)
        )
        self.contrast_dial.valueChanged.connect(
            lambda value: self._send_contrast(value)
        )
        
        return group
    
    def _create_control_button(self, text: str, min_width: int = 80) -> QPushButton:
        """Create a control button with standard styling."""
        btn = QPushButton(text)
        btn.setMinimumWidth(min_width)
        btn.setEnabled(False)
        return btn
    
    def _create_auto_repeat_button(self, text: str, min_width: int = 80) -> AutoRepeatButton:
        """Create an auto-repeat button."""
        btn = AutoRepeatButton(text)
        btn.setMinimumWidth(min_width)
        btn.setEnabled(False)
        btn.set_auto_repeat(True)
        return btn
    
    def _connect_signals(self) -> None:
        """Connect internal signals and slots."""
        pass
    
    def _apply_settings(self) -> None:
        """Apply settings to controls."""
        # Configure auto-repeat timings
        initial_delay = self.settings.get("auto_repeat_initial_delay", 500)
        repeat_interval = self.settings.get("auto_repeat_delay", 50)
        
        for btn in self.findChildren(AutoRepeatButton):
            btn.set_repeat_delays(initial_delay, repeat_interval)
    
    def update_settings(self, new_settings: dict) -> None:
        """Update panel settings."""
        if "auto_repeat_initial_delay" in new_settings or "auto_repeat_delay" in new_settings:
            self._apply_settings()
    
    def _send_pan_tilt(self, pan_move: int, tilt_move: int) -> None:
        """Send pan/tilt command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            speed = self.pan_tilt_speed_spin.value()
            camera.pan_tilt_relative(speed, speed, pan_move, tilt_move)
    
    def _send_pan_tilt_stop(self) -> None:
        """Send pan/tilt stop command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.pan_tilt_stop()
    
    def _send_pan_tilt_home(self) -> None:
        """Send pan/tilt home command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.pan_tilt_absolute(1, 1, 0, 0)
    
    def _send_zoom_absolute(self, position: int) -> None:
        """Send absolute zoom command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.zoom_absolute(position)
    
    def _send_zoom_tele(self, speed: int) -> None:
        """Send zoom telephoto command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.zoom_tele(speed)
    
    def _send_zoom_wide(self, speed: int) -> None:
        """Send zoom wide command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.zoom_wide(speed)
    
    def _send_zoom_stop(self) -> None:
        """Send zoom stop command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.zoom_stop()
    
    def _send_focus_auto(self) -> None:
        """Send autofocus command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_auto()
    
    def _send_focus_manual(self) -> None:
        """Send manual focus command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_manual()
    
    def _send_focus_near(self, speed: int) -> None:
        """Send focus near command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_near(speed)
    
    def _send_focus_far(self, speed: int) -> None:
        """Send focus far command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_far(speed)
    
    def _send_focus_stop(self) -> None:
        """Send focus stop command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_stop()
    
    def _send_iris_open(self, speed: int) -> None:
        """Send iris open command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.iris_open(speed)
    
    def _send_iris_close(self, speed: int) -> None:
        """Send iris close command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.iris_close(speed)
    
    def _send_iris_stop(self) -> None:
        """Send iris stop command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.iris_stop()
    
    def _send_white_balance_auto(self) -> None:
        """Send auto white balance command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.white_balance_auto()
    
    def _send_white_balance_indoor(self) -> None:
        """Send indoor white balance command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.white_balance_indoor()
    
    def _send_white_balance_outdoor(self) -> None:
        """Send outdoor white balance command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.white_balance_outdoor()

    def _send_exposure(self, value: int) -> None:
        """Send exposure compensation to the active DirectShow camera."""
        if not self.enabled:
            return
        camera = self.camera_manager.get_active_camera()
        if camera and hasattr(camera, "exposure"):
            camera.exposure(value)

    def _send_contrast(self, value: int) -> None:
        """Send contrast value to the active DirectShow camera."""
        if not self.enabled:
            return
        camera = self.camera_manager.get_active_camera()
        if camera and hasattr(camera, "contrast"):
            camera.contrast(value)

    def _send_video_control(self, name: str, value: int) -> None:
        """Send a standard DirectShow video-processing value."""
        property_ids = {
            "brightness": 0,
            "contrast": 1,
            "hue": 2,
            "saturation": 3,
            "sharpness": 4,
            "gamma": 5,
            "backlight": 8,
            "gain": 9,
        }
        camera = self.camera_manager.get_active_camera()
        property_id = property_ids.get(name)
        if self.enabled and camera and property_id is not None:
            if hasattr(camera, "video_proc_amp"):
                camera.video_proc_amp(property_id, value)
    
    def enable_controls(self) -> None:
        """Enable all controls."""
        self.enabled = True
        for child in self.findChildren((QPushButton, AutoRepeatButton)):
            child.setEnabled(True)
        for child in self.findChildren((QSlider, QDial, PanTiltJoystick)):
            child.setEnabled(True)
        for child in self.findChildren(QSpinBox):
            child.setEnabled(True)

    def apply_capabilities(self, capabilities: dict[str, bool]) -> None:
        """Disable CCU sections that the active transport cannot control."""
        section_capabilities = {
            "Pan/Tilt Control": "pan_tilt",
            "Zoom Control": "zoom",
            "Focus Control": "focus",
            "Iris Control": "iris",
            "White Balance": "white_balance",
            "Exposure Control": "exposure",
            "Image Controls": None,
        }
        for group in self.findChildren(QGroupBox):
            capability = section_capabilities.get(group.title())
            if capability is not None:
                if capability == "exposure":
                    exposure_supported = capabilities.get("exposure", False)
                    contrast_supported = capabilities.get("contrast", False)
                    group.setEnabled(exposure_supported or contrast_supported)
                    self.exposure_dial.setEnabled(exposure_supported)
                    self.contrast_dial.setEnabled(contrast_supported)
                else:
                    group.setEnabled(capabilities.get(capability, False))
            elif group.title() == "Image Controls":
                for name, dial in self.image_dials.items():
                    dial.setEnabled(capabilities.get(name, False))
                group.setEnabled(any(
                    capabilities.get(name, False) for name in self.image_dials
                ))
    
    def disable_controls(self) -> None:
        """Disable all controls."""
        self.enabled = False
        for child in self.findChildren((QPushButton, AutoRepeatButton)):
            child.setEnabled(False)
        for child in self.findChildren((QSlider, QDial, PanTiltJoystick)):
            child.setEnabled(False)
        for child in self.findChildren(QSpinBox):
            child.setEnabled(False)

        return
        
        # Pan/Tilt Control
        pan_tilt_group = self._create_pan_tilt_group()
        layout.addWidget(pan_tilt_group)
        
        # Zoom Control
        zoom_group = self._create_zoom_group()
        layout.addWidget(zoom_group)
        
        # Focus Control
        focus_group = self._create_focus_group()
        layout.addWidget(focus_group)
        
        # Iris Control
        iris_group = self._create_iris_group()
        layout.addWidget(iris_group)
        
        # White Balance Control
        wb_group = self._create_white_balance_group()
        layout.addWidget(wb_group)
        
        # Exposure Control
        exposure_group = self._create_exposure_group()
        layout.addWidget(exposure_group)
        
        layout.addStretch()
    
    def _create_pan_tilt_group(self) -> QGroupBox:
        """Create pan/tilt control group."""
        group = QGroupBox("Pan/Tilt Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QGridLayout(group)
        
        # Speed controls
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.pan_tilt_speed_spin = QSpinBox()
        self.pan_tilt_speed_spin.setRange(1, 24)
        self.pan_tilt_speed_spin.setValue(15)
        speed_layout.addWidget(self.pan_tilt_speed_spin)
        speed_layout.addStretch()
        layout.addLayout(speed_layout, 0, 0, 1, 3)
        
        # Direction buttons (simplified 8-way control)
        self.pan_up_btn = self._create_auto_repeat_button("▲ UP", 24)
        self.pan_down_btn = self._create_auto_repeat_button("▼ DOWN", 24)
        self.pan_left_btn = self._create_auto_repeat_button("◄ LEFT", 24)
        self.pan_right_btn = self._create_auto_repeat_button("► RIGHT", 24)
        self.pan_home_btn = self._create_control_button("HOME", 24)
        
        # Arrow layout (cross pattern)
        arrow_layout = QGridLayout()
        arrow_layout.addWidget(self.pan_up_btn, 0, 1)
        arrow_layout.addWidget(self.pan_left_btn, 1, 0)
        arrow_layout.addWidget(self.pan_home_btn, 1, 1)
        arrow_layout.addWidget(self.pan_right_btn, 1, 2)
        arrow_layout.addWidget(self.pan_down_btn, 2, 1)
        
        layout.addLayout(arrow_layout, 1, 0, 1, 3)
        
        # Connect signals
        self.pan_up_btn.pressed.connect(
            lambda: self._send_pan_tilt(0, -100)
        )
        self.pan_up_btn.repeating.connect(
            lambda: self._send_pan_tilt(0, -100)
        )
        self.pan_down_btn.pressed.connect(
            lambda: self._send_pan_tilt(0, 100)
        )
        self.pan_down_btn.repeating.connect(
            lambda: self._send_pan_tilt(0, 100)
        )
        self.pan_left_btn.pressed.connect(
            lambda: self._send_pan_tilt(-100, 0)
        )
        self.pan_left_btn.repeating.connect(
            lambda: self._send_pan_tilt(-100, 0)
        )
        self.pan_right_btn.pressed.connect(
            lambda: self._send_pan_tilt(100, 0)
        )
        self.pan_right_btn.repeating.connect(
            lambda: self._send_pan_tilt(100, 0)
        )
        for button in (
            self.pan_up_btn,
            self.pan_down_btn,
            self.pan_left_btn,
            self.pan_right_btn,
        ):
            button.released.connect(self._send_pan_tilt_stop)
        self.pan_home_btn.clicked.connect(
            lambda: self._send_pan_tilt_home()
        )
        
        return group
    
    def _create_zoom_group(self) -> QGroupBox:
        """Create zoom control group."""
        group = QGroupBox("Zoom Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout(group)
        
        self.zoom_wide_btn = self._create_auto_repeat_button("◄ WIDE (Out)")
        self.zoom_tele_btn = self._create_auto_repeat_button("TELE (In) ►")
        self.zoom_stop_btn = self._create_control_button("STOP")
        
        layout.addWidget(QLabel("Zoom:"))
        layout.addWidget(self.zoom_wide_btn)
        
        zoom_slider_layout = QVBoxLayout()
        zoom_slider_layout.addWidget(QLabel("Zoom Position:"))
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(0, 0xFFFF)
        self.zoom_slider.setValue(0)
        self.zoom_slider.sliderMoved.connect(
            lambda: self._send_zoom_absolute(self.zoom_slider.value())
        )
        zoom_slider_layout.addWidget(self.zoom_slider)
        layout.addLayout(zoom_slider_layout)
        
        layout.addWidget(self.zoom_tele_btn)
        layout.addWidget(self.zoom_stop_btn)
        
        # Connect signals
        self.zoom_wide_btn.pressed.connect(
            lambda: self._send_zoom_wide(7)
        )
        self.zoom_wide_btn.repeating.connect(
            lambda: self._send_zoom_wide(7)
        )
        self.zoom_tele_btn.pressed.connect(
            lambda: self._send_zoom_tele(7)
        )
        self.zoom_tele_btn.repeating.connect(
            lambda: self._send_zoom_tele(7)
        )
        self.zoom_stop_btn.clicked.connect(
            lambda: self._send_zoom_stop()
        )
        
        return group
    
    def _create_focus_group(self) -> QGroupBox:
        """Create focus control group."""
        group = QGroupBox("Focus Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout(group)
        
        self.focus_auto_btn = self._create_control_button("Auto Focus")
        self.focus_manual_btn = self._create_control_button("Manual Focus")
        self.focus_near_btn = self._create_control_button("◄ NEAR")
        self.focus_far_btn = self._create_control_button("FAR ►")
        self.focus_stop_btn = self._create_control_button("STOP")
        
        layout.addWidget(QLabel("Focus:"))
        layout.addWidget(self.focus_auto_btn)
        layout.addWidget(self.focus_manual_btn)
        layout.addWidget(self.focus_near_btn)
        layout.addWidget(self.focus_far_btn)
        layout.addWidget(self.focus_stop_btn)
        layout.addStretch()
        
        # Connect signals
        self.focus_auto_btn.clicked.connect(
            lambda: self._send_focus_auto()
        )
        self.focus_manual_btn.clicked.connect(
            lambda: self._send_focus_manual()
        )
        self.focus_near_btn.pressed.connect(
            lambda: self._send_focus_near(5)
        )
        self.focus_near_btn.released.connect(
            lambda: self._send_focus_stop()
        )
        self.focus_far_btn.pressed.connect(
            lambda: self._send_focus_far(5)
        )
        self.focus_far_btn.released.connect(
            lambda: self._send_focus_stop()
        )
        self.focus_stop_btn.clicked.connect(
            lambda: self._send_focus_stop()
        )
        
        return group
    
    def _create_iris_group(self) -> QGroupBox:
        """Create iris control group."""
        group = QGroupBox("Iris Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout(group)
        
        self.iris_open_btn = self._create_control_button("◄ OPEN (Bright)")
        self.iris_close_btn = self._create_control_button("CLOSE (Dark) ►")
        self.iris_stop_btn = self._create_control_button("STOP")
        
        layout.addWidget(QLabel("Iris:"))
        layout.addWidget(self.iris_open_btn)
        
        iris_slider_layout = QVBoxLayout()
        iris_slider_layout.addWidget(QLabel("Iris Level:"))
        self.iris_slider = QSlider(Qt.Orientation.Horizontal)
        self.iris_slider.setRange(0, 100)
        self.iris_slider.setValue(50)
        iris_slider_layout.addWidget(self.iris_slider)
        layout.addLayout(iris_slider_layout)
        
        layout.addWidget(self.iris_close_btn)
        layout.addWidget(self.iris_stop_btn)
        
        # Connect signals
        self.iris_open_btn.pressed.connect(
            lambda: self._send_iris_open(5)
        )
        self.iris_open_btn.released.connect(
            lambda: self._send_iris_stop()
        )
        self.iris_close_btn.pressed.connect(
            lambda: self._send_iris_close(5)
        )
        self.iris_close_btn.released.connect(
            lambda: self._send_iris_stop()
        )
        self.iris_stop_btn.clicked.connect(
            lambda: self._send_iris_stop()
        )
        
        return group
    
    def _create_white_balance_group(self) -> QGroupBox:
        """Create white balance control group."""
        group = QGroupBox("White Balance")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("Mode:"))
        
        self.wb_auto_btn = self._create_control_button("Auto")
        self.wb_indoor_btn = self._create_control_button("Indoor")
        self.wb_outdoor_btn = self._create_control_button("Outdoor")
        
        layout.addWidget(self.wb_auto_btn)
        layout.addWidget(self.wb_indoor_btn)
        layout.addWidget(self.wb_outdoor_btn)
        layout.addStretch()
        
        # Connect signals
        self.wb_auto_btn.clicked.connect(
            lambda: self._send_white_balance_auto()
        )
        self.wb_indoor_btn.clicked.connect(
            lambda: self._send_white_balance_indoor()
        )
        self.wb_outdoor_btn.clicked.connect(
            lambda: self._send_white_balance_outdoor()
        )
        
        return group
    
    def _create_exposure_group(self) -> QGroupBox:
        """Create exposure control group."""
        group = QGroupBox("Exposure Control")
        group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("Exposure:"))
        
        self.exposure_dial = QDial()
        self.exposure_dial.setMinimumSize(110, 110)
        self.exposure_dial.setMaximumSize(128, 128)
        self.exposure_dial.setRange(-12, 12)
        self.exposure_dial.setValue(0)
        self.exposure_dial.setNotchesVisible(True)
        layout.addWidget(self.exposure_dial)
        
        self.exposure_value_label = QLabel("0.0")
        layout.addWidget(self.exposure_value_label)

        layout.addWidget(QLabel("Contrast:"))
        self.contrast_dial = QDial()
        self.contrast_dial.setMinimumSize(110, 110)
        self.contrast_dial.setMaximumSize(128, 128)
        self.contrast_dial.setRange(0, 100)
        self.contrast_dial.setValue(50)
        self.contrast_dial.setNotchesVisible(True)
        layout.addWidget(self.contrast_dial)
        
        self.exposure_dial.valueChanged.connect(
            lambda: self.exposure_value_label.setText(
                f"{self.exposure_dial.value() * 0.5:.1f}"
            )
        )
        self.exposure_dial.valueChanged.connect(
            lambda value: self._send_exposure(value)
        )
        self.contrast_dial.valueChanged.connect(
            lambda value: self._send_contrast(value)
        )
        
        return group
    
    def _create_control_button(self, text: str, min_width: int = 80) -> QPushButton:
        """Create a control button with standard styling."""
        btn = QPushButton(text)
        btn.setMinimumWidth(min_width)
        btn.setEnabled(False)
        return btn
    
    def _connect_signals(self) -> None:
        """Connect internal signals and slots."""
        pass
    
    def _send_pan_tilt(self, pan_move: int, tilt_move: int) -> None:
        """Send pan/tilt command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            speed = self.pan_tilt_speed_spin.value()
            camera.pan_tilt_relative(speed, speed, pan_move, tilt_move)
    
    def _send_pan_tilt_stop(self) -> None:
        """Send pan/tilt stop command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.pan_tilt_stop()
    
    def _send_pan_tilt_home(self) -> None:
        """Send pan/tilt home command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.pan_tilt_absolute(1, 1, 0, 0)
    
    def _send_zoom_absolute(self, position: int) -> None:
        """Send absolute zoom command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.zoom_absolute(position)
    
    def _send_zoom_tele(self, speed: int) -> None:
        """Send zoom telephoto command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.zoom_tele(speed)
    
    def _send_zoom_wide(self, speed: int) -> None:
        """Send zoom wide command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.zoom_wide(speed)
    
    def _send_zoom_stop(self) -> None:
        """Send zoom stop command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.zoom_stop()
    
    def _send_focus_auto(self) -> None:
        """Send autofocus command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_auto()
    
    def _send_focus_manual(self) -> None:
        """Send manual focus command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_manual()
    
    def _send_focus_near(self, speed: int) -> None:
        """Send focus near command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_near(speed)
    
    def _send_focus_far(self, speed: int) -> None:
        """Send focus far command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_far(speed)
    
    def _send_focus_stop(self) -> None:
        """Send focus stop command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.focus_stop()
    
    def _send_iris_open(self, speed: int) -> None:
        """Send iris open command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.iris_open(speed)
    
    def _send_iris_close(self, speed: int) -> None:
        """Send iris close command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.iris_close(speed)
    
    def _send_iris_stop(self) -> None:
        """Send iris stop command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.iris_stop()
    
    def _send_white_balance_auto(self) -> None:
        """Send auto white balance command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.white_balance_auto()
    
    def _send_white_balance_indoor(self) -> None:
        """Send indoor white balance command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.white_balance_indoor()
    
    def _send_white_balance_outdoor(self) -> None:
        """Send outdoor white balance command."""
        if not self.enabled:
            return
        
        camera = self.camera_manager.get_active_camera()
        if camera:
            camera.white_balance_outdoor()
    
    def enable_controls(self) -> None:
        """Enable all controls."""
        self.enabled = True
        for child in self.findChildren(QPushButton):
            child.setEnabled(True)
        for child in self.findChildren(QSlider):
            child.setEnabled(True)
        for child in self.findChildren(QSpinBox):
            child.setEnabled(True)
    
    def disable_controls(self) -> None:
        """Disable all controls."""
        self.enabled = False
        for child in self.findChildren(QPushButton):
            child.setEnabled(False)
        for child in self.findChildren(QSlider):
            child.setEnabled(False)
        for child in self.findChildren(QSpinBox):
            child.setEnabled(False)


_LegacyControlPanel = ControlPanel


class ControlPanel(_LegacyControlPanel):
    """Compact settings dashboard with persistent movement and zoom controls."""

    def _init_ui(self) -> None:
        self.setFixedWidth(250)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        settings_content = QWidget()
        settings_layout = QVBoxLayout(settings_content)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(4)

        self.settings_group = QGroupBox("Camera Settings")
        state_layout = QGridLayout(self.settings_group)
        state_layout.setContentsMargins(5, 12, 5, 5)
        state_layout.setHorizontalSpacing(4)
        state_layout.setVerticalSpacing(4)

        self._summary_buttons = {}
        self._summary_reset_buttons = {}
        self._summary_values = {
            "pan_tilt": "center",
            "pt_speed": "15",
            "zoom": "0",
            "focus": "auto",
            "iris": "50",
            "white_balance": "auto",
            "exposure": "0.0",
            "contrast": "50",
            "brightness": "50",
            "saturation": "50",
            "sharpness": "50",
            "gamma": "50",
            "hue": "50",
            "gain": "50",
            "backlight": "50",
        }
        self.reset_all_btn = QPushButton("Reset All Controls")
        self.reset_all_btn.setToolTip(
            "Restore all supported controls to MerekaiPTZControl defaults"
        )
        self.reset_all_btn.clicked.connect(self._reset_all_controls)
        summary = (
            ("Iris", "iris"),
            ("WB", "white_balance"),
            ("Exposure", "exposure"),
            ("Contrast", "contrast"),
            ("Brightness", "brightness"),
            ("Saturation", "saturation"),
            ("Sharpness", "sharpness"),
            ("Gamma", "gamma"),
            ("Hue", "hue"),
            ("Gain", "gain"),
            ("Backlight", "backlight"),
        )
        saved_names = self.settings.get("camera_setting_matrix_names", {})
        if not isinstance(saved_names, dict):
            logger.warning("Ignoring invalid camera setting matrix names")
            saved_names = {}
        self._summary_labels = {}
        self._summary_disabled = self._load_disabled_summary_settings()
        for index, (label, key) in enumerate(summary):
            saved_label = saved_names.get(key, label)
            if not isinstance(saved_label, str) or not saved_label.strip():
                saved_label = label
            self._summary_labels[key] = saved_label.strip()
            button = SettingSummaryButton()
            button.setMinimumHeight(56)
            button.setToolTip(
                f"Adjust {self._summary_labels[key]}. Right-click to rename."
            )
            button.clicked.connect(
                lambda checked=False, value=key: self._select_setting(value)
            )
            button.context_menu_requested.connect(
                lambda position, value=key:
                    self._show_summary_context_menu(value, position)
            )
            reset_button = QPushButton("↺")
            reset_button.setFixedSize(28, 28)
            reset_button.setToolTip(f"Reset {label} to its default")
            reset_button.setAccessibleName(f"Reset {label}")
            reset_button.setStyleSheet("padding: 0px;")
            reset_button.clicked.connect(
                lambda checked=False, value=key: self._reset_setting(value)
            )
            self._summary_buttons[key] = button
            self._summary_reset_buttons[key] = reset_button
            self._refresh_summary(key)
            tile = QWidget()
            tile_layout = QHBoxLayout(tile)
            tile_layout.setContentsMargins(0, 0, 0, 0)
            tile_layout.setSpacing(2)
            tile_layout.addWidget(button, 1)
            tile_layout.addWidget(reset_button)
            if key == "backlight":
                state_layout.addWidget(self.reset_all_btn, index // 2 + 1, 0)
                state_layout.addWidget(tile, index // 2 + 1, 1)
            else:
                state_layout.addWidget(tile, index // 2 + 1, index % 2)
        settings_layout.addWidget(self.settings_group)
        settings_layout.addStretch()

        self.editor_group = QGroupBox("Adjust Pan / Tilt")
        self.editor_group.setFixedHeight(64)
        editor_layout = QVBoxLayout(self.editor_group)
        editor_layout.setContentsMargins(5, 4, 5, 2)
        editor_layout.setSpacing(2)
        self.editor_stack = QStackedWidget()
        self.editor_stack.setFixedHeight(40)
        editor_row = QHBoxLayout()
        editor_row.setSpacing(2)
        editor_row.addWidget(self.editor_stack, 1)
        self.reset_setting_btn = QPushButton("↻")
        self.reset_setting_btn.setFixedSize(28, 28)
        self.reset_setting_btn.setToolTip("Reset the selected setting")
        self.reset_setting_btn.setAccessibleName("Reset selected setting")
        self.reset_setting_btn.setStyleSheet("padding: 0px;")
        self.reset_setting_btn.clicked.connect(self._reset_selected_setting)
        editor_row.addWidget(self.reset_setting_btn)
        editor_layout.addLayout(editor_row)
        layout.addWidget(settings_content)
        layout.addWidget(self.editor_group)

        self._editors = {}
        self._capabilities = {}
        self._create_fixed_motion_controls(layout)
        self._create_dashboard_editors()
        for key in self._summary_buttons:
            self._refresh_summary(key)
        self._select_setting("exposure")
        self.disable_controls()

    def _refresh_summary(self, key: str, label: str = "") -> None:
        button = self._summary_buttons.get(key)
        if button is not None:
            if label:
                self._summary_labels[key] = label
            title = self._display_summary_label(key)
            button.setProperty("setting_label", title)
            button.setProperty("matrix_disabled", key in self._summary_disabled)
            value = self._summary_values[key]
            button.setText(f"{title}: {value}")
            button.setAccessibleName(f"{title}: {value}")
            button.setToolTip(
                self._tr("Adjust {name}. Right-click to rename.").format(
                    name=title
                )
            )
            reset_button = self._summary_reset_buttons.get(key)
            if reset_button is not None:
                reset_button.setToolTip(
                    self._tr("Reset {name} to its default").format(name=title)
                )
                reset_button.setAccessibleName(
                    self._tr("Reset {name}").format(name=title)
                )
            style = "padding: 2px 0px;"
            slider = (
                getattr(self, "iris_slider", None)
                if key == "iris"
                else getattr(self, "range_sliders", {}).get(key)
            )
            if slider is not None:
                try:
                    value = float(self._summary_values[key])
                except ValueError:
                    button.setStyleSheet(style)
                minimum = float(slider.minimum())
                maximum = float(slider.maximum())
                if key == "exposure":
                    minimum *= 0.5
                    maximum *= 0.5
                if maximum > minimum:
                    position = max(
                        0.0, min(1.0, (value - minimum) / (maximum - minimum))
                    )
                    color = QColor.fromHsv(round(position * 300), 190, 255)
                    style += f" color: {color.name()};"
            if key in self._summary_disabled:
                style += " color: #697170; border-style: dashed;"
            button.setStyleSheet(style)

    def _camera_setting_key(self) -> str:
        return getattr(self.camera_manager, "active_camera", None) or "default"

    def _load_disabled_summary_settings(self) -> set[str]:
        saved = self.settings.get("camera_setting_matrix_disabled", {})
        if not isinstance(saved, dict):
            logger.warning("Ignoring invalid disabled camera setting data")
            return set()
        values = saved.get(self._camera_setting_key(), [])
        if not isinstance(values, list):
            return set()
        return {value for value in values if isinstance(value, str)}

    def _save_disabled_summary_settings(self) -> None:
        saved = self.settings.get("camera_setting_matrix_disabled", {})
        if not isinstance(saved, dict):
            saved = {}
        saved = dict(saved)
        saved[self._camera_setting_key()] = sorted(self._summary_disabled)
        self.settings.set("camera_setting_matrix_disabled", saved)
        self.settings.save()

    def _show_summary_context_menu(self, key: str, position) -> None:
        menu = QMenu(self)
        rename_action = menu.addAction("Change name")
        disabled = key in self._summary_disabled
        toggle_action = menu.addAction(
            "Enable button" if disabled else "Disable button"
        )
        selected = menu.exec(position)
        if selected == rename_action:
            self._rename_summary_setting(key)
        elif selected == toggle_action:
            if disabled:
                self._summary_disabled.remove(key)
            else:
                self._summary_disabled.add(key)
            self._refresh_summary(key)
            self._save_disabled_summary_settings()

    def _rename_summary_setting(self, key: str) -> None:
        current_name = self._display_summary_label(key)
        new_name, accepted = QInputDialog.getText(
            self,
            self._tr("Rename Camera Setting"),
            self._tr("Setting name:"),
            text=current_name,
        )
        if not accepted:
            return
        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(
                self,
                self._tr("Invalid Setting Name"),
                self._tr("The setting name cannot be empty."),
            )
            return

        saved_names = self.settings.get("camera_setting_matrix_names", {})
        if not isinstance(saved_names, dict):
            logger.warning("Replacing invalid camera setting matrix names")
            saved_names = {}
        saved_names = dict(saved_names)
        saved_names[key] = new_name
        self.settings.set("camera_setting_matrix_names", saved_names)
        self.settings.save()
        self._summary_labels[key] = new_name
        self._refresh_summary(key)
        self._summary_buttons[key].setToolTip(
            f"Adjust {new_name}. Right-click to rename."
        )

    def _add_editor(self, key: str, widget: QWidget) -> None:
        self._editors[key] = self.editor_stack.addWidget(widget)

    def _create_fixed_motion_controls(self, parent_layout: QVBoxLayout) -> None:
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(4)

        pan_group = QGroupBox("Pan / Tilt")
        pan_layout = QVBoxLayout(pan_group)
        pan_layout.setContentsMargins(5, 10, 5, 5)
        pan_layout.setSpacing(3)
        self.pan_tilt_speed_spin = QSpinBox()
        self.pan_tilt_speed_spin.setRange(1, 24)
        self.pan_tilt_speed_spin.setValue(
            self.settings.get("default_pan_speed", 15)
        )
        self.pan_tilt_speed_spin.setToolTip("Pan and tilt movement speed")
        self.pan_home_btn = self._create_control_button("HOME", 48)
        self.pan_home_btn.setToolTip("Return pan and tilt to their default center")
        self.pan_tilt_joystick = PanTiltJoystick()
        self.pan_tilt_joystick.setFixedSize(88, 88)
        self.pan_tilt_joystick.movement_changed.connect(self._on_pan_tilt_changed)
        self.pan_tilt_joystick.released.connect(self._send_pan_tilt_stop)
        movement_layout = QHBoxLayout()
        movement_layout.setSpacing(4)
        movement_layout.addWidget(self.pan_tilt_joystick)
        direction_layout = QGridLayout()
        direction_layout.setSpacing(2)
        self.pan_direction_buttons = {}
        directions = (
            ("up", "↑", 0, 1, 0, -100),
            ("left", "←", 1, 0, -100, 0),
            ("right", "→", 1, 2, 100, 0),
            ("down", "↓", 2, 1, 0, 100),
        )
        for name, text, row, column, pan, tilt in directions:
            button = self._create_auto_repeat_button(text, 28)
            button.setFixedSize(34, 30)
            button.setToolTip(name.capitalize())
            button.setAccessibleName(name.capitalize())
            button.pressed.connect(
                lambda x=pan, y=tilt: self._send_pan_tilt(x, y)
            )
            button.repeating.connect(
                lambda x=pan, y=tilt: self._send_pan_tilt(x, y)
            )
            button.released.connect(self._send_pan_tilt_stop)
            self.pan_direction_buttons[name] = button
            direction_layout.addWidget(button, row, column)
        movement_layout.addLayout(direction_layout)
        pan_layout.addLayout(movement_layout)

        pan_options = QHBoxLayout()
        pan_options.setSpacing(4)
        pan_options.addWidget(QLabel("Speed"))
        pan_options.addWidget(self.pan_tilt_speed_spin)
        pan_options.addWidget(self.pan_home_btn)
        pan_layout.addLayout(pan_options)
        self.pan_home_btn.clicked.connect(self._on_pan_home)
        self.pan_tilt_speed_spin.valueChanged.connect(
            lambda value: self._set_summary("pt_speed", str(value))
        )
        controls_layout.addWidget(pan_group)

        zoom_group = QGroupBox("Zoom")
        zoom_group.setFixedHeight(100)
        zoom_layout = QVBoxLayout(zoom_group)
        zoom_layout.setContentsMargins(5, 12, 5, 5)
        zoom_layout.setSpacing(3)
        zoom_value_row = QHBoxLayout()
        zoom_value_row.addWidget(QLabel("Position"))
        self.zoom_value_label = QLabel("0")
        self.zoom_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        zoom_value_row.addWidget(self.zoom_value_label)
        self.zoom_default_btn = QPushButton("Home")
        self.zoom_default_btn.setToolTip("Return zoom to its home wide position")
        self.zoom_default_btn.clicked.connect(self._reset_zoom_default)
        zoom_value_row.addWidget(self.zoom_default_btn)
        zoom_layout.addLayout(zoom_value_row)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(0, 0xFFFF)
        zoom_layout.addWidget(self.zoom_slider)

        zoom_buttons = QHBoxLayout()
        self.zoom_wide_btn = self._create_auto_repeat_button("WIDE", 42)
        self.zoom_tele_btn = self._create_auto_repeat_button("TELE", 42)
        self.zoom_stop_btn = self._create_control_button("STOP", 42)
        for button in (self.zoom_wide_btn, self.zoom_stop_btn, self.zoom_tele_btn):
            zoom_buttons.addWidget(button)
        zoom_layout.addLayout(zoom_buttons)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        self.zoom_wide_btn.pressed.connect(lambda: self._on_zoom_motion(-1))
        self.zoom_wide_btn.repeating.connect(lambda: self._on_zoom_motion(-1))
        self.zoom_wide_btn.released.connect(self._send_zoom_stop)
        self.zoom_tele_btn.pressed.connect(lambda: self._on_zoom_motion(1))
        self.zoom_tele_btn.repeating.connect(lambda: self._on_zoom_motion(1))
        self.zoom_tele_btn.released.connect(self._send_zoom_stop)
        self.zoom_stop_btn.clicked.connect(self._send_zoom_stop)
        controls_layout.addWidget(zoom_group)

        focus_group = QGroupBox("Focus")
        focus_group.setFixedHeight(100)
        focus_layout = QVBoxLayout(focus_group)
        focus_layout.setContentsMargins(5, 10, 5, 5)
        focus_layout.setSpacing(3)
        focus_modes = QHBoxLayout()
        self.focus_auto_btn = self._create_control_button("AUTO", 40)
        self.focus_manual_btn = self._create_control_button("MANUAL", 48)
        self.focus_default_btn = self._create_control_button("Home", 40)
        self.focus_default_btn.setToolTip("Restore autofocus")
        self.focus_default_btn.clicked.connect(lambda: self._reset_setting("focus"))
        focus_modes.addWidget(self.focus_auto_btn)
        focus_modes.addWidget(self.focus_manual_btn)
        focus_modes.addWidget(self.focus_default_btn)
        focus_layout.addLayout(focus_modes)
        focus_actions = QHBoxLayout()
        self.focus_near_btn = self._create_auto_repeat_button("NEAR", 40)
        self.focus_stop_btn = self._create_control_button("STOP", 40)
        self.focus_far_btn = self._create_auto_repeat_button("FAR", 40)
        focus_actions.addWidget(self.focus_near_btn)
        focus_actions.addWidget(self.focus_stop_btn)
        focus_actions.addWidget(self.focus_far_btn)
        focus_layout.addLayout(focus_actions)
        self.focus_auto_btn.clicked.connect(self._on_focus_auto)
        self.focus_manual_btn.clicked.connect(self._on_focus_manual)
        self.focus_near_btn.pressed.connect(lambda: self._send_focus_near(5))
        self.focus_near_btn.repeating.connect(lambda: self._send_focus_near(5))
        self.focus_near_btn.released.connect(self._send_focus_stop)
        self.focus_far_btn.pressed.connect(lambda: self._send_focus_far(5))
        self.focus_far_btn.repeating.connect(lambda: self._send_focus_far(5))
        self.focus_far_btn.released.connect(self._send_focus_stop)
        self.focus_stop_btn.clicked.connect(self._send_focus_stop)
        controls_layout.addWidget(focus_group)
        parent_layout.addLayout(controls_layout)

    def _create_dashboard_editors(self) -> None:
        iris_page = QWidget()
        iris_layout = QHBoxLayout(iris_page)
        iris_layout.setContentsMargins(0, 0, 0, 0)
        iris_layout.setSpacing(2)
        self.iris_slider = QSlider(Qt.Orientation.Horizontal)
        self.iris_slider.setMinimumWidth(20)
        self.iris_slider.setRange(0, 100)
        self.iris_slider.setValue(50)
        self.iris_open_btn = self._create_control_button("OPEN", 42)
        self.iris_close_btn = self._create_control_button("CLOSE", 42)
        self.iris_stop_btn = self._create_control_button("STOP", 42)
        iris_layout.addWidget(self.iris_open_btn)
        iris_layout.addWidget(self.iris_slider, 1)
        iris_layout.addWidget(self.iris_close_btn)
        iris_layout.addWidget(self.iris_stop_btn)
        self.iris_slider.valueChanged.connect(
            lambda value: self._set_summary("iris", str(value))
        )
        self.iris_open_btn.pressed.connect(lambda: self._send_iris_open(5))
        self.iris_open_btn.released.connect(self._send_iris_stop)
        self.iris_close_btn.pressed.connect(lambda: self._send_iris_close(5))
        self.iris_close_btn.released.connect(self._send_iris_stop)
        self.iris_stop_btn.clicked.connect(self._send_iris_stop)
        self._add_editor("iris", iris_page)

        white_page = QWidget()
        white_layout = QHBoxLayout(white_page)
        white_layout.setContentsMargins(0, 0, 0, 0)
        white_layout.setSpacing(2)
        self.wb_auto_btn = self._create_control_button("AUTO", 46)
        self.wb_indoor_btn = self._create_control_button("INDOOR", 54)
        self.wb_outdoor_btn = self._create_control_button("OUTDOOR", 56)
        for button in (self.wb_auto_btn, self.wb_indoor_btn, self.wb_outdoor_btn):
            white_layout.addWidget(button)
        self.wb_auto_btn.clicked.connect(lambda: self._on_white_balance("auto"))
        self.wb_indoor_btn.clicked.connect(lambda: self._on_white_balance("indoor"))
        self.wb_outdoor_btn.clicked.connect(lambda: self._on_white_balance("outdoor"))
        self._add_editor("white_balance", white_page)

        slider_settings = (
            ("exposure", "Exposure", -12, 12, 0),
            ("contrast", "Contrast", 0, 100, 50),
            ("brightness", "Brightness", 0, 100, 50),
            ("saturation", "Saturation", 0, 100, 50),
            ("sharpness", "Sharpness", 0, 100, 50),
            ("gamma", "Gamma", 0, 100, 50),
            ("hue", "Hue", 0, 100, 50),
            ("gain", "Gain", 0, 100, 50),
            ("backlight", "Backlight", 0, 100, 50),
        )
        self._setting_defaults = {
            key: value for key, _label, _minimum, _maximum, value in slider_settings
        }
        self.range_sliders = {}
        self.range_value_labels = {}
        self.range_step_buttons = {}
        for key, label, minimum, maximum, value in slider_settings:
            page = QWidget()
            page_layout = QHBoxLayout(page)
            page_layout.setContentsMargins(2, 2, 2, 2)
            page_layout.setSpacing(4)
            decrease = QPushButton("−")
            decrease.setFixedSize(24, 30)
            decrease.setToolTip(f"Decrease {label.lower()}")
            decrease.setAccessibleName(f"Decrease {label.lower()}")
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setMinimumWidth(32)
            slider.setRange(minimum, maximum)
            slider.setValue(value)
            slider.setTracking(True)
            slider.setPageStep(max(1, (maximum - minimum) // 10))
            value_label = QLabel(
                f"{value * 0.5:.1f}" if key == "exposure" else str(value)
            )
            value_label.setMinimumWidth(32)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            increase = QPushButton("+")
            increase.setFixedSize(24, 30)
            increase.setToolTip(f"Increase {label.lower()}")
            increase.setAccessibleName(f"Increase {label.lower()}")
            decrease.clicked.connect(
                lambda checked=False, control=slider: control.setValue(
                    control.value() - 1
                )
            )
            increase.clicked.connect(
                lambda checked=False, control=slider: control.setValue(
                    control.value() + 1
                )
            )
            slider.valueChanged.connect(
                lambda changed, name=key, display=value_label:
                    self._on_range_changed(name, changed, display)
            )
            page_layout.addWidget(decrease)
            page_layout.addWidget(slider, 1)
            page_layout.addWidget(value_label)
            page_layout.addWidget(increase)
            self.range_sliders[key] = slider
            self.range_value_labels[key] = value_label
            self.range_step_buttons[key] = (decrease, increase)
            self._add_editor(key, page)

    def _select_setting(self, key: str) -> None:
        if key in self._summary_disabled:
            return
        index = self._editors.get(key)
        if index is None:
            return
        self._selected_setting = key
        self.editor_stack.setCurrentIndex(index)
        label = self._summary_buttons[key].property("setting_label")
        self.editor_group.setTitle(
            self._tr("Adjust {name}").format(name=label)
        )
        self.reset_setting_btn.setToolTip(
            self._tr("Reset {name} to its default").format(name=label)
        )
        self.reset_setting_btn.setEnabled(
            self.enabled and self._capabilities.get(key, False)
        )

    def _reset_selected_setting(self) -> None:
        key = getattr(self, "_selected_setting", None)
        if key:
            self._reset_setting(key)

    def _reset_setting(self, key: str) -> None:
        if not self.enabled or not self._capabilities.get(key, False):
            return
        if key == "iris":
            value = self.settings.get("iris_manual_level", 50)
            self.iris_slider.setValue(value)
            self._set_summary("iris", str(value))
        elif key == "white_balance":
            self._on_white_balance(self.settings.get("white_balance_mode", "auto"))
        elif key == "focus":
            self._on_focus_auto()
        elif key in self.range_sliders:
            slider = self.range_sliders[key]
            value = self._setting_defaults[key]
            if slider.value() == value:
                self._on_range_changed(key, value, self.range_value_labels[key])
            else:
                slider.setValue(value)

    def _reset_pan_speed(self) -> None:
        if self.enabled and self._capabilities.get("pan_tilt", False):
            self.pan_tilt_speed_spin.setValue(
                self.settings.get("default_pan_speed", 15)
            )

    def _reset_zoom_default(self) -> None:
        if not self.enabled or not self._capabilities.get("zoom", False):
            return
        default_zoom = self.settings.get("zoom_min", 0)
        if self._capabilities.get("zoom_absolute", False):
            if self.zoom_slider.value() == default_zoom:
                self._on_zoom_changed(default_zoom)
            else:
                self.zoom_slider.setValue(default_zoom)
        else:
            self.control_changed.emit("zoom_default", default_zoom)
            self._display_zoom_value(default_zoom)

    def _display_zoom_value(self, value: int) -> None:
        self.zoom_value_label.setText(str(value))
        self._summary_values["zoom"] = str(value)
        self._refresh_summary("zoom")

    def _reset_all_controls(self) -> None:
        if not self.enabled:
            return
        for key in ("iris", "white_balance", *self.range_sliders):
            if self._capabilities.get(key, False):
                self._reset_setting(key)
        if self._capabilities.get("pan_tilt", False):
            self._reset_pan_speed()
            self._set_summary("pan_tilt", "center")
        if self._capabilities.get("pan_tilt", False) or self._capabilities.get(
            "zoom", False
        ):
            self.control_changed.emit("reset_ptz", None)
            if self._capabilities.get("zoom", False) and not self._capabilities.get(
                "zoom_absolute", False
            ):
                self._display_zoom_value(self.settings.get("zoom_min", 0))
        if self._capabilities.get("focus", False):
            self._reset_setting("focus")

    def _set_summary(self, key: str, value: str) -> None:
        self._summary_values[key] = value
        self._refresh_summary(key)
        self.control_changed.emit(key, value)

    def _on_pan_tilt_changed(self, pan: int, tilt: int) -> None:
        self._set_summary("pan_tilt", f"{pan:+d}, {tilt:+d}")
        self._send_pan_tilt(pan, -tilt)

    def _send_pan_tilt(self, pan_move: int, tilt_move: int) -> None:
        if not self.enabled:
            return
        camera = self.camera_manager.get_active_camera()
        if camera is None:
            return
        speed = self.pan_tilt_speed_spin.value()
        if camera.pan_tilt_relative(
            speed, speed, pan_move, tilt_move
        ):
            self.control_changed.emit(
                "ptz_delta",
                (
                    (pan_move > 0) - (pan_move < 0),
                    (tilt_move > 0) - (tilt_move < 0),
                ),
            )

    def _on_pan_home(self) -> None:
        self._send_pan_tilt_home()
        self._set_summary("pan_tilt", "center")
        self.control_changed.emit("ptz_home", None)

    def _on_zoom_changed(self, value: int) -> None:
        self.zoom_value_label.setText(str(value))
        self._set_summary("zoom", str(value))
        self._send_zoom_absolute(value)

    def _on_zoom_motion(self, direction: int) -> None:
        if not self.enabled:
            return
        if direction > 0:
            self._send_zoom_tele(7)
        else:
            self._send_zoom_wide(7)
        self.control_changed.emit("zoom_delta", direction)

    def _on_focus_auto(self) -> None:
        self._set_summary("focus", "auto")
        self._send_focus_auto()

    def _on_focus_manual(self) -> None:
        self._set_summary("focus", "manual")
        self._send_focus_manual()

    def _on_white_balance(self, mode: str) -> None:
        self._set_summary("white_balance", mode)
        sender = {
            "auto": self._send_white_balance_auto,
            "indoor": self._send_white_balance_indoor,
            "outdoor": self._send_white_balance_outdoor,
        }[mode]
        sender()

    def _on_range_changed(self, key: str, value: int, display: QLabel) -> None:
        display.setText(f"{value * 0.5:.1f}" if key == "exposure" else str(value))
        self._set_summary(key, display.text())
        if key == "exposure":
            self._send_exposure(value)
        elif key == "contrast":
            self._send_contrast(value)
        else:
            self._send_video_control(key, value)

    def apply_capabilities(self, capabilities: dict[str, bool]) -> None:
        self._capabilities = dict(capabilities)
        self._summary_disabled = self._load_disabled_summary_settings()
        for key in self._summary_buttons:
            self._refresh_summary(key)
        pan_tilt_supported = capabilities.get("pan_tilt", False)
        self.pan_tilt_joystick.setEnabled(pan_tilt_supported)
        for button in self.pan_direction_buttons.values():
            button.setEnabled(pan_tilt_supported)
        self.pan_tilt_speed_spin.setEnabled(capabilities.get("pan_tilt", False))
        self.pan_home_btn.setEnabled(
            capabilities.get("pan_tilt_home", capabilities.get("pan_tilt", False))
        )
        for key, slider in self.range_sliders.items():
            supported = capabilities.get(key, False)
            slider.setEnabled(supported)
            for button in self.range_step_buttons[key]:
                button.setEnabled(supported)
        zoom_supported = capabilities.get("zoom", False)
        self.zoom_slider.setEnabled(
            capabilities.get("zoom_absolute", zoom_supported)
        )
        self.zoom_wide_btn.setEnabled(zoom_supported)
        self.zoom_tele_btn.setEnabled(zoom_supported)
        self.zoom_stop_btn.setEnabled(zoom_supported)
        self.zoom_default_btn.setEnabled(zoom_supported)
        focus_supported = capabilities.get("focus", False)
        for button in (
            self.focus_auto_btn,
            self.focus_manual_btn,
            self.focus_near_btn,
            self.focus_far_btn,
            self.focus_stop_btn,
            self.focus_default_btn,
        ):
            button.setEnabled(focus_supported)
        for key, button in self._summary_reset_buttons.items():
            button.setEnabled(capabilities.get(key, False))
        self.reset_all_btn.setEnabled(
            any(
                capabilities.get(key, False)
                for key in (
                    "pan_tilt",
                    "zoom",
                    "focus",
                    "iris",
                    "white_balance",
                    *self.range_sliders,
                )
            )
        )
        selected = getattr(self, "_selected_setting", None)
        if selected:
            self.reset_setting_btn.setEnabled(
                self.enabled and capabilities.get(selected, False)
            )

    def refresh_camera_state(self, camera) -> None:
        """Refresh display-only values from the newly active camera."""
        if camera is None:
            return

        getter = getattr(camera, "get_ptz_position", None)
        if callable(getter):
            position = getter()
            zoom = position.get("zoom")
            if zoom is not None:
                zoom = max(0, min(0xFFFF, int(zoom)))
                with QSignalBlocker(self.zoom_slider):
                    self.zoom_slider.setValue(zoom)
                self._display_zoom_value(zoom)

        status_getter = getattr(camera, "get_status", None)
        if not callable(status_getter):
            return
        status = status_getter()
        if not isinstance(status, dict):
            return

        for key, value in status.items():
            if key not in self.range_sliders or not isinstance(value, (int, float)):
                continue
            slider = self.range_sliders[key]
            value = int(value)
            if slider.minimum() <= value <= slider.maximum():
                with QSignalBlocker(slider):
                    slider.setValue(value)
                display = (
                    f"{value * 0.5:.1f}" if key == "exposure" else str(value)
                )
                self._summary_values[key] = display
                self._refresh_summary(key)

    def saved_control_state(self) -> dict[str, object]:
        state: dict[str, object] = {"pan_speed": self.pan_tilt_speed_spin.value()}
        if self._capabilities.get("focus", False):
            state["focus"] = self._summary_values["focus"]
        if self._capabilities.get("iris", False):
            state["iris"] = self.iris_slider.value()
        if self._capabilities.get("white_balance", False):
            state["white_balance"] = self._summary_values["white_balance"]
        if self._capabilities.get("zoom", False):
            if self._capabilities.get("zoom_absolute", False):
                state["zoom"] = self.zoom_slider.value()
            else:
                state["zoom"] = self._summary_values["zoom"]
        for key, slider in self.range_sliders.items():
            if self._capabilities.get(key, False):
                state[key] = slider.value()
        return state

    def apply_saved_control_state(self, state: dict[str, object]) -> None:
        if "pan_speed" in state:
            self.pan_tilt_speed_spin.setValue(int(state["pan_speed"]))

        focus = state.get("focus")
        if self._capabilities.get("focus", False):
            if focus == "auto":
                self._on_focus_auto()
            elif focus == "manual":
                self._on_focus_manual()

        white_balance = state.get("white_balance")
        if self._capabilities.get("white_balance", False) and white_balance in {
            "auto",
            "indoor",
            "outdoor",
        }:
            self._on_white_balance(str(white_balance))

        if self._capabilities.get("iris", False) and "iris" in state:
            self.iris_slider.setValue(int(state["iris"]))
            self._set_summary("iris", str(self.iris_slider.value()))

        if self._capabilities.get("zoom", False) and "zoom" in state:
            zoom = state["zoom"]
            if self._capabilities.get("zoom_absolute", False):
                self.zoom_slider.setValue(int(zoom))
            else:
                self._display_zoom_value(int(zoom))

        for key, slider in self.range_sliders.items():
            if self._capabilities.get(key, False) and key in state:
                slider.setValue(int(state[key]))

    def enable_controls(self) -> None:
        self.enabled = True
        for child in self.findChildren(QPushButton):
            child.setEnabled(True)
        for child in self.findChildren((QSlider, QDial, PanTiltJoystick, QSpinBox)):
            child.setEnabled(True)
        if self._capabilities:
            self.apply_capabilities(self._capabilities)

    def disable_controls(self) -> None:
        self.enabled = False
        for child in self.findChildren(QPushButton):
            child.setEnabled(False)
        for child in self.findChildren((QSlider, QDial, PanTiltJoystick, QSpinBox)):
            child.setEnabled(False)
        for button in self._summary_buttons.values():
            button.setEnabled(True)
        self.reset_setting_btn.setEnabled(False)
