import sys
from pathlib import Path

from src.app_paths import app_data_dir, resource_path


def test_source_app_data_dir_uses_dev(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert app_data_dir() == Path("dev")


def test_frozen_app_data_dir_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert app_data_dir() == tmp_path / "MerekaiPTZControl"


def test_resource_path_resolves_from_project_root(monkeypatch):
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    assert resource_path("resources/merekaiptzcontrol.png") == (
        Path(__file__).parents[1] / "resources" / "merekaiptzcontrol.png"
    )
