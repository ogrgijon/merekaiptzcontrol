import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QInputDialog

from src.ui.control_panel import ControlPanel
from src.ui.i18n import apply_language


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


class FakeSettings:
    def __init__(self, values=None):
        self.values = values or {}
        self.saved = False

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def save(self):
        self.saved = True


class FakeCameraManager:
    def get_active_camera(self):
        return None


def test_setting_reset_restores_default_slider_value(qt_app):
    panel = ControlPanel(FakeCameraManager(), FakeSettings())
    panel.enable_controls()
    panel.apply_capabilities({"brightness": True})
    panel.range_sliders["brightness"].setValue(22)

    panel._reset_setting("brightness")

    assert panel.range_sliders["brightness"].value() == 50
    assert panel._summary_values["brightness"] == "50"
    panel.close()


def test_global_reset_emits_ptz_reset_and_restores_supported_controls(qt_app):
    panel = ControlPanel(FakeCameraManager(), FakeSettings())
    panel.enable_controls()
    panel.apply_capabilities(
        {
            "pan_tilt": True,
            "zoom": True,
            "focus": True,
            "brightness": True,
        }
    )
    panel.range_sliders["brightness"].setValue(20)
    changes = []
    panel.control_changed.connect(lambda key, value: changes.append((key, value)))

    panel._reset_all_controls()

    assert panel.range_sliders["brightness"].value() == 50
    assert panel.pan_tilt_speed_spin.value() == 15
    assert ("reset_ptz", None) in changes
    assert panel._summary_values["focus"] == "auto"
    panel.close()


def test_zoom_home_button_and_no_pan_tilt_default_button(qt_app):
    panel = ControlPanel(FakeCameraManager(), FakeSettings())

    assert panel.zoom_default_btn.text() == "Home"
    assert panel.focus_default_btn.text() == "Home"
    assert not hasattr(panel, "pan_speed_default_btn")
    panel.close()


def test_spanish_setting_tiles_localize_defaults_but_keep_custom_names(qt_app):
    settings = FakeSettings(
        {
            "language": "es",
            "camera_setting_matrix_names": {"brightness": "Luz de sala"},
        }
    )
    panel = ControlPanel(FakeCameraManager(), settings)

    assert panel._summary_buttons["exposure"].text() == "Exposición: 0.0"
    assert panel._summary_buttons["white_balance"].text() == "WB: auto"
    assert panel._summary_buttons["brightness"].text() == "Luz de sala: 50"
    assert panel.editor_group.title() == "Ajustar Exposición"
    apply_language(panel, "es")
    assert panel.pan_home_btn.text() == "INICIO"
    assert panel.zoom_wide_btn.text() == "ANCHO"
    assert panel.focus_near_btn.text() == "CERCA"
    assert panel.iris_open_btn.text() == "ABRIR"

    settings.values["language"] = "en"
    panel.retranslate()
    apply_language(panel, "en")

    assert panel._summary_buttons["exposure"].text() == "Exposure: 0.0"
    assert panel._summary_buttons["brightness"].text() == "Luz de sala: 50"
    assert panel.pan_home_btn.text() == "HOME"
    panel.close()


def test_camera_setting_value_color_tracks_rainbow_range(qt_app):
    panel = ControlPanel(FakeCameraManager(), FakeSettings())
    button = panel._summary_buttons["brightness"]

    panel._set_summary("brightness", "0")
    minimum_color = button.styleSheet()
    panel._set_summary("brightness", "100")
    maximum_color = button.styleSheet()

    assert "padding: 2px 0px" in maximum_color
    assert button.minimumHeight() == 56
    assert "color:" in minimum_color
    assert minimum_color != maximum_color
    panel.close()


def test_matrix_value_precedes_name_and_double_click_renames_persistently(
    qt_app, monkeypatch
):
    settings = FakeSettings()
    panel = ControlPanel(FakeCameraManager(), settings)
    button = panel._summary_buttons["brightness"]
    monkeypatch.setattr(
        QInputDialog,
        "getText",
        lambda *args, **kwargs: ("Room Light", True),
    )

    panel._rename_summary_setting("brightness")

    assert button.text() == "Room Light: 50"
    assert settings.get("camera_setting_matrix_names")["brightness"] == "Room Light"
    assert settings.saved
    panel.close()


def test_camera_setting_click_selects_editor_while_disconnected(qt_app):
    panel = ControlPanel(FakeCameraManager(), FakeSettings())

    panel._summary_buttons["brightness"].click()

    assert panel._selected_setting == "brightness"
    assert panel.editor_group.title() == "Adjust Brightness"
    panel.close()


def test_camera_setting_disable_state_is_persistent(qt_app):
    settings = FakeSettings()
    panel = ControlPanel(FakeCameraManager(), settings)

    panel._summary_disabled.add("brightness")
    panel._refresh_summary("brightness")
    panel._save_disabled_summary_settings()

    assert settings.get("camera_setting_matrix_disabled")["default"] == [
        "brightness"
    ]
    assert panel._summary_buttons["brightness"].property("matrix_disabled")
    panel.close()
