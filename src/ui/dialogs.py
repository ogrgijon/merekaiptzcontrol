"""
Dialog Windows

Additional dialog windows for MerekaiPTZControl.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QGroupBox, QGridLayout, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap

from src.app_paths import resource_path
from src.config.settings import Settings
from .i18n import apply_language


class SettingsDialog(QDialog):
    """Settings configuration dialog (inspired by old SettingsDlg)."""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, settings: Settings, parent=None):
        """Initialize settings dialog."""
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings - MerekaiPTZControl")
        self.setModal(True)
        self.setGeometry(200, 200, 500, 600)
        self.setMinimumWidth(500)
        
        self._init_ui()
        self._load_settings()
        apply_language(self, self.settings.get("language", "en"))
    
    def _init_ui(self) -> None:
        """Initialize user interface."""
        layout = QVBoxLayout(self)
        
        # Motor/Movement Settings (from old C++ app)
        motor_group = QGroupBox("Motor Control")
        motor_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        motor_layout = QGridLayout(motor_group)
        
        motor_layout.addWidget(QLabel("Motor Interval Timer (ms):"), 0, 0)
        self.motor_interval_spin = QSpinBox()
        self.motor_interval_spin.setRange(10, 500)
        self.motor_interval_spin.setValue(70)
        self.motor_interval_spin.setToolTip(
            "Time between motor commands (lower = faster response, higher = smoother)"
        )
        motor_layout.addWidget(self.motor_interval_spin, 0, 1)
        
        motor_layout.addWidget(QLabel("Auto-Repeat Initial Delay (ms):"), 1, 0)
        self.auto_repeat_initial_spin = QSpinBox()
        self.auto_repeat_initial_spin.setRange(100, 2000)
        self.auto_repeat_initial_spin.setValue(500)
        self.auto_repeat_initial_spin.setToolTip(
            "Delay before auto-repeat starts when button is held"
        )
        motor_layout.addWidget(self.auto_repeat_initial_spin, 1, 1)
        
        motor_layout.addWidget(QLabel("Auto-Repeat Interval (ms):"), 2, 0)
        self.auto_repeat_interval_spin = QSpinBox()
        self.auto_repeat_interval_spin.setRange(10, 500)
        self.auto_repeat_interval_spin.setValue(50)
        self.auto_repeat_interval_spin.setToolTip(
            "Time between auto-repeat commands"
        )
        motor_layout.addWidget(self.auto_repeat_interval_spin, 2, 1)
        
        self.use_extension_unit_motion_check = QCheckBox(
            "Use Native Motion Control"
        )
        self.use_extension_unit_motion_check.setToolTip(
            "Use camera-specific Native motion control if available"
        )
        motor_layout.addWidget(self.use_extension_unit_motion_check, 3, 0, 1, 2)
        
        layout.addWidget(motor_group)
        
        # Camera Settings
        camera_group = QGroupBox("Camera Settings")
        camera_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        camera_layout = QGridLayout(camera_group)
        
        camera_layout.addWidget(QLabel("Baud Rate:"), 0, 0)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "19200", "38400", "115200"])
        self.baudrate_combo.setCurrentText("115200")
        camera_layout.addWidget(self.baudrate_combo, 0, 1)
        
        camera_layout.addWidget(QLabel("Timeout (seconds):"), 1, 0)
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(0.5, 10.0)
        self.timeout_spin.setValue(2.0)
        self.timeout_spin.setSingleStep(0.1)
        camera_layout.addWidget(self.timeout_spin, 1, 1)
        
        camera_layout.addWidget(QLabel("Max Presets:"), 2, 0)
        self.presets_spin = QSpinBox()
        self.presets_spin.setRange(5, 20)
        self.presets_spin.setValue(8)
        camera_layout.addWidget(self.presets_spin, 2, 1)
        
        layout.addWidget(camera_group)
        
        # UI Settings
        ui_group = QGroupBox("UI Settings")
        ui_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        ui_layout = QVBoxLayout(ui_group)
        
        self.enable_shortcuts_check = QCheckBox("Enable Keyboard Shortcuts")
        self.enable_shortcuts_check.setChecked(True)
        ui_layout.addWidget(self.enable_shortcuts_check)
        
        self.enable_hotkeys_check = QCheckBox("Enable Global Hotkeys (Windows only)")
        self.enable_hotkeys_check.setChecked(False)
        ui_layout.addWidget(self.enable_hotkeys_check)

        ui_layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Español", "es")
        ui_layout.addWidget(self.language_combo)

        layout.addWidget(ui_group)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_to_defaults)
        
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_settings(self) -> None:
        """Load settings from manager."""
        self.motor_interval_spin.setValue(
            self.settings.get("motor_interval_timer", 70)
        )
        self.auto_repeat_initial_spin.setValue(
            self.settings.get("auto_repeat_initial_delay", 500)
        )
        self.auto_repeat_interval_spin.setValue(
            self.settings.get("auto_repeat_delay", 50)
        )
        self.use_extension_unit_motion_check.setChecked(
            self.settings.get("use_extension_unit_motion_control", False)
        )
        self.baudrate_combo.setCurrentText(
            str(self.settings.get("camera_baudrate", 115200))
        )
        self.timeout_spin.setValue(
            self.settings.get("camera_timeout", 2.0)
        )
        self.presets_spin.setValue(
            self.settings.get("max_presets", 8)
        )
        self.enable_shortcuts_check.setChecked(
            self.settings.get("enable_keyboard_shortcuts", True)
        )
        self.enable_hotkeys_check.setChecked(
            self.settings.get("enable_global_hotkeys", False)
        )
        language_index = self.language_combo.findData(
            self.settings.get("language", "en")
        )
        self.language_combo.setCurrentIndex(max(language_index, 0))
    
    def get_settings(self) -> dict:
        """Get modified settings."""
        return {
            "motor_interval_timer": self.motor_interval_spin.value(),
            "auto_repeat_initial_delay": self.auto_repeat_initial_spin.value(),
            "auto_repeat_delay": self.auto_repeat_interval_spin.value(),
            "use_extension_unit_motion_control": self.use_extension_unit_motion_check.isChecked(),
            "camera_baudrate": int(self.baudrate_combo.currentText()),
            "camera_timeout": self.timeout_spin.value(),
            "max_presets": self.presets_spin.value(),
            "enable_keyboard_shortcuts": self.enable_shortcuts_check.isChecked(),
            "enable_global_hotkeys": self.enable_hotkeys_check.isChecked(),
            "language": self.language_combo.currentData(),
        }
    
    def _reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.settings.reset_to_defaults()
        self._load_settings()
    
    def accept(self) -> None:
        """Accept and save settings."""
        new_settings = self.get_settings()
        for key, value in new_settings.items():
            self.settings.set(key, value)
        self.settings_changed.emit(new_settings)
        super().accept()


class AboutDialog(QDialog):
    """About dialog - shows application information."""
    
    def __init__(self, parent=None, language: str = "en"):
        """Initialize about dialog."""
        super().__init__(parent)
        self.language = language
        self.setWindowTitle("About MerekaiPTZControl")
        self.setWindowIcon(QIcon(str(resource_path("resources/merekaiptzcontrol.png"))))
        self.setModal(True)
        self.setGeometry(200, 200, 500, 400)
        self.setMinimumWidth(400)
        
        self._init_ui()
        apply_language(self, language)
    
    def _init_ui(self) -> None:
        """Initialize user interface."""
        layout = QVBoxLayout(self)

        logo = QLabel()
        logo.setPixmap(
            QPixmap(str(resource_path("resources/merekaiptzcontrol.png"))).scaled(
                112,
                112,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        
        title = QLabel("<b>MerekaiPTZControl v1.0.0</b>")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        subtitle = QLabel("Professional PTZ Camera Control")
        subtitle.setFont(QFont("Arial", 11))
        layout.addWidget(subtitle)
        
        layout.addSpacing(10)
        
        description = QTextEdit()
        description.setReadOnly(True)
        english_description = """
# MerekaiPTZControl

Professional PTZ camera control in a focused desktop interface. Adjust camera
movement, refine the image, and save repeatable positions from one place.

## Camera support
Compatible cameras can connect through serial VISCA, Linux V4L2, or the
optional Windows DirectShow/UVC bridge. Detection and available controls
depend on the camera and its exposed interfaces.

## Features
- Pan, tilt, and zoom with adjustable movement speeds
- Focus, exposure, white balance, and image controls when supported
- Save and recall camera presets
- Auto-repeat movement controls

## Technology and licensing
- Python 3.8+ and PyQt6
- MIT-licensed original application
- Optional Windows bridge includes GPL-3.0-or-later source

See the project README and native bridge documentation for setup, compatible
camera details, and license information.
        """
        spanish_description = """
# MerekaiPTZControl

Control profesional de cámaras PTZ en una interfaz de escritorio sencilla.
Ajusta el movimiento de la cámara, afina la imagen y guarda posiciones para
volver a utilizarlas.

## Compatibilidad con cámaras
Conecta cámaras compatibles mediante VISCA serie, V4L2 en Linux o el puente
opcional DirectShow/UVC para Windows. La detección y los controles disponibles
dependen de la cámara y de las interfaces que ofrece.

## Funciones
- Paneo, inclinación y zoom con velocidades ajustables
- Enfoque, exposición, balance de blancos y controles de imagen compatibles
- Guardar y recuperar preajustes de cámara
- Controles de movimiento con repetición automática

## Tecnología y licencias
- Python 3.8+ y PyQt6
- Aplicación original con licencia MIT
- El puente opcional para Windows incluye código bajo GPL-3.0-or-later

Consulta el README del proyecto y la documentación del puente nativo para ver
la instalación, las cámaras compatibles y la información de licencias.
        """
        description.setMarkdown(
            spanish_description if self.language == "es" else english_description
        )
        layout.addWidget(description)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class DeviceInfoDialog(QDialog):
    """Dialog to display connected camera information."""
    
    def __init__(
        self, camera_name: str, camera_info: dict, parent=None, language: str = "en"
    ):
        """
        Initialize device info dialog.
        
        Args:
            camera_name: Name of the camera
            camera_info: Dictionary with camera information
            parent: Parent widget
        """
        super().__init__(parent)
        self.language = language
        self.setWindowTitle(f"Camera Information - {camera_name}")
        self.setModal(True)
        self.setGeometry(200, 200, 400, 300)
        self.setMinimumWidth(400)
        
        self._init_ui(camera_name, camera_info)
        apply_language(self, language)
    
    def _init_ui(self, camera_name: str, camera_info: dict) -> None:
        """Initialize user interface."""
        layout = QVBoxLayout(self)
        
        title = QLabel(f"<b>{camera_name}</b>")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        
        info_content = f"""
<b>Camera Information</b>

Port: {camera_info.get('port', 'Unknown')}
Baud Rate: {camera_info.get('baudrate', 'Unknown')} bps
Status: {camera_info.get('status', 'Unknown')}
Model: {camera_info.get('model', 'Unknown')}
Firmware: {camera_info.get('firmware', 'Unknown')}

<b>Pan/Tilt Range</b>
Pan: {camera_info.get('pan_range', 'N/A')}
Tilt: {camera_info.get('tilt_range', 'N/A')}

<b>Zoom Range</b>
{camera_info.get('zoom_range', 'N/A')}

<b>Features</b>
Focus: {camera_info.get('focus_support', 'Auto/Manual')}
Iris: {camera_info.get('iris_support', 'Yes')}
White Balance: {camera_info.get('wb_support', 'Yes')}
Presets: {camera_info.get('presets', 8)}
        """
        if self.language == "es":
            for english, spanish in (
                ("Camera Information", "Información de la cámara"),
                ("Baud Rate", "Velocidad en baudios"),
                ("Status", "Estado"),
                ("Model", "Modelo"),
                ("Firmware", "Firmware"),
                ("Pan/Tilt Range", "Rango de paneo/inclinación"),
                ("Pan", "Paneo"),
                ("Tilt", "Inclinación"),
                ("Zoom Range", "Rango de zoom"),
                ("Features", "Funciones"),
                ("Focus", "Enfoque"),
                ("White Balance", "WB"),
                ("Presets", "Preajustes"),
            ):
                info_content = info_content.replace(english, spanish)
        
        info_text.setHtml(info_content)
        layout.addWidget(info_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
