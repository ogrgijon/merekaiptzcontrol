"""
Camera Transport Base Class

Defines the abstract interface for all camera communication transports.
Each protocol (HID, VISCA, Windows XU) implements this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .models import CameraCapabilities, CameraModel


@dataclass
class CommandResult:
    """Result of a camera command execution."""
    
    success: bool
    """Whether the command succeeded."""
    
    error: Optional[str] = None
    """Error message if command failed."""
    
    status: Optional[Dict[str, Any]] = field(default_factory=dict)
    """Status data returned by camera (if applicable)."""
    
    def __bool__(self) -> bool:
        """Allow using CommandResult in boolean context."""
        return self.success


class CameraTransport(ABC):
    """
    Abstract base class for all camera communication transports.
    
    Subclasses implement specific protocols (HID, VISCA, Windows XU).
    This provides a unified interface regardless of underlying protocol.
    """
    
    def __init__(self):
        """Initialize transport."""
        self.model: CameraModel = CameraModel.UNKNOWN
        self.capabilities: Optional[CameraCapabilities] = None
        self.connected: bool = False
        self.display_name: str = "Unknown Camera"
    
    # =========================================================================
    # Connection Management
    # =========================================================================
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to camera.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Terminate connection to camera."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if currently connected to camera.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    # =========================================================================
    # Pan/Tilt Control
    # =========================================================================
    
    @abstractmethod
    def pan_tilt_relative(
        self,
        pan_speed: int,
        tilt_speed: int,
        pan_move: int,
        tilt_move: int
    ) -> CommandResult:
        """
        Send relative pan/tilt command.
        
        Movement is specified as direction and duration, not absolute position.
        Camera moves in the specified direction at the specified speed.
        
        Args:
            pan_speed: Pan speed (1-7 for HID, 1-24 for VISCA)
            tilt_speed: Tilt speed (1-7 for HID, 1-24 for VISCA)
            pan_move: Pan movement direction:
                    negative = left, positive = right, 0 = no movement
            tilt_move: Tilt movement direction:
                     negative = down, positive = up, 0 = no movement
        
        Returns:
            CommandResult with success status
        """
        pass
    
    @abstractmethod
    def pan_tilt_absolute(
        self,
        pan_speed: int,
        tilt_speed: int,
        pan_pos: int,
        tilt_pos: int
    ) -> CommandResult:
        """
        Send absolute pan/tilt command.
        
        Move camera to specific absolute position.
        Note: Not all protocols/cameras support this.
        
        Args:
            pan_speed: Pan speed (1-24 for VISCA)
            tilt_speed: Tilt speed (1-24 for VISCA)
            pan_pos: Absolute pan position
            tilt_pos: Absolute tilt position
        
        Returns:
            CommandResult with success status
        """
        pass
    
    def pan_tilt_stop(self) -> CommandResult:
        """
        Stop all pan/tilt movement.
        
        Default implementation returns success. Subclasses override if needed.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(success=True)
    
    # =========================================================================
    # Zoom Control
    # =========================================================================
    
    @abstractmethod
    def zoom_relative(
        self,
        speed: int,
        direction: int
    ) -> CommandResult:
        """
        Send relative zoom command.
        
        Zoom in or out at specified speed.
        
        Args:
            speed: Zoom speed (1-7 for HID, 0-7 for VISCA)
            direction: Zoom direction:
                     positive = zoom in (telephoto)
                     negative = zoom out (wide)
                     0 = stop zoom
        
        Returns:
            CommandResult with success status
        """
        pass
    
    @abstractmethod
    def zoom_absolute(self, position: int) -> CommandResult:
        """
        Send absolute zoom command.
        
        Set zoom to specific position (0-100%).
        Note: Not all protocols/cameras support this.
        
        Args:
            position: Absolute zoom position (0-100)
        
        Returns:
            CommandResult with success status
        """
        pass
    
    def zoom_stop(self) -> CommandResult:
        """
        Stop zoom movement.
        
        Default implementation returns success. Subclasses override if needed.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(success=True)
    
    # =========================================================================
    # Focus Control
    # =========================================================================
    
    def focus_auto(self) -> CommandResult:
        """
        Enable auto focus mode.
        
        Default implementation returns not supported. Override in subclasses.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Focus control not supported by this camera"
        )
    
    def focus_manual(self) -> CommandResult:
        """
        Switch to manual focus mode.
        
        Default implementation returns not supported. Override in subclasses.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Focus control not supported by this camera"
        )
    
    def focus_relative(self, speed: int, direction: int) -> CommandResult:
        """
        Send relative focus command.
        
        Args:
            speed: Focus speed (1-8)
            direction: Focus direction:
                     positive = focus far (infinity)
                     negative = focus near
                     0 = stop focus
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Focus control not supported by this camera"
        )
    
    def focus_absolute(self, position: int) -> CommandResult:
        """
        Send absolute focus command.
        
        Args:
            position: Absolute focus position (0-100)
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Focus control not supported by this camera"
        )
    
    # =========================================================================
    # Iris Control
    # =========================================================================
    
    def iris_auto(self) -> CommandResult:
        """
        Enable auto iris mode.
        
        Default implementation returns not supported. Override in subclasses.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Iris control not supported by this camera"
        )
    
    def iris_manual(self) -> CommandResult:
        """
        Switch to manual iris mode.
        
        Default implementation returns not supported. Override in subclasses.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Iris control not supported by this camera"
        )
    
    def iris_relative(self, speed: int, direction: int) -> CommandResult:
        """
        Send relative iris command.
        
        Args:
            speed: Iris speed (0-3)
            direction: Iris direction:
                     positive = open iris (increase brightness)
                     negative = close iris (decrease brightness)
                     0 = stop
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Iris control not supported by this camera"
        )
    
    # =========================================================================
    # White Balance Control
    # =========================================================================
    
    def white_balance_auto(self) -> CommandResult:
        """
        Enable auto white balance mode.
        
        Default implementation returns not supported. Override in subclasses.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="White balance control not supported by this camera"
        )
    
    def white_balance_preset(self, preset: str) -> CommandResult:
        """
        Set white balance to preset mode.
        
        Args:
            preset: Preset name (e.g., "indoor", "outdoor")
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="White balance control not supported by this camera"
        )
    
    def white_balance_manual(self, rg_gain: int, bg_gain: int) -> CommandResult:
        """
        Set white balance to manual mode.
        
        Args:
            rg_gain: Red/Green gain (0-255)
            bg_gain: Blue/Green gain (0-255)
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="White balance control not supported by this camera"
        )
    
    # =========================================================================
    # Exposure Control
    # =========================================================================
    
    def exposure_auto(self) -> CommandResult:
        """
        Enable auto exposure mode.
        
        Default implementation returns not supported. Override in subclasses.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Exposure control not supported by this camera"
        )
    
    def exposure_manual(self) -> CommandResult:
        """
        Switch to manual exposure mode.
        
        Default implementation returns not supported. Override in subclasses.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Exposure control not supported by this camera"
        )
    
    def exposure_compensation(self, value: int) -> CommandResult:
        """
        Set exposure compensation.
        
        Args:
            value: Compensation value (-12 to +12 EV)
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Exposure control not supported by this camera"
        )
    
    # =========================================================================
    # Preset Management
    # =========================================================================
    
    def save_preset(self, position: int) -> CommandResult:
        """
        Save current camera position to preset.
        
        Default implementation returns not supported. Override in subclasses.
        
        Args:
            position: Preset position (0-7 or higher depending on camera)
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Preset management not supported by this camera"
        )
    
    def recall_preset(self, position: int) -> CommandResult:
        """
        Recall camera position from preset.
        
        Default implementation returns not supported. Override in subclasses.
        
        Args:
            position: Preset position (0-7 or higher depending on camera)
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Preset management not supported by this camera"
        )
    
    def home(self) -> CommandResult:
        """
        Move camera to home position.
        
        Default implementation returns not supported. Override in subclasses.
        
        Returns:
            CommandResult with success status
        """
        return CommandResult(
            success=False,
            error="Home position not supported by this camera"
        )
    
    # =========================================================================
    # Status and Feedback
    # =========================================================================
    
    @abstractmethod
    def get_status(self) -> Optional[Dict[str, Any]]:
        """
        Poll camera for status information.
        
        Returns current camera position, zoom level, etc.
        
        Returns:
            Dictionary with status data, or None if not supported
            
        Example:
            {
                "pan_position": 100,
                "tilt_position": 50,
                "zoom_position": 30,
                "focus_position": 128,
                "iris_position": 64,
                "connected": True,
            }
        """
        pass
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def validate_pan_speed(self, speed: int) -> int:
        """Validate and clamp pan speed to valid range."""
        if not self.capabilities or not self.capabilities.pan_tilt:
            return speed
        min_speed, max_speed = self.capabilities.pan_speed_range
        return max(min_speed, min(max_speed, speed))
    
    def validate_tilt_speed(self, speed: int) -> int:
        """Validate and clamp tilt speed to valid range."""
        if not self.capabilities or not self.capabilities.pan_tilt:
            return speed
        min_speed, max_speed = self.capabilities.tilt_speed_range
        return max(min_speed, min(max_speed, speed))
    
    def validate_zoom_speed(self, speed: int) -> int:
        """Validate and clamp zoom speed to valid range."""
        if not self.capabilities or not self.capabilities.zoom:
            return speed
        min_speed, max_speed = self.capabilities.zoom_speed_range
        return max(min_speed, min(max_speed, speed))
    
    def supports_feature(self, feature: str) -> bool:
        """Check if camera supports a specific feature."""
        if not self.capabilities:
            return False
        
        feature_map = {
            "pan_tilt": self.capabilities.pan_tilt,
            "zoom": self.capabilities.zoom,
            "focus": self.capabilities.focus,
            "iris": self.capabilities.iris,
            "white_balance": self.capabilities.white_balance,
            "exposure": self.capabilities.exposure,
            "presets": self.capabilities.presets > 0,
            "absolute_positioning": self.capabilities.absolute_positioning,
            "status_polling": self.capabilities.status_polling,
        }
        
        return feature_map.get(feature, False)
