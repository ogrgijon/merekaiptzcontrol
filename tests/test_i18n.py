import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow

from src.ui.dialogs import SettingsDialog
from src.ui.i18n import apply_language, translate


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


class FakeSettings:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def reset_to_defaults(self):
        self.values = {"language": "en"}


def test_translation_can_switch_languages(qt_app):
    label = QLabel("Add Camera")

    apply_language(label, "es")
    assert label.text() == "Añadir cámara"

    apply_language(label, "en")
    assert label.text() == "Add Camera"


def test_language_switch_retranslates_menus_and_actions(qt_app):
    window = QMainWindow()
    menu = window.menuBar().addMenu("&File")
    action = menu.addAction("&Settings")

    apply_language(window, "es")
    assert menu.title() == "&Archivo"
    assert action.text() == "&Configuración"

    apply_language(window, "en")
    assert menu.title() == "&File"
    assert action.text() == "&Settings"


def test_settings_dialog_exposes_language_preference(qt_app):
    settings = FakeSettings({"language": "es"})
    dialog = SettingsDialog(settings)

    assert dialog.language_combo.currentData() == "es"
    assert dialog.use_extension_unit_motion_check.text() == "Usar control de movimiento Nativo"
    assert "USB" not in dialog.use_extension_unit_motion_check.toolTip()
    dialog.language_combo.setCurrentIndex(dialog.language_combo.findData("en"))
    assert dialog.get_settings()["language"] == "en"

    english_dialog = SettingsDialog(FakeSettings({"language": "en"}))
    assert english_dialog.use_extension_unit_motion_check.text() == "Use Native Motion Control"
    assert english_dialog.use_extension_unit_motion_check.toolTip() == (
        "Use camera-specific Native motion control if available"
    )

def test_language_translation_leaves_unknown_text_unchanged():
    assert translate("Camera model XYZ", "es") == "Camera model XYZ"


def test_requested_spanish_labels():
    assert translate("Reset All Controls", "es") == "Restablecer"
    assert translate("White Balance", "es") == "WB"
    assert translate("WB", "es") == "WB"
