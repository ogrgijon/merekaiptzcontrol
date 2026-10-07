"""
Auto-repeat Button Control

Implements button behavior with auto-repeat (like the old C++ CPTZButton).
When a button is pressed and held, it automatically repeats the command.
"""

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import QTimer, pyqtSignal


class AutoRepeatButton(QPushButton):
    """
    Push button with auto-repeat functionality.
    
    When held down, the button emits its clicked signal repeatedly
    after an initial delay, useful for continuous camera movements.
    """
    
    # Signals
    repeating = pyqtSignal()  # Emitted when auto-repeat triggers
    
    def __init__(self, text: str = "", parent=None):
        """
        Initialize auto-repeat button.
        
        Args:
            text: Button text
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        self.auto_repeat_enabled = False
        self.initial_delay = 500  # ms before auto-repeat starts
        self.repeat_interval = 50  # ms between repeats
        
        # Timers for auto-repeat
        self._initial_timer = QTimer()
        self._initial_timer.setSingleShot(True)
        self._initial_timer.timeout.connect(self._start_repeat)
        
        self._repeat_timer = QTimer()
        self._repeat_timer.timeout.connect(self._on_repeat)
        
        # Track pressed state
        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)
    
    def set_auto_repeat(self, enabled: bool) -> None:
        """
        Enable/disable auto-repeat functionality.
        
        Args:
            enabled: True to enable, False to disable
        """
        self.auto_repeat_enabled = enabled
        if not enabled:
            self._stop_repeat()
    
    def set_repeat_delays(self, initial_delay: int, repeat_interval: int) -> None:
        """
        Set auto-repeat timing.
        
        Args:
            initial_delay: Milliseconds before auto-repeat starts (default 500ms)
            repeat_interval: Milliseconds between repeats (default 50ms)
        """
        self.initial_delay = initial_delay
        self.repeat_interval = repeat_interval
        self._initial_timer.setInterval(initial_delay)
        self._repeat_timer.setInterval(repeat_interval)
    
    def _on_pressed(self) -> None:
        """Handle button press."""
        if self.auto_repeat_enabled:
            self._initial_timer.start(self.initial_delay)
    
    def _on_released(self) -> None:
        """Handle button release."""
        self._stop_repeat()
    
    def _start_repeat(self) -> None:
        """Start the auto-repeat timer."""
        if self.auto_repeat_enabled and self.isDown():
            self._repeat_timer.start(self.repeat_interval)
    
    def _stop_repeat(self) -> None:
        """Stop auto-repeat."""
        self._initial_timer.stop()
        self._repeat_timer.stop()
    
    def _on_repeat(self) -> None:
        """Emit repeat signal."""
        if self.auto_repeat_enabled and self.isDown():
            self.repeating.emit()
        else:
            self._stop_repeat()
