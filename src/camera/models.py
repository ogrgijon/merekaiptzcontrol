"""
Camera Model Registry and Capability Definitions

Defines supported USB camera models and their capabilities.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class CameraProtocol(Enum):
    """Supported camera communication protocols."""
    HID = "hid"                  # USB HID (USB PTZ cameras)
    VISCA_SERIAL = "visca_serial"  # Serial RS-232 VISCA
    VISCA_IP = "visca_ip"        # IP network VISCA (future)
    WINDOWS_XU = "windows_xu"    # Windows Extension Unit (DirectShow)


class CameraModel(Enum):
    """Supported camera models."""
    PTZ_PRO = "ptz_pro"
    PTZ_PRO_2 = "ptz_pro_2"
    RALLY = "rally"
    RALLY_BAR = "rally_bar"
    UNKNOWN = "unknown"


@dataclass
class CameraCapabilities:
    """Camera capability specification."""
    
    # Pan/Tilt capabilities
    pan_tilt: bool = False
    pan_speed_range: Tuple[int, int] = (0, 0)      # (min, max)
    tilt_speed_range: Tuple[int, int] = (0, 0)
    pan_position_range: Tuple[int, int] = (-2448, 2448)
    tilt_position_range: Tuple[int, int] = (-1296, 1296)
    
    # Zoom capabilities
    zoom: bool = False
    zoom_speed_range: Tuple[int, int] = (0, 0)
    zoom_position_range: Tuple[int, int] = (0, 100)  # 0-100%
    
    # Focus capabilities
    focus: bool = False
    focus_speed_range: Tuple[int, int] = (0, 0)
    auto_focus: bool = False
    focus_near_limit: int = 0
    
    # Iris capabilities
    iris: bool = False
    iris_speed_range: Tuple[int, int] = (0, 0)
    auto_iris: bool = False
    
    # White balance capabilities
    white_balance: bool = False
    white_balance_modes: List[str] = None  # ["auto", "indoor", "outdoor"]
    
    # Exposure capabilities
    exposure: bool = False
    exposure_range: Tuple[int, int] = (-12, 12)  # EV range
    
    # Preset capabilities
    presets: int = 0  # Number of preset positions (0 = not supported)
    
    # Advanced capabilities
    absolute_positioning: bool = False  # Pan/tilt absolute positioning
    status_polling: bool = False        # Can query camera status
    
    def __post_init__(self):
        """Initialize default values."""
        if self.white_balance_modes is None:
            self.white_balance_modes = []


# Camera Model Database
# These definitions document the capabilities of each supported camera model
CAMERA_MODELS: Dict[CameraModel, Dict] = {
    CameraModel.PTZ_PRO: {
        "name": "PTZ PRO",
        "usb_ids": [(0x046D, 0x086E)],
        "protocols": [CameraProtocol.HID, CameraProtocol.WINDOWS_XU],
        "capabilities": CameraCapabilities(
            # Pan/Tilt
            pan_tilt=True,
            pan_speed_range=(1, 7),
            tilt_speed_range=(1, 7),
            
            # Zoom
            zoom=True,
            zoom_speed_range=(1, 7),
            
            # Focus - NOT supported on PTZ PRO
            focus=False,
            
            # Iris - NOT supported
            iris=False,
            
            # White Balance - NOT supported
            white_balance=False,
            
            # Exposure - NOT supported
            exposure=False,
            
            # Presets - 8 positions
            presets=8,
            
            # Advanced
            absolute_positioning=False,
            status_polling=False,
        ),
        "hid_report_id": 0x0B,
        "hid_report_size": 32,
        "motor_interval_ms": 70,  # Default from C++ reference
    },
    
    CameraModel.PTZ_PRO_2: {
        "name": "PTZ PRO 2",
        "usb_ids": [(0x046D, 0x085F)],
        "protocols": [CameraProtocol.HID, CameraProtocol.WINDOWS_XU],
        "capabilities": CameraCapabilities(
            # Pan/Tilt
            pan_tilt=True,
            pan_speed_range=(1, 7),
            tilt_speed_range=(1, 7),
            
            # Zoom
            zoom=True,
            zoom_speed_range=(1, 7),
            
            # Focus - NOT supported
            focus=False,
            
            # Iris - NOT supported
            iris=False,
            
            # White Balance - NOT supported
            white_balance=False,
            
            # Exposure - NOT supported
            exposure=False,
            
            # Presets - 8 positions
            presets=8,
            
            # Advanced
            absolute_positioning=False,
            status_polling=False,
        ),
        "hid_report_id": 0x0B,
        "hid_report_size": 32,
        "motor_interval_ms": 70,
    },
    
    CameraModel.RALLY: {
        "name": "RALLY",
        "usb_ids": [(0x046D, 0x086A)],  # Example PID
        "protocols": [CameraProtocol.HID, CameraProtocol.WINDOWS_XU],
        "capabilities": CameraCapabilities(
            # Pan/Tilt
            pan_tilt=True,
            pan_speed_range=(1, 7),
            tilt_speed_range=(1, 7),
            
            # Zoom
            zoom=True,
            zoom_speed_range=(1, 7),
            
            # Focus - NOT supported
            focus=False,
            
            # Iris - NOT supported
            iris=False,
            
            # White Balance - NOT supported
            white_balance=False,
            
            # Exposure - NOT supported
            exposure=False,
            
            # Presets - 8 positions
            presets=8,
            
            # Advanced
            absolute_positioning=False,
            status_polling=False,
        ),
        "hid_report_id": 0x0B,
        "hid_report_size": 32,
        "motor_interval_ms": 70,
    },
    
    CameraModel.UNKNOWN: {
        "name": "Unknown Camera",
        "usb_ids": [],
        "protocols": [CameraProtocol.VISCA_SERIAL],
        "capabilities": CameraCapabilities(
            # Generic VISCA camera capabilities
            pan_tilt=True,
            pan_speed_range=(1, 24),
            tilt_speed_range=(1, 24),
            
            zoom=True,
            zoom_speed_range=(0, 7),
            
            focus=True,
            focus_speed_range=(1, 8),
            auto_focus=True,
            
            iris=True,
            iris_speed_range=(0, 3),
            auto_iris=True,
            
            white_balance=True,
            white_balance_modes=["auto", "indoor", "outdoor"],
            
            exposure=True,
            exposure_range=(-12, 12),
            
            presets=8,
            
            absolute_positioning=True,
            status_polling=True,
        ),
    },
}


def get_camera_model(model_enum: CameraModel) -> Optional[Dict]:
    """Get camera model definition."""
    return CAMERA_MODELS.get(model_enum)


def get_camera_capabilities(model_enum: CameraModel) -> Optional[CameraCapabilities]:
    """Get camera capabilities."""
    model_def = get_camera_model(model_enum)
    return model_def["capabilities"] if model_def else None


def find_model_by_usb_id(vendor_id: int, product_id: int) -> CameraModel:
    """Find camera model by USB vendor and product ID."""
    for model, definition in CAMERA_MODELS.items():
        if model == CameraModel.UNKNOWN:
            continue
        if (vendor_id, product_id) in definition.get("usb_ids", []):
            return model
    return CameraModel.UNKNOWN


def supports_protocol(model: CameraModel, protocol: CameraProtocol) -> bool:
    """Check if camera model supports a protocol."""
    model_def = get_camera_model(model)
    if not model_def:
        return False
    return protocol in model_def.get("protocols", [])
