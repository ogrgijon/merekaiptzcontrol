"""MerekaiPTZControl: PyQt6 application for controlling compatible PTZ cameras."""

__version__ = "1.0.0"
__author__ = "MerekaiPTZControl contributors"
__license__ = "MIT"

from .config.settings import Settings
from .camera.camera_manager import CameraManager

__all__ = ["Settings", "CameraManager"]
