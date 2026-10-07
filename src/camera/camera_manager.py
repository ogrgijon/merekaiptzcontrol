"""
Camera Manager

Manages multiple camera devices and provides high-level control interface.
"""

import logging
import sys
from typing import Dict, List, Optional

from .camera_device import CameraDevice, CameraStatus
from .usb_camera_backend import UvcBridge, UvcCameraDevice
from .v4l2_backend import (
    V4L2Camera,
    V4L2CameraDevice,
    list_cameras as list_v4l2_cameras,
)

logger = logging.getLogger(__name__)


class CameraManager:
    """Manages multiple PTZ camera devices."""

    def __init__(self):
        """Initialize camera manager."""
        self.cameras: Dict[str, object] = {}
        self.active_camera: Optional[str] = None

    def get_available_ports(self) -> List[str]:
        """
        Get list of available serial ports.

        Returns:
            List of available serial port names
        """
        ports = []
        bridge = UvcBridge()
        if bridge.available:
            for index, name in enumerate(bridge.list_devices()):
                ports.append(f"uvc://{index}|{name}")

        if sys.platform.startswith("linux"):
            ports.extend(camera.port for camera in list_v4l2_cameras())

        logger.info(f"Found {len(ports)} available camera device(s)")
        return ports

    def add_camera(self, name: str, port: str, baudrate: int = 115200) -> bool:
        """
        Add a camera device.

        Args:
            name: Friendly name for camera
            port: Serial port identifier or HID identifier
            baudrate: Serial communication speed (for serial devices)

        Returns:
            True if camera added successfully
        """
        try:
            if name in self.cameras:
                logger.warning(f"Camera '{name}' already exists")
                return False

            if port.startswith(("uvc://",)):
                index, _, display_name = port.split("/", 2)[2].partition("|")
                camera = UvcCameraDevice(int(index), display_name or None)
            elif port.startswith("v4l2://"):
                device_path, _, display_name = port[len("v4l2://") :].partition("|")
                v4l2_camera = V4L2Camera(device_path, display_name or device_path)
                camera = V4L2CameraDevice(v4l2_camera)
            else:
                camera = CameraDevice(port, baudrate)

            self.cameras[name] = camera
            logger.info(f"Added camera '{name}' on port {port}")
            return True

        except Exception as e:
            logger.error(f"Failed to add camera: {e}")
            return False

    def remove_camera(self, name: str) -> bool:
        """
        Remove a camera device.

        Args:
            name: Camera name

        Returns:
            True if camera removed successfully
        """
        if name in self.cameras:
            camera = self.cameras[name]
            if camera.is_connected():
                camera.disconnect()
            del self.cameras[name]
            logger.info(f"Removed camera '{name}'")
            return True

        return False

    def connect_camera(self, name: str) -> bool:
        """
        Connect to a camera.

        Args:
            name: Camera name

        Returns:
            True if connection successful
        """
        if name not in self.cameras:
            logger.error(f"Camera '{name}' not found")
            return False

        camera = self.cameras[name]
        if camera.connect():
            self.active_camera = name
            logger.info(f"Connected to camera '{name}'")
            return True

        return False

    def disconnect_camera(self, name: str) -> bool:
        """
        Disconnect from a camera.

        Args:
            name: Camera name

        Returns:
            True if disconnection successful
        """
        if name not in self.cameras:
            return False

        camera = self.cameras[name]
        camera.disconnect()

        if self.active_camera == name:
            self.active_camera = None

        logger.info(f"Disconnected from camera '{name}'")
        return True

    def get_camera(self, name: str) -> Optional[CameraDevice]:
        """
        Get camera device by name.

        Args:
            name: Camera name

        Returns:
            CameraDevice or None if not found
        """
        return self.cameras.get(name)

    def get_active_camera(self) -> Optional[CameraDevice]:
        """
        Get currently active camera.

        Returns:
            Active CameraDevice or None
        """
        if self.active_camera and self.active_camera in self.cameras:
            return self.cameras[self.active_camera]
        return None

    def set_active_camera(self, name: str) -> bool:
        """
        Set active camera.

        Args:
            name: Camera name

        Returns:
            True if camera exists
        """
        if name in self.cameras:
            self.active_camera = name
            logger.info(f"Active camera set to '{name}'")
            return True

        return False

    def list_cameras(self) -> List[str]:
        """
        Get list of all camera names.

        Returns:
            List of camera names
        """
        return list(self.cameras.keys())

    def get_camera_status(self, name: str) -> Optional[CameraStatus]:
        """
        Get status of a camera.

        Args:
            name: Camera name

        Returns:
            CameraStatus or None if camera not found
        """
        camera = self.cameras.get(name)
        if camera:
            return camera.status
        return None

    def disconnect_all(self) -> None:
        """Disconnect all cameras."""
        for name in list(self.cameras.keys()):
            self.disconnect_camera(name)

        self.active_camera = None
        logger.info("Disconnected all cameras")
