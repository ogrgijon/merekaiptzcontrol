"""
VISCA Protocol Implementation

Implements the VISCA (Video Index Switching Compression Architecture)
protocol for controlling PTZ cameras over USB/Serial connection.
"""

import struct
from enum import IntEnum
from typing import List, Tuple, Optional


class VISCACommand(IntEnum):
    """VISCA command codes."""
    
    # Pan-Tilt Commands
    PAN_TILT_HOME = 0x04
    PAN_TILT_ABSOLUTE = 0x02
    PAN_TILT_RELATIVE = 0x03
    PAN_TILT_STOP = 0x01
    
    # Zoom Commands
    ZOOM_TELE = 0x02  # Telephoto (zoom in)
    ZOOM_WIDE = 0x03  # Wide (zoom out)
    ZOOM_STOP = 0x00  # Stop zoom
    ZOOM_ABSOLUTE = 0x47
    
    # Focus Commands
    FOCUS_AUTO = 0x38  # Auto focus
    FOCUS_MANUAL = 0x39  # Manual focus
    FOCUS_ONE_PUSH = 0x18  # One-push autofocus
    FOCUS_FAR = 0x02  # Focus to infinity
    FOCUS_NEAR = 0x03  # Focus to near
    FOCUS_STOP = 0x01  # Stop focus
    
    # Exposure/Iris Commands
    EXPOSURE_AUTO = 0x39  # Auto exposure
    EXPOSURE_MANUAL = 0x0F  # Manual exposure
    IRIS_AUTO = 0x0F  # Auto iris
    IRIS_MANUAL = 0x0B  # Manual iris
    IRIS_OPEN = 0x02  # Iris open
    IRIS_CLOSE = 0x03  # Iris close
    
    # White Balance Commands
    WHITE_BALANCE_AUTO = 0x35  # Auto white balance
    WHITE_BALANCE_INDOOR = 0x01  # Indoor preset
    WHITE_BALANCE_OUTDOOR = 0x02  # Outdoor preset
    WHITE_BALANCE_MANUAL = 0x03  # Manual adjustment


class VISCAProtocol:
    """VISCA protocol handler for camera communication."""
    
    def __init__(self):
        """Initialize VISCA protocol handler."""
        self.camera_id = 1  # Default camera ID
        self.sequence_number = 0
    
    def create_command(self, command_bytes: bytes) -> bytes:
        """
        Create a complete VISCA command with header and checksum.
        
        VISCA command structure:
        [Header] [Camera_ID] [Message_Type] [Message_Body] [Terminator]
        
        Args:
            command_bytes: The command body bytes
            
        Returns:
            Complete VISCA command with header and checksum
        """
        header = 0x80  # VISCA header
        camera_id = 0x30 | (self.camera_id & 0x0F)  # Camera ID (1-7)
        message_type = 0x01  # Command type
        
        # Build command: header + camera_id + message_type + command + checksum
        payload = bytes([header, camera_id, message_type]) + command_bytes
        
        # Calculate checksum (XOR of all bytes)
        checksum = 0
        for byte in payload:
            checksum ^= byte
        
        # Add terminator
        terminator = 0xFF
        complete_command = payload + bytes([checksum, terminator])
        
        return complete_command
    
    def pan_tilt_absolute(self, pan_speed: int, tilt_speed: int, 
                          pan_position: int, tilt_position: int) -> bytes:
        """
        Send absolute pan/tilt command.
        
        Args:
            pan_speed: Pan speed (1-24, where 24 is fastest)
            tilt_speed: Tilt speed (1-24, where 24 is fastest)
            pan_position: Absolute pan position (-2448 to 2448)
            tilt_position: Absolute tilt position (-1296 to 1296)
            
        Returns:
            VISCA command bytes
        """
        # Clamp values
        pan_speed = max(1, min(24, pan_speed))
        tilt_speed = max(1, min(24, tilt_speed))
        
        # Convert positions to VISCA format (16-bit values)
        pan_val = self._encode_16bit(pan_position)
        tilt_val = self._encode_16bit(tilt_position)
        
        command = bytes([
            0x01,  # Command category
            0x06,  # Pan-tilt category
            0x02,  # Absolute position command
            pan_speed, tilt_speed
        ]) + pan_val + tilt_val
        
        return self.create_command(command)
    
    def pan_tilt_relative(self, pan_speed: int, tilt_speed: int,
                          pan_movement: int, tilt_movement: int) -> bytes:
        """
        Send relative pan/tilt command.
        
        Args:
            pan_speed: Pan speed (1-24)
            tilt_speed: Tilt speed (1-24)
            pan_movement: Relative pan movement (-2448 to 2448)
            tilt_movement: Relative tilt movement (-1296 to 1296)
            
        Returns:
            VISCA command bytes
        """
        pan_speed = max(1, min(24, pan_speed))
        tilt_speed = max(1, min(24, tilt_speed))
        
        pan_val = self._encode_16bit(pan_movement)
        tilt_val = self._encode_16bit(tilt_movement)
        
        command = bytes([
            0x01,  # Command category
            0x06,  # Pan-tilt category
            0x03,  # Relative position command
            pan_speed, tilt_speed
        ]) + pan_val + tilt_val
        
        return self.create_command(command)
    
    def pan_tilt_stop(self) -> bytes:
        """
        Stop pan/tilt movement.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x06,  # Pan-tilt category
            0x01   # Stop command
        ])
        return self.create_command(command)
    
    def zoom_absolute(self, zoom_position: int) -> bytes:
        """
        Set absolute zoom position.
        
        Args:
            zoom_position: Zoom position (0x0000 to 0xFFFF)
                          0x0000 = wide, 0xFFFF = telephoto
                          
        Returns:
            VISCA command bytes
        """
        zoom_position = max(0x0000, min(0xFFFF, zoom_position))
        zoom_val = self._encode_16bit(zoom_position)
        
        command = bytes([
            0x01,  # Command category
            0x04,  # Zoom category
            0x47   # Absolute zoom command
        ]) + zoom_val
        
        return self.create_command(command)
    
    def zoom_tele(self, speed: int) -> bytes:
        """
        Start zoom telephoto (zoom in).
        
        Args:
            speed: Zoom speed (0-7, where 7 is fastest)
            
        Returns:
            VISCA command bytes
        """
        speed = max(0, min(7, speed))
        
        command = bytes([
            0x01,  # Command category
            0x04,  # Zoom category
            0x02,  # Tele zoom command
            0x20 | speed  # Speed
        ])
        
        return self.create_command(command)
    
    def zoom_wide(self, speed: int) -> bytes:
        """
        Start zoom wide (zoom out).
        
        Args:
            speed: Zoom speed (0-7, where 7 is fastest)
            
        Returns:
            VISCA command bytes
        """
        speed = max(0, min(7, speed))
        
        command = bytes([
            0x01,  # Command category
            0x04,  # Zoom category
            0x03,  # Wide zoom command
            0x30 | speed  # Speed
        ])
        
        return self.create_command(command)
    
    def zoom_stop(self) -> bytes:
        """
        Stop zoom movement.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x04,  # Zoom category
            0x00   # Stop zoom command
        ])
        
        return self.create_command(command)
    
    def focus_auto(self) -> bytes:
        """
        Enable autofocus.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x04,  # Focus category
            0x38,  # Auto focus command
            0x02   # On
        ])
        
        return self.create_command(command)
    
    def focus_manual(self) -> bytes:
        """
        Enable manual focus.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x04,  # Focus category
            0x38,  # Manual focus command
            0x03   # Off (manual mode)
        ])
        
        return self.create_command(command)
    
    def focus_far(self, speed: int) -> bytes:
        """
        Focus to far (infinity).
        
        Args:
            speed: Focus speed (0-7)
            
        Returns:
            VISCA command bytes
        """
        speed = max(0, min(7, speed))
        
        command = bytes([
            0x01,  # Command category
            0x04,  # Focus category
            0x08,  # Focus drive command
            0x20 | speed  # Far + speed
        ])
        
        return self.create_command(command)
    
    def focus_near(self, speed: int) -> bytes:
        """
        Focus to near.
        
        Args:
            speed: Focus speed (0-7)
            
        Returns:
            VISCA command bytes
        """
        speed = max(0, min(7, speed))
        
        command = bytes([
            0x01,  # Command category
            0x04,  # Focus category
            0x08,  # Focus drive command
            0x30 | speed  # Near + speed
        ])
        
        return self.create_command(command)
    
    def focus_stop(self) -> bytes:
        """
        Stop focus movement.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x04,  # Focus category
            0x08,  # Focus drive command
            0x00   # Stop
        ])
        
        return self.create_command(command)
    
    def iris_open(self, speed: int) -> bytes:
        """
        Open iris (increase brightness).
        
        Args:
            speed: Iris speed (0-7)
            
        Returns:
            VISCA command bytes
        """
        speed = max(0, min(7, speed))
        
        command = bytes([
            0x01,  # Command category
            0x04,  # Iris category
            0x0B,  # Iris drive command
            0x20 | speed  # Open + speed
        ])
        
        return self.create_command(command)
    
    def iris_close(self, speed: int) -> bytes:
        """
        Close iris (decrease brightness).
        
        Args:
            speed: Iris speed (0-7)
            
        Returns:
            VISCA command bytes
        """
        speed = max(0, min(7, speed))
        
        command = bytes([
            0x01,  # Command category
            0x04,  # Iris category
            0x0B,  # Iris drive command
            0x30 | speed  # Close + speed
        ])
        
        return self.create_command(command)
    
    def iris_stop(self) -> bytes:
        """
        Stop iris adjustment.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x04,  # Iris category
            0x0B,  # Iris drive command
            0x00   # Stop
        ])
        
        return self.create_command(command)
    
    def white_balance_auto(self) -> bytes:
        """
        Enable auto white balance.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x04,  # White balance category
            0x35,  # White balance mode
            0x00   # Auto
        ])
        
        return self.create_command(command)
    
    def white_balance_indoor(self) -> bytes:
        """
        Set white balance to indoor preset.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x04,  # White balance category
            0x35,  # White balance mode
            0x01   # Indoor
        ])
        
        return self.create_command(command)
    
    def white_balance_outdoor(self) -> bytes:
        """
        Set white balance to outdoor preset.
        
        Returns:
            VISCA command bytes
        """
        command = bytes([
            0x01,  # Command category
            0x04,  # White balance category
            0x35,  # White balance mode
            0x02   # Outdoor
        ])
        
        return self.create_command(command)
    
    @staticmethod
    def _encode_16bit(value: int) -> bytes:
        """
        Encode a 16-bit signed value to VISCA 4-byte format.
        
        VISCA uses a special 4-byte encoding where each nibble is
        encoded as a separate byte.
        
        Args:
            value: 16-bit signed integer
            
        Returns:
            4 bytes in VISCA format
        """
        # Convert to unsigned 16-bit
        if value < 0:
            unsigned_val = 0x10000 + value
        else:
            unsigned_val = value
        
        # Split into nibbles
        byte0 = (unsigned_val >> 12) & 0x0F
        byte1 = (unsigned_val >> 8) & 0x0F
        byte2 = (unsigned_val >> 4) & 0x0F
        byte3 = unsigned_val & 0x0F
        
        return bytes([byte0, byte1, byte2, byte3])
    
    @staticmethod
    def _decode_16bit(data: bytes) -> int:
        """
        Decode VISCA 4-byte format to 16-bit signed value.
        
        Args:
            data: 4 bytes in VISCA format
            
        Returns:
            16-bit signed integer
        """
        if len(data) < 4:
            return 0
        
        # Combine nibbles
        unsigned_val = (
            (data[0] << 12) |
            (data[1] << 8) |
            (data[2] << 4) |
            data[3]
        )
        
        # Convert to signed
        if unsigned_val & 0x8000:
            return unsigned_val - 0x10000
        return unsigned_val
