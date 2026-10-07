"""
Unified Camera Wrapper

Bridges between the abstract transport layer and the UI layer.
Provides a consistent interface for all camera types.
"""

import logging
from typing import Optional

from .camera_device import CameraStatus
from .hid_transport import HidTransport
from .models import CameraModel
from .transport import CameraTransport, CommandResult

logger = logging.getLogger(__name__)


class CameraWrapper:
    """
    Wraps a CameraTransport and provides high-level control methods.
    
    This class bridges between the abstract transport layer and the UI layer,
    providing a consistent interface regardless of the underlying protocol.
    """

    def __init__(self, transport: CameraTransport):
        """
        Initialize camera wrapper.

        Args:
            transport: CameraTransport instance to wrap
        """
        self.transport = transport

    @property
    def display_name(self) -> str:
        """Get display name for this camera."""
        return self.transport.display_name

    @property
    def status(self) -> CameraStatus:
        """Get camera connection status."""
        if self.transport.is_connected():
            return CameraStatus.CONNECTED
        else:
            return CameraStatus.DISCONNECTED

    @property
    def capabilities(self) -> dict:
        """Get camera capabilities dictionary."""
        if self.transport.capabilities:
            return {
                "pan_tilt": True,
                "zoom": True,
                "focus": bool(self.transport.capabilities.focus),
                "iris": bool(self.transport.capabilities.iris),
                "white_balance": bool(self.transport.capabilities.white_balance),
                "exposure": bool(self.transport.capabilities.exposure),
                "presets": bool(self.transport.capabilities.presets),
            }
        return {
            "pan_tilt": True,
            "zoom": True,
            "focus": False,
            "iris": False,
            "white_balance": False,
            "exposure": False,
            "presets": False,
        }

    def connect(self) -> bool:
        """Connect to camera."""
        return self.transport.connect()

    def disconnect(self) -> None:
        """Disconnect from camera."""
        self.transport.disconnect()

    def is_connected(self) -> bool:
        """Check if connected."""
        return self.transport.is_connected()

    # =========================================================================
    # Pan/Tilt Control - Wrapper methods that call transport
    # =========================================================================

    def pan_tilt_relative(
        self,
        pan_speed: int,
        tilt_speed: int,
        pan_move: int,
        tilt_move: int,
    ) -> bool:
        """
        Send relative pan/tilt command.

        Args:
            pan_speed: Pan speed (1-7 or 1-24)
            tilt_speed: Tilt speed (1-7 or 1-24)
            pan_move: Pan direction (-100=left, 0=stop, 100=right)
            tilt_move: Tilt direction (-100=down, 0=stop, 100=up)

        Returns:
            True if successful
        """
        result = self.transport.pan_tilt_relative(
            pan_speed, tilt_speed, pan_move, tilt_move
        )
        return result.success

    def pan_tilt_absolute(
        self,
        pan_speed: int,
        tilt_speed: int,
        pan_pos: int,
        tilt_pos: int,
    ) -> bool:
        """Send absolute pan/tilt command."""
        result = self.transport.pan_tilt_absolute(
            pan_speed, tilt_speed, pan_pos, tilt_pos
        )
        return result.success

    def pan_tilt_stop(self) -> bool:
        """Stop pan/tilt movement."""
        result = self.transport.pan_tilt_stop()
        return result.success

    # =========================================================================
    # Zoom Control
    # =========================================================================

    def zoom_relative(self, speed: int, direction: int) -> bool:
        """Send relative zoom command."""
        result = self.transport.zoom_relative(speed, direction)
        return result.success

    def zoom_absolute(self, position: int) -> bool:
        """Send absolute zoom command."""
        result = self.transport.zoom_absolute(position)
        return result.success

    def zoom_stop(self) -> bool:
        """Stop zoom movement."""
        result = self.transport.zoom_stop()
        return result.success

    def zoom_tele(self, speed: int) -> bool:
        """Send zoom telephoto (in) command."""
        return self.zoom_relative(speed, 1)

    def zoom_wide(self, speed: int) -> bool:
        """Send zoom wide (out) command."""
        return self.zoom_relative(speed, -1)

    # =========================================================================
    # Focus Control
    # =========================================================================

    def focus_auto(self) -> bool:
        """Enable autofocus."""
        result = self.transport.focus_auto()
        return result.success

    def focus_manual(self) -> bool:
        """Disable autofocus (manual mode)."""
        result = self.transport.focus_manual()
        return result.success

    def focus_relative(self, speed: int, direction: int) -> bool:
        """Send relative focus command."""
        result = self.transport.focus_relative(speed, direction)
        return result.success

    def focus_absolute(self, position: int) -> bool:
        """Send absolute focus command."""
        result = self.transport.focus_absolute(position)
        return result.success

    def focus_far(self, speed: int) -> bool:
        """Move focus far."""
        return self.focus_relative(speed, 1)

    def focus_near(self, speed: int) -> bool:
        """Move focus near."""
        return self.focus_relative(speed, -1)

    def focus_stop(self) -> bool:
        """Stop focus movement."""
        result = self.transport.focus_stop()
        return result.success

    # =========================================================================
    # Iris Control
    # =========================================================================

    def iris_auto(self) -> bool:
        """Enable auto iris."""
        result = self.transport.iris_auto()
        return result.success

    def iris_manual(self) -> bool:
        """Enable manual iris control."""
        result = self.transport.iris_manual()
        return result.success

    def iris_relative(self, speed: int, direction: int) -> bool:
        """Send relative iris command."""
        result = self.transport.iris_relative(speed, direction)
        return result.success

    def iris_open(self, speed: int) -> bool:
        """Open iris (brighten)."""
        return self.iris_relative(speed, 1)

    def iris_close(self, speed: int) -> bool:
        """Close iris (darken)."""
        return self.iris_relative(speed, -1)

    def iris_stop(self) -> bool:
        """Stop iris movement."""
        result = self.transport.iris_stop()
        return result.success

    # =========================================================================
    # White Balance Control
    # =========================================================================

    def white_balance_auto(self) -> bool:
        """Enable auto white balance."""
        result = self.transport.white_balance_auto()
        return result.success

    def white_balance_preset(self, preset: str) -> bool:
        """Set white balance preset."""
        result = self.transport.white_balance_preset(preset)
        return result.success

    def white_balance_manual(self, blue: int, red: int) -> bool:
        """Set manual white balance."""
        result = self.transport.white_balance_manual(blue, red)
        return result.success

    def white_balance_indoor(self) -> bool:
        """Set white balance to indoor preset."""
        return self.white_balance_preset("indoor")

    def white_balance_outdoor(self) -> bool:
        """Set white balance to outdoor preset."""
        return self.white_balance_preset("outdoor")

    # =========================================================================
    # Exposure Control
    # =========================================================================

    def exposure_auto(self) -> bool:
        """Enable auto exposure."""
        result = self.transport.exposure_auto()
        return result.success

    def exposure_manual(self) -> bool:
        """Enable manual exposure control."""
        result = self.transport.exposure_manual()
        return result.success

    def exposure_compensation(self, compensation: int) -> bool:
        """Set exposure compensation."""
        result = self.transport.exposure_compensation(compensation)
        return result.success

    # =========================================================================
    # Preset Control
    # =========================================================================

    def save_preset(self, preset_id: int) -> bool:
        """Save current position to preset."""
        result = self.transport.save_preset(preset_id)
        return result.success

    def recall_preset(self, preset_id: int) -> bool:
        """Recall saved preset position."""
        result = self.transport.recall_preset(preset_id)
        return result.success

    def home(self) -> bool:
        """Move to home position."""
        result = self.transport.home()
        return result.success

    def get_ptz_position(self) -> dict[str, Optional[int]]:
        """Read the current PTZ position when the transport supports it."""
        getter = getattr(self.transport, "get_ptz_position", None)
        if not callable(getter):
            return {"pan": None, "tilt": None, "zoom": None}
        return getter()

    # =========================================================================
    # Status Query
    # =========================================================================

    def get_status(self) -> Optional[dict]:
        """Get camera status information."""
        result = self.transport.get_status()
        if result.success and result.data:
            return result.data
        return None
