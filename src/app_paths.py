"""Application paths for source runs and frozen Windows builds."""

import os
import sys
from pathlib import Path


def app_data_dir() -> Path:
    """Return the writable directory for settings, presets, and logs."""
    if getattr(sys, "frozen", False):
        local_app_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local_app_data / "MerekaiPTZControl"
    return Path("dev")


def resource_path(relative_path: str) -> Path:
    """Resolve a bundled resource in source mode or a PyInstaller build."""
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return bundle_dir / relative_path
