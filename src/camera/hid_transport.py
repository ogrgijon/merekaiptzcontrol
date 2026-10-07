"""
HID Transport for USB PTZ Cameras

Implements HID protocol for USB USB PTZ cameras (PTZ PRO, PTZ PRO 2, RALLY).
Uses report ID 0x0B with 32-byte HID reports.

HID Command Protocol:
  Report ID: 0x0B
  Command Codes:
    0x00 = Tilt Up
    0x01 = Tilt Down
    0x02 = Pan Right
    0x03 = Pan Left
    0x04 = Zoom In (Telephoto)
    0x05 = Zoom Out (Wide)

Speed Control:
  Speed parameter is informational only. The UI layer (AutoRepeatButton)
  controls actual speed by adjusting how often commands are sent.
  Speed 1 = slow (commands sent every 300ms)
  Speed 7 = fast (commands sent every 25ms)
"""

import logging
from typing import List, Optional

import hid

from .models import (CAMERA_MODELS, CameraCapabilities, CameraModel,
                     CameraProtocol, find_model_by_usb_id,
                     get_camera_capabilities)
from .transport import CameraTransport, CommandResult

logger = logging.getLogger(__name__)


class HidTransport(CameraTransport):
    """
    HID transport for USB PTZ cameras.
    
    Supports:
    - PTZ PRO (USB ID: 0x046D:0x086E)
    - PTZ PRO 2 (USB ID: 0x046D:0x085F)
    - RALLY (USB ID: 0x046D:0x086A)
    
    Protocol: USB HID report ID 0x0B, 32-byte report format
    """
    
    # USB Vendor and Product IDs
    SUPPORTED_VENDOR_ID = 0x046D
    PTZ_PRO_PID = 0x086E
    PTZ_PRO_2_PID = 0x085F
    RALLY_PID = 0x086A
    
    # HID Protocol Constants
    PTZ_REPORT_ID = 0x0B
    REPORT_SIZE = 32
    HID_TIMEOUT_MS = 5000
    
    # HID Command Codes
    CMD_TILT_UP = 0x00
    CMD_TILT_DOWN = 0x01
    CMD_PAN_RIGHT = 0x02
    CMD_PAN_LEFT = 0x03
    CMD_ZOOM_IN = 0x04
    CMD_ZOOM_OUT = 0x05
    
    # Speed Mapping: Speed Level (1-7) → Command Interval (milliseconds)
    # Higher speed = shorter interval = more frequent commands
    # These values are tuned for smooth, responsive camera movement
    SPEED_TO_INTERVAL_MS = {
        1: 300,  # 300ms between commands (slowest)
        2: 200,
        3: 150,
        4: 100,  # Default speed
        5: 75,
        6: 50,
        7: 25,   # 25ms between commands (fastest)
    }
    
    def __init__(self, device_path: bytes):
        """
        Initialize HID transport.
        
        Args:
            device_path: HID device path (from hid.enumerate)
        """
        super().__init__()
        self.device_path = device_path
        self.device: Optional[hid.device] = None
        
        # Detect camera model
        self._detect_model()
        
        # Set display name
        if self.model != CameraModel.UNKNOWN:
            model_def = CAMERA_MODELS.get(self.model)
            if model_def:
                self.display_name = model_def["name"]
    
    def _detect_model(self) -> None:
        """
        Detect camera model from USB device IDs.
        
        Gets VID/PID from the device path via hid.enumerate().
        """
        try:
            # Find device info by matching paths
            vendor_id = None
            product_id = None
            
            for device_info in hid.enumerate():
                if device_info.get("path") == self.device_path:
                    vendor_id = device_info.get("vendor_id")
                    product_id = device_info.get("product_id")
                    break
            
            if vendor_id is None or product_id is None:
                logger.warning(f"Could not find VID/PID for device path {self.device_path[:8]}...")
                self.model = CameraModel.UNKNOWN
                return
            
            # Map USB IDs to camera model
            if vendor_id == self.SUPPORTED_VENDOR_ID:
                self.model = find_model_by_usb_id(vendor_id, product_id)
                
                # Load camera capabilities
                if self.model != CameraModel.UNKNOWN:
                    self.capabilities = get_camera_capabilities(self.model)
                    logger.info(
                        f"Detected USB camera: {self.model.value} "
                        f"(USB {vendor_id:04X}:{product_id:04X})"
                    )
            else:
                logger.warning(f"Device is not a USB camera (VID {vendor_id:04X})")
                self.model = CameraModel.UNKNOWN
        
        except Exception as e:
            logger.warning(f"Could not detect camera model: {e}")
            self.model = CameraModel.UNKNOWN
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    def connect(self) -> bool:
        """
        Establish connection to HID device.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try using open_path first (most compatible)
            self.device = hid.device()
            self.device.open_path(self.device_path)
            self.connected = True
            
            logger.info(
                f"Connected to {self.model.value} via HID "
                f"({self.device_path[:8] if isinstance(self.device_path, bytes) else str(self.device_path)[:8]}...)"
            )
            return True
        
        except Exception as e:
            logger.warning(f"open_path failed, trying open(vendor_id, product_id): {e}")
            try:
                # Fallback: use open with VID/PID (like PyPTZPro does)
                self.device = hid.device()
                self.device.open(self.SUPPORTED_VENDOR_ID, self.PTZ_PRO_2_PID)  # Try PTZ PRO 2 first
                self.connected = True
                logger.info(f"Connected to {self.model.value} via HID (VID/PID fallback)")
                return True
            except Exception as e2:
                logger.error(f"Both connection methods failed: {e2}")
                self.connected = False
                self.device = None
                return False
    
    def disconnect(self) -> None:
        """Disconnect from HID device."""
        # Close HID device
        if self.device:
            try:
                self.device.close()
            except Exception as e:
                logger.warning(f"Error closing HID device: {e}")
        
        self.device = None
        self.connected = False
        logger.info(f"Disconnected from {self.model.value}")
    
    def is_connected(self) -> bool:
        """
        Check if currently connected to camera.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected and self.device is not None
    
    # =========================================================================
    # Pan/Tilt Control
    # =========================================================================
    
    def pan_tilt_relative(
        self,
        pan_speed: int,
        tilt_speed: int,
        pan_move: int,
        tilt_move: int
    ) -> CommandResult:
        """
        Send relative pan/tilt command.
        
        Sends a single command each time. The caller (UI) is responsible for
        calling this repeatedly to achieve continuous movement.
        
        Args:
            pan_speed: Pan speed (1-7 or 1-24, where 7/24 is fastest) - for info only
            tilt_speed: Tilt speed (1-7 or 1-24, where 7/24 is fastest) - for info only
            pan_move: Pan direction (negative=left, positive=right, 0=stop)
            tilt_move: Tilt direction (negative=down, positive=up, 0=stop)
        
        Returns:
            CommandResult with success status
        """
        if not self.is_connected():
            return CommandResult(success=False, error="Not connected to camera")
        
        success = True
        
        # Send tilt command if needed
        if tilt_move < 0:
            success &= self._send_command(self.CMD_TILT_DOWN)
        elif tilt_move > 0:
            success &= self._send_command(self.CMD_TILT_UP)
        
        # Send pan command if needed
        if pan_move > 0:
            success &= self._send_command(self.CMD_PAN_RIGHT)
        elif pan_move < 0:
            success &= self._send_command(self.CMD_PAN_LEFT)
        
        if success:
            return CommandResult(success=True)
        else:
            return CommandResult(success=False, error="Failed to send pan/tilt command")
    
    def pan_tilt_absolute(
        self,
        pan_speed: int,
        tilt_speed: int,
        pan_pos: int,
        tilt_pos: int
    ) -> CommandResult:
        """
        Absolute pan/tilt not supported by HID protocol.
        
        Returns:
            CommandResult with error message
        """
        return CommandResult(
            success=False,
            error="HID protocol does not support absolute pan/tilt positioning"
        )
    
    # =========================================================================
    # Zoom Control
    # =========================================================================
    
    def zoom_relative(self, speed: int, direction: int) -> CommandResult:
        """
        Send relative zoom command.
        
        Sends a single command each time. The caller (UI) is responsible for
        calling this repeatedly to achieve continuous zoom.
        
        Args:
            speed: Zoom speed (1-7 or 1-24, where 7/24 is fastest) - for info only
            direction: Zoom direction (positive=in, negative=out, 0=stop)
        
        Returns:
            CommandResult with success status
        """
        if not self.is_connected():
            return CommandResult(success=False, error="Not connected to camera")
        
        if direction == 0:
            return CommandResult(success=True)
        
        # Send zoom command
        cmd = self.CMD_ZOOM_IN if direction > 0 else self.CMD_ZOOM_OUT
        
        if self._send_command(cmd):
            return CommandResult(success=True)
        else:
            return CommandResult(success=False, error="Failed to send zoom command")
    
    def zoom_absolute(self, position: int) -> CommandResult:
        """
        Absolute zoom not supported by HID protocol.
        
        Returns:
            CommandResult with error message
        """
        return CommandResult(
            success=False,
            error="HID protocol does not support absolute zoom positioning"
        )
    
    # =========================================================================
    # Internal Methods
    # =========================================================================
    
    def _send_command(self, command_code: int) -> bool:
        """
        Send raw HID command.
        
        Args:
            command_code: Command code (0x00-0x05)
        
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.device:
            return False
        
        try:
            # Build HID report
            report = [0] * self.REPORT_SIZE
            report[0] = self.PTZ_REPORT_ID
            report[1] = command_code & 0xFF
            
            # Send report
            bytes_written = self.device.write(report)
            return bytes_written > 0
        
        except Exception as e:
            logger.error(f"HID command failed (0x{command_code:02X}): {e}")
            return False
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Optional[dict]:
        """
        HID protocol doesn't support status polling.
        
        Returns:
            None (status not available)
        """
        return None


def list_hid_cameras() -> List[dict]:
    """
    List all connected USB HID PTZ cameras.
    
    Returns:
        List of camera information dictionaries
    """
    cameras = []
    
    try:
        for device in hid.enumerate(HidTransport.SUPPORTED_VENDOR_ID):
            # Check for PTZ cameras (usage page 0x0C = consumer control)
            if device.get("usage_page") != 0x0C:
                continue
            
            # Get product ID and map to model
            product_id = device.get("product_id")
            model = find_model_by_usb_id(HidTransport.SUPPORTED_VENDOR_ID, product_id)
            
            cameras.append({
                "model": model,
                "model_name": CAMERA_MODELS.get(model, {}).get("name", "Unknown"),
                "path": device["path"],
                "vendor_id": device.get("vendor_id"),
                "product_id": product_id,
                "product_string": device.get("product_string", "USB PTZ Camera"),
                "manufacturer_string": device.get("manufacturer_string", "USB"),
            })
    
    except Exception as e:
        logger.error(f"Failed to enumerate HID cameras: {e}")
    
    return cameras
