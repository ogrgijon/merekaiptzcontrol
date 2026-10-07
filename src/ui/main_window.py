"""
Main Application Window

PyQt6 main window for MerekaiPTZControl.
"""

import logging
import sys
from typing import Optional

from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QIcon
from PyQt6.QtWidgets import (QComboBox, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QMainWindow, QMenu, QMenuBar, QMessageBox,
                             QPushButton, QSizePolicy, QSplitter, QStatusBar,
                             QVBoxLayout, QWidget)

from src.camera.camera_device import CameraStatus
from src.camera.camera_manager import CameraManager
from src.app_paths import resource_path
from src.config.settings import Settings

from .control_panel import ControlPanel
from .dialogs import AboutDialog, SettingsDialog
from .i18n import apply_language, translate
from .preset_manager import PresetManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window for MerekaiPTZControl."""

    # Signals
    camera_connected = pyqtSignal(str)
    camera_disconnected = pyqtSignal(str)

    def __init__(self):
        """Initialize main window."""
        super().__init__()

        self.settings = Settings()
        self.camera_manager = CameraManager()
        self.control_panel: Optional[ControlPanel] = None
        self.preset_manager: Optional[PresetManager] = None
        self.camera_buttons: dict[str, QPushButton] = {}

        self.setWindowTitle("MerekaiPTZControl - PTZ Camera Control")
        self.setWindowIcon(QIcon(str(resource_path("resources/merekaiptzcontrol.png"))))
        self.setMinimumSize(QSize(270, 700))
        self.setGeometry(100, 0, 270, 1080)

        self._init_menu_bar()
        self._init_ui()
        self._apply_ccu_style()
        self._connect_signals()
        if self.control_panel:
            self.control_panel.retranslate()
        if self.preset_manager:
            self.preset_manager.retranslate()
        apply_language(self, self.settings.get("language", "en"))

        logger.info("Main window initialized")

    def _apply_ccu_style(self) -> None:
        """Apply the compact broadcast CCU visual treatment."""
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #111416; color: #d7dcda; }
            QMenuBar { background: #1b2022; color: #d7dcda; border-bottom: 1px solid #3a4244; }
            QMenuBar::item:selected, QMenu::item:selected { background: #2d383a; }
            QGroupBox { margin-top: 6px; border: 1px solid #3b4547; border-radius: 2px; padding: 7px 4px 4px; font-weight: 700; color: #b7c1bd; }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #e1b455; }
            QPushButton { min-height: 22px; background: #252c2e; border: 1px solid #4b5658; border-radius: 2px; color: #e4e8e6; padding: 1px 4px; }
            QPushButton:hover { background: #334043; border-color: #e1b455; }
            QPushButton:pressed { background: #1a1f20; border-color: #d88445; }
            QPushButton:checked { background: #5a4a1f; border-color: #e1b455; color: #ffffff; }
            QPushButton:disabled { color: #697170; background: #191d1e; border-color: #2b3233; }
            QComboBox, QSpinBox, QDoubleSpinBox { min-height: 24px; background: #1b2022; border: 1px solid #4b5658; padding: 1px 4px; }
            QSlider::groove:horizontal { height: 5px; background: #3b4547; }
            QSlider::handle:horizontal { width: 14px; margin: -5px 0; background: #e1b455; border-radius: 2px; }
            QStatusBar { background: #0b0d0e; color: #9ba7a2; border-top: 1px solid #3a4244; }
            QTabBar::tab { background: #1b2022; padding: 8px 18px; border: 1px solid #3b4547; }
            QTabBar::tab:selected { background: #2d383a; color: #e1b455; }
        """)

    def _init_menu_bar(self) -> None:
        """Initialize menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self._on_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _init_ui(self) -> None:
        """Initialize user interface."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Connection panel: one "Add Camera" button plus a matrix of added cameras
        connection_layout = QVBoxLayout()
        connection_buttons = QHBoxLayout()

        self.add_camera_btn = QPushButton("Add Camera")
        self.add_camera_btn.setToolTip("Add a camera from the available cameras list")
        self.add_camera_btn.clicked.connect(self._on_add_camera)
        connection_buttons.addWidget(self.add_camera_btn)

        self.device_info_btn = QPushButton("Device Info")
        self.device_info_btn.clicked.connect(self._on_device_info)
        self.device_info_btn.setEnabled(False)
        connection_buttons.addWidget(self.device_info_btn)
        connection_layout.addLayout(connection_buttons)

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red;")
        connection_layout.addWidget(self.status_label)

        self.camera_matrix_layout = QGridLayout()
        connection_layout.addLayout(self.camera_matrix_layout)
        main_layout.addLayout(connection_layout)
        # Keep presets visible above the scrollable camera controls.
        self.control_panel = ControlPanel(self.camera_manager, self.settings)
        self.preset_manager = PresetManager(self.camera_manager, self.settings)
        self.preset_manager.control_panel = self.control_panel
        self.control_panel.control_changed.connect(
            self.preset_manager.track_control_change
        )
        self.preset_manager.restore_controls.connect(
            self.control_panel.apply_saved_control_state
        )

        workspace_splitter = QSplitter(Qt.Orientation.Vertical)
        workspace_splitter.setChildrenCollapsible(False)
        workspace_splitter.addWidget(self.preset_manager)
        workspace_splitter.addWidget(self.control_panel)
        workspace_splitter.setStretchFactor(0, 0)
        workspace_splitter.setStretchFactor(1, 1)
        workspace_splitter.setSizes([240, 710])
        main_layout.addWidget(workspace_splitter)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(
            translate("Ready", self.settings.get("language", "en"))
        )

    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        self.camera_connected.connect(self._on_camera_connected)
        self.camera_disconnected.connect(self._on_camera_disconnected)

    def _on_add_camera(self) -> None:
        """Show available cameras and add the chosen one to the camera matrix."""
        ports = self.camera_manager.get_available_ports()
        menu = QMenu(self)
        for index, port in enumerate(ports, start=1):
            if self._camera_name(port) in self.camera_buttons:
                continue
            label = port.split("|", 1)[1] if "|" in port else port
            camera_label = translate("Camera {index}: {label}", self.settings.get("language", "en"))
            action = menu.addAction(camera_label.format(index=index, label=label))
            action.setData(port)
        if menu.isEmpty():
            message = "No new cameras available" if ports else "No cameras found"
            self.statusBar.showMessage(translate(message, self.settings.get("language", "en")))
            return
        chosen = menu.exec(
            self.add_camera_btn.mapToGlobal(self.add_camera_btn.rect().bottomLeft())
        )
        if not chosen:
            return
        port = chosen.data()
        camera_name = self._camera_name(port)
        if camera_name not in self.camera_manager.list_cameras():
            if not self.camera_manager.add_camera(
                camera_name, port, self.settings.get("camera_baudrate", 115200)
            ):
                QMessageBox.critical(
                    self,
                    translate("Camera Error", self.settings.get("language", "en")),
                    translate(
                        "Could not create the camera controller.",
                        self.settings.get("language", "en"),
                    ),
                )
                return
        label = port.split("|", 1)[1] if "|" in port else port
        button = QPushButton(label)
        button.setCheckable(True)
        button.setMinimumHeight(36)
        button.setMinimumWidth(0)
        button.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        button.setToolTip(label)
        button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        button.clicked.connect(
            lambda checked=False, name=camera_name: self._on_camera_clicked(name)
        )
        button.customContextMenuRequested.connect(
            lambda pos, name=camera_name: self._on_camera_context_menu(name, pos)
        )
        self.camera_buttons[camera_name] = button
        position = len(self.camera_buttons) - 1
        self.camera_matrix_layout.addWidget(button, position // 2, position % 2)
        self._on_camera_clicked(camera_name)

    def _on_camera_clicked(self, camera_name: str) -> None:
        """Select a camera from the matrix and connect it automatically."""
        camera = self.camera_manager.get_camera(camera_name)
        if not camera:
            return
        if not camera.is_connected() and not self.camera_manager.connect_camera(camera_name):
            QMessageBox.critical(
                self,
                translate("Connection Failed", self.settings.get("language", "en")),
                translate(
                    "Could not connect to {camera}",
                    self.settings.get("language", "en"),
                ).format(camera=camera_name),
            )
            self._update_camera_buttons()
            return
        self.camera_manager.set_active_camera(camera_name)
        self.camera_connected.emit(camera_name)

    def _on_camera_context_menu(self, camera_name: str, pos) -> None:
        """Offer disconnect/remove for a camera button."""
        button = self.camera_buttons[camera_name]
        menu = QMenu(self)
        disconnect_action = menu.addAction("Disconnect")
        remove_action = menu.addAction("Remove")
        chosen = menu.exec(button.mapToGlobal(pos))
        if chosen == disconnect_action:
            self.camera_manager.disconnect_camera(camera_name)
            self.camera_disconnected.emit(camera_name)
        elif chosen == remove_action:
            self.camera_manager.remove_camera(camera_name)
            self.camera_buttons.pop(camera_name).deleteLater()
            for position, widget in enumerate(self.camera_buttons.values()):
                self.camera_matrix_layout.addWidget(widget, position // 2, position % 2)
            self.camera_disconnected.emit(camera_name)

    def _update_camera_buttons(self) -> None:
        """Reflect active/connected state in the camera matrix."""
        for name, button in self.camera_buttons.items():
            camera = self.camera_manager.get_camera(name)
            button.setChecked(name == self.camera_manager.active_camera)
            connected = bool(camera and camera.is_connected())
            button.setStyleSheet("" if connected else "color: #8a9390;")

    @staticmethod
    def _camera_name(port_data: str) -> str:
        """Return the stable manager key for a discovered camera."""
        return f"Camera_{port_data.replace('/', '_').replace(':', '_')}"

    def _on_camera_connected(self, camera_name: str) -> None:
        """Handle camera connected signal."""
        language = self.settings.get("language", "en")
        self.status_label.setText(translate("Status: Connected", language))
        self.status_label.setStyleSheet("color: green;")
        self.device_info_btn.setEnabled(True)
        self.statusBar.showMessage(
            translate("Connected to {camera}", language).format(camera=camera_name)
        )
        self._update_camera_buttons()

        camera = self.camera_manager.get_active_camera()
        if self.control_panel:
            self.control_panel.enable_controls()
            self.control_panel.apply_capabilities(getattr(camera, "capabilities", {}))
            self.control_panel.refresh_camera_state(camera)
        if self.preset_manager:
            self.preset_manager.apply_capabilities(
                getattr(camera, "capabilities", {}), camera_name
            )

    def _on_camera_disconnected(self, camera_name: str) -> None:
        """Handle camera disconnected signal."""
        self._update_camera_buttons()
        if self.camera_manager.get_active_camera():
            return
        language = self.settings.get("language", "en")
        self.status_label.setText(translate("Status: Disconnected", language))
        self.status_label.setStyleSheet("color: red;")
        self.device_info_btn.setEnabled(False)
        self.statusBar.showMessage(translate("Disconnected", language))

        if self.control_panel:
            self.control_panel.disable_controls()
        if self.preset_manager:
            self.preset_manager.apply_capabilities({}, None)
    def _on_settings(self) -> None:
        """Handle settings menu action."""
        settings_dialog = SettingsDialog(self.settings, self)
        settings_dialog.settings_changed.connect(self._on_settings_changed)
        settings_dialog.exec()

    def _on_settings_changed(self, new_settings: dict) -> None:
        """Handle settings change."""
        logger.info(f"Settings updated: {new_settings}")

        # Update control panel with new settings
        if self.control_panel:
            self.control_panel.update_settings(new_settings)
            self.control_panel.retranslate()

        # Update preset manager with new preset count
        if self.preset_manager:
            max_presets = new_settings.get("max_presets", 8)
            self.preset_manager.MAX_PRESETS = max_presets
            self.preset_manager.retranslate()
        language = self.settings.get("language", "en")
        self.statusBar.showMessage(translate(self.statusBar.currentMessage(), language))
        apply_language(self, language)

    def _on_device_info(self) -> None:
        """Show device information dialog."""
        camera = self.camera_manager.get_active_camera()

        if not camera:
            language = self.settings.get("language", "en")
            QMessageBox.warning(
                self,
                translate("No Camera", language),
                translate("Please connect a camera first.", language),
            )
            return

        capabilities = getattr(camera, "capabilities", {})
        camera_info = {
            "device": getattr(camera, "display_name", "Camera"),
            "transport": (
                "Windows UVC"
                if getattr(camera, "capabilities", {}).get("uvc_standard")
                else camera.__class__.__name__
            ),
            "status": camera.status.value,
            "model": getattr(camera, "display_name", "Unknown camera"),
            "firmware": "Unknown",
            "pan_range": "Standard UVC",
            "tilt_range": "Standard UVC",
            "zoom_range": "Standard UVC",
            "focus_support": "Yes" if capabilities.get("focus") else "No",
            "iris_support": "Yes" if capabilities.get("iris") else "No",
            "wb_support": "Yes" if capabilities.get("white_balance") else "No",
            "presets": (
                self.settings.get("max_presets", 8)
                if capabilities.get("presets")
                else (
                    f"{self.settings.get('max_presets', 8)} (software)"
                    if capabilities.get("pan_tilt") or capabilities.get("zoom")
                    else "Not supported"
                )
            ),
        }

        from .dialogs import DeviceInfoDialog

        dialog = DeviceInfoDialog(
            self.camera_manager.active_camera or "Camera",
            camera_info,
            self,
            self.settings.get("language", "en"),
        )
        dialog.exec()

    def _on_about(self) -> None:
        """Show about dialog."""
        dialog = AboutDialog(self, self.settings.get("language", "en"))
        dialog.exec()

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        self.camera_manager.disconnect_all()
        self.settings.save()
        logger.info("Application closed")
        event.accept()
