import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from src.ui.preset_manager import PresetManager


@pytest.fixture(scope="module")
def qt_app():
    return QApplication.instance() or QApplication([])


class FakeCamera:
    def __init__(self):
        self.position = {"pan": 10000, "tilt": 20000, "zoom": 30000}
        self.absolute_calls = []
        self.relative_calls = []
        self.saved_presets = []
        self.recalled_presets = []

    def save_preset(self, slot):
        self.saved_presets.append(slot)
        return True

    def goto_preset(self, slot):
        self.recalled_presets.append(slot)
        return True

    def get_ptz_position(self):
        return self.position

    def pan_tilt_absolute(self, pan_speed, tilt_speed, pan, tilt):
        self.absolute_calls.append((pan, tilt))
        return True

    def zoom_absolute(self, zoom):
        self.absolute_calls.append(zoom)
        return True

    def pan_tilt_relative(self, pan_speed, tilt_speed, pan, tilt):
        self.relative_calls.append((pan, tilt))
        return True

    def pan_tilt_stop(self):
        return True

    def zoom_tele(self, speed):
        self.relative_calls.append(("zoom", 1))
        return True

    def zoom_wide(self, speed):
        self.relative_calls.append(("zoom", -1))
        return True

    def zoom_stop(self):
        return True


class FakeCameraManager:
    active_camera = "camera-a"

    def __init__(self):
        self.camera = FakeCamera()

    def get_active_camera(self):
        return self.camera


class FakeSettings:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)


class FakeControlPanel:
    def saved_control_state(self):
        return {"brightness": 61, "focus": "manual"}


def test_default_preset_names_are_translated_but_custom_names_are_preserved(
    qt_app, tmp_path, monkeypatch
):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    settings = FakeSettings({"language": "es"})
    presets = PresetManager(FakeCameraManager(), settings)
    presets.presets = {
        "slot_0": {"name": "Preset 1"},
        "slot_1": {"name": "Plano general"},
    }

    presets.retranslate()

    assert presets.slot_buttons[0].text() == "1: Preajuste 1"
    assert presets.slot_buttons[1].text() == "2: Plano general"
    assert presets.slot_buttons[2].text() == "3: Vacío"

    settings.values["language"] = "en"
    presets.retranslate()
    assert presets.slot_buttons[0].text() == "1: Preset 1"
    assert presets.slot_buttons[1].text() == "2: Plano general"
    presets.close()


def test_software_preset_saves_ptz_and_last_set_controls(
    qt_app, tmp_path, monkeypatch
):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    manager = FakeCameraManager()
    presets = PresetManager(manager, FakeSettings())
    presets.control_panel = FakeControlPanel()
    presets.apply_capabilities(
        {
            "pan_tilt": True,
            "pan_tilt_absolute": True,
            "zoom": True,
            "zoom_absolute": True,
            "presets": False,
        },
        "camera-a",
    )

    assert presets.save_mode_btn.isEnabled()
    presets.save_mode_btn.setChecked(True)
    presets._on_slot_clicked(0)

    saved = json.loads((tmp_path / "presets.json").read_text())
    state = saved["presets"]["slot_0"]["camera_states"]["camera-a"]
    assert state == {
        "hardware_preset": False,
        "position": {"x": 10000, "y": 20000, "z": 30000},
        "controls": {"brightness": 61, "focus": "manual"},
    }
    assert presets.save_mode_btn.isChecked() is False


def test_hardware_presets_are_used_when_camera_supports_them(
    qt_app, tmp_path, monkeypatch
):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    manager = FakeCameraManager()
    presets = PresetManager(manager, FakeSettings())
    presets.control_panel = FakeControlPanel()
    presets.apply_capabilities(
        {"pan_tilt": True, "zoom": True, "presets": True}, "camera-a"
    )
    restored = []
    presets.restore_controls.connect(restored.append)

    presets.save_mode_btn.setChecked(True)
    presets._on_slot_clicked(2)
    presets._on_slot_clicked(2)

    state = presets.presets["slot_2"]["camera_states"]["camera-a"]
    assert state["hardware_preset"] is True
    assert "position" not in state
    assert manager.camera.saved_presets == [2]
    assert manager.camera.recalled_presets == [2]
    assert restored == [{"brightness": 61, "focus": "manual"}]


def test_preset_recall_moves_to_saved_xyz_and_restores_controls(
    qt_app, tmp_path, monkeypatch
):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    manager = FakeCameraManager()
    presets = PresetManager(manager, FakeSettings())
    presets.apply_capabilities(
        {
            "pan_tilt": True,
            "pan_tilt_absolute": True,
            "zoom": True,
            "zoom_absolute": True,
        },
        "camera-a",
    )
    restored = []
    presets.restore_controls.connect(restored.append)
    presets.presets["slot_0"] = {
        "name": "Preset 1",
        "camera_states": {
            "camera-a": {
                "position": {"x": 10000, "y": 20000, "z": 30000},
                "controls": {"brightness": 61},
            }
        },
    }
    manager.camera.position = {"pan": 32768, "tilt": 32768, "zoom": 0}

    presets._on_slot_clicked(0)

    expected_pan = round(10000 * 4896 / 0xFFFF - 2448)
    expected_tilt = round(20000 * 2592 / 0xFFFF - 1296)
    assert manager.camera.absolute_calls == [
        (expected_pan, expected_tilt),
        30000,
    ]
    assert restored == [{"brightness": 61}]


def test_position_estimate_tracks_xyz_command_deltas(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    presets = PresetManager(FakeCameraManager(), FakeSettings())
    presets.apply_capabilities({"pan_tilt": True, "zoom": True}, "camera-a")
    presets.positions["camera-a"] = presets._center_position()

    presets.track_control_change("ptz_delta", (1, -1))
    presets.track_control_change("zoom_delta", 1)

    assert presets.positions["camera-a"] == {
        "x": 0x8000 + presets.POSITION_STEP,
        "y": 0x8000 - presets.POSITION_STEP,
        "z": presets.POSITION_STEP,
    }
    assert "X " in presets.position_label.text()
    presets._persist_timer.stop()


def test_reset_ptz_returns_supported_axes_to_defaults(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    manager = FakeCameraManager()
    presets = PresetManager(manager, FakeSettings())
    presets.apply_capabilities(
        {
            "pan_tilt": True,
            "pan_tilt_home": True,
            "zoom": True,
            "zoom_absolute": True,
        },
        "camera-a",
    )

    presets.track_control_change("reset_ptz", None)

    assert manager.camera.absolute_calls == [(0, 0), 0]
    assert presets.positions["camera-a"] == {"x": 0x8000, "y": 0x8000, "z": 0}


def test_zoom_default_does_not_move_pan_or_tilt(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    manager = FakeCameraManager()
    presets = PresetManager(manager, FakeSettings())
    presets.apply_capabilities(
        {
            "pan_tilt": True,
            "pan_tilt_absolute": True,
            "zoom": True,
            "zoom_absolute": True,
        },
        "camera-a",
    )

    presets.track_control_change("zoom_default", 0)

    assert manager.camera.absolute_calls == [0]
    assert presets.positions["camera-a"] == {"x": 10000, "y": 20000, "z": 0}


def test_relative_recall_queues_each_xyz_step(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    manager = FakeCameraManager()
    presets = PresetManager(manager, FakeSettings())
    presets.apply_capabilities({"pan_tilt": True, "zoom": True}, "camera-a")
    center = presets._center_position()
    manager.camera.position = {
        "pan": center["x"],
        "tilt": center["y"],
        "zoom": center["z"],
    }
    target = {
        "x": center["x"] + 2 * presets.POSITION_STEP,
        "y": center["y"] - presets.POSITION_STEP,
        "z": presets.POSITION_STEP,
    }

    presets._recall_state(manager.camera, "camera-a", {"position": target})

    assert presets._relative_moves == [
        (1, -1, 0),
        (1, 0, 0),
        (0, 0, 1),
    ]
    presets._move_timer.stop()
    presets._stop_timer.stop()


def test_relative_move_dispatches_next_xyz_step(qt_app, tmp_path, monkeypatch):
    monkeypatch.setattr(PresetManager, "PRESET_FILE", str(tmp_path / "presets.json"))
    manager = FakeCameraManager()
    presets = PresetManager(manager, FakeSettings())
    presets.apply_capabilities({"pan_tilt": True, "zoom": True}, "camera-a")
    presets._relative_moves = [(1, -1, 0)]

    presets._run_next_relative_move()

    assert manager.camera.relative_calls == [(100, -100)]
    assert presets._stop_timer.isActive()
    presets._move_timer.stop()
    presets._stop_timer.stop()
