"""
Camera Device Interface

Provides high-level interface for communicating with PTZ cameras
over USB/Serial connection using VISCA protocol.
"""

import logging
from enum import Enum
from typing import Callable, Dict, Optional

import serial

from .visca_protocol import VISCAProtocol

logger = logging.getLogger(__name__)


DEFAULT_CAPABILITIES: Dict[str, bool] = {
    "pan_tilt": True,
    "pan_tilt_absolute": True,
    "zoom": True,
    "zoom_absolute": True,
    "focus": True,
    "iris": True,
    "white_balance": True,
    "exposure": True,
    "presets": False,
}


class CameraStatus(Enum):
    """Camera connection and operational status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class CameraDevice:
    """Interface for controlling a PTZ camera."""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        """
        Initialize camera device.
        
        Args:
            port: Serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            baudrate: Serial communication speed (default 115200)
            timeout: Serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port: Optional[serial.Serial] = None
        self.protocol = VISCAProtocol()
        self.status = CameraStatus.DISCONNECTED
        self._status_callback: Optional[Callable] = None
        self.capabilities = DEFAULT_CAPABILITIES.copy()

    @property
    def display_name(self) -> str:
        """Human-readable transport name for device information."""
        return f"Serial camera ({self.port})"
    
    def connect(self) -> bool:
        """
        Establish connection to camera.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.status = CameraStatus.CONNECTING
            self._notify_status()
            
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                rtscts=False,
                dsrdtr=False
            )
            
            if self.serial_port.is_open:
                logger.info(f"Connected to camera on {self.port}")
                self.status = CameraStatus.CONNECTED
                self._notify_status()
                return True
            else:
                raise Exception("Failed to open serial port")
                
        except Exception as e:
            logger.error(f"Failed to connect to camera: {e}")
            self.status = CameraStatus.ERROR
            self._notify_status()
            return False
    
    def disconnect(self) -> None:
        """Disconnect from camera."""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            logger.info(f"Disconnected from camera on {self.port}")
        
        self.status = CameraStatus.DISCONNECTED
        self._notify_status()
    
    def is_connected(self) -> bool:
        """Check if camera is connected."""
        return (self.serial_port is not None and 
                self.serial_port.is_open and 
                self.status == CameraStatus.CONNECTED)
    
    def send_command(self, command: bytes) -> bool:
        """
        Send VISCA command to camera.
        
        Args:
            command: VISCA command bytes
            
        Returns:
            True if command sent successfully
        """
        if not self.is_connected():
            logger.warning("Camera not connected, cannot send command")
            return False
        
        try:
            self.serial_port.write(command)
            self.serial_port.flush()
            logger.debug(f"Sent command: {command.hex()}")
            return True
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            self.status = CameraStatus.ERROR
            self._notify_status()
            return False
    
    def read_response(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """
        Read response from camera.
        
        Args:
            timeout: Read timeout in seconds (uses default if None)
            
        Returns:
            Response bytes or None if no response
        """
        if not self.is_connected():
            return None
        
        try:
            old_timeout = self.serial_port.timeout
            if timeout is not None:
                self.serial_port.timeout = timeout
            
            response = self.serial_port.read_until(b'\xff')
            
            if timeout is not None:
                self.serial_port.timeout = old_timeout
            
            if response:
                logger.debug(f"Received response: {response.hex()}")
                return response
            return None
            
        except serial.SerialTimeoutException:
            return None
        except Exception as e:
            logger.error(f"Failed to read response: {e}")
            return None
    
    def pan_tilt_absolute(self, pan_speed: int, tilt_speed: int,
                          pan_pos: int, tilt_pos: int) -> bool:
        """
        Move to absolute pan/tilt position.
        
        Args:
            pan_speed: Pan speed (1-24)
            tilt_speed: Tilt speed (1-24)
            pan_pos: Pan position (-2448 to 2448)
            tilt_pos: Tilt position (-1296 to 1296)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.pan_tilt_absolute(
            pan_speed, tilt_speed, pan_pos, tilt_pos
        )
        return self.send_command(command)
    
    def pan_tilt_relative(self, pan_speed: int, tilt_speed: int,
                          pan_move: int, tilt_move: int) -> bool:
        """
        Move relative to current pan/tilt position.
        
        Args:
            pan_speed: Pan speed (1-24)
            tilt_speed: Tilt speed (1-24)
            pan_move: Relative pan movement (-2448 to 2448)
            tilt_move: Relative tilt movement (-1296 to 1296)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.pan_tilt_relative(
            pan_speed, tilt_speed, pan_move, tilt_move
        )
        return self.send_command(command)
    
    def pan_tilt_stop(self) -> bool:
        """Stop pan/tilt movement."""
        command = self.protocol.pan_tilt_stop()
        return self.send_command(command)
    
    def zoom_absolute(self, zoom_pos: int) -> bool:
        """
        Set absolute zoom position.
        
        Args:
            zoom_pos: Zoom position (0x0000 to 0xFFFF)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.zoom_absolute(zoom_pos)
        return self.send_command(command)
    
    def zoom_tele(self, speed: int) -> bool:
        """
        Start zoom telephoto (zoom in).
        
        Args:
            speed: Zoom speed (0-7)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.zoom_tele(speed)
        return self.send_command(command)
    
    def zoom_wide(self, speed: int) -> bool:
        """
        Start zoom wide (zoom out).
        
        Args:
            speed: Zoom speed (0-7)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.zoom_wide(speed)
        return self.send_command(command)
    
    def zoom_stop(self) -> bool:
        """Stop zoom movement."""
        command = self.protocol.zoom_stop()
        return self.send_command(command)
    
    def focus_auto(self) -> bool:
        """Enable autofocus."""
        command = self.protocol.focus_auto()
        return self.send_command(command)
    
    def focus_manual(self) -> bool:
        """Enable manual focus."""
        command = self.protocol.focus_manual()
        return self.send_command(command)
    
    def focus_far(self, speed: int) -> bool:
        """
        Focus to far (infinity).
        
        Args:
            speed: Focus speed (0-7)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.focus_far(speed)
        return self.send_command(command)
    
    def focus_near(self, speed: int) -> bool:
        """
        Focus to near.
        
        Args:
            speed: Focus speed (0-7)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.focus_near(speed)
        return self.send_command(command)
    
    def focus_stop(self) -> bool:
        """Stop focus movement."""
        command = self.protocol.focus_stop()
        return self.send_command(command)
    
    def iris_open(self, speed: int) -> bool:
        """
        Open iris (increase brightness).
        
        Args:
            speed: Iris speed (0-7)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.iris_open(speed)
        return self.send_command(command)
    
    def iris_close(self, speed: int) -> bool:
        """
        Close iris (decrease brightness).
        
        Args:
            speed: Iris speed (0-7)
            
        Returns:
            True if command sent successfully
        """
        command = self.protocol.iris_close(speed)
        return self.send_command(command)
    
    def iris_stop(self) -> bool:
        """Stop iris adjustment."""
        command = self.protocol.iris_stop()
        return self.send_command(command)
    
    def white_balance_auto(self) -> bool:
        """Enable auto white balance."""
        command = self.protocol.white_balance_auto()
        return self.send_command(command)
    
    def white_balance_indoor(self) -> bool:
        """Set white balance to indoor preset."""
        command = self.protocol.white_balance_indoor()
        return self.send_command(command)
    
    def white_balance_outdoor(self) -> bool:
        """Set white balance to outdoor preset."""
        command = self.protocol.white_balance_outdoor()
        return self.send_command(command)
    
    def set_status_callback(self, callback: Callable) -> None:
        """
        Set callback function for status changes.
        
        Args:
            callback: Function to call when status changes
        """
        self._status_callback = callback
    
    def _notify_status(self) -> None:
        """Notify callback of status change."""
        if self._status_callback:
            try:
                self._status_callback(self.status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
