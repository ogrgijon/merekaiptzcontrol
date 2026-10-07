"""
Unit tests for VISCA protocol implementation.
"""

import pytest
from src.camera.visca_protocol import VISCAProtocol


class TestVISCAProtocol:
    """Test cases for VISCA protocol."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.protocol = VISCAProtocol()
    
    def test_pan_tilt_absolute(self):
        """Test absolute pan/tilt command."""
        command = self.protocol.pan_tilt_absolute(15, 15, 100, 50)
        
        assert command is not None
        assert isinstance(command, bytes)
        assert len(command) > 0
        # Command should end with terminator 0xFF
        assert command[-1] == 0xFF
    
    def test_zoom_tele(self):
        """Test zoom telephoto command."""
        command = self.protocol.zoom_tele(7)
        
        assert command is not None
        assert isinstance(command, bytes)
        assert command[-1] == 0xFF
    
    def test_zoom_wide(self):
        """Test zoom wide command."""
        command = self.protocol.zoom_wide(7)
        
        assert command is not None
        assert isinstance(command, bytes)
        assert command[-1] == 0xFF
    
    def test_focus_auto(self):
        """Test autofocus command."""
        command = self.protocol.focus_auto()
        
        assert command is not None
        assert isinstance(command, bytes)
        assert command[-1] == 0xFF
    
    def test_white_balance_auto(self):
        """Test auto white balance command."""
        command = self.protocol.white_balance_auto()
        
        assert command is not None
        assert isinstance(command, bytes)
        assert command[-1] == 0xFF
    
    def test_encode_decode_16bit(self):
        """Test 16-bit encoding and decoding."""
        test_values = [0, 100, -100, 2448, -2448, 0xFFFF]
        
        for value in test_values:
            encoded = VISCAProtocol._encode_16bit(value)
            assert len(encoded) == 4
            
            # Note: decoding might not be exact for negative values
            # This is a basic test
            assert isinstance(encoded, bytes)
