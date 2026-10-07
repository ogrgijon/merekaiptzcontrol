"""
Settings Manager

Manages application configuration and user preferences.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.app_paths import app_data_dir
from .defaults import DEFAULT_SETTINGS


logger = logging.getLogger(__name__)


class Settings:
    """Application settings manager."""
    
    SETTINGS_FILE = app_data_dir() / "settings.json"
    
    def __init__(self):
        """Initialize settings manager."""
        self.settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()
        self._load_settings()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value.
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value.
        
        Args:
            key: Setting key
            value: New value
        """
        self.settings[key] = value
        logger.debug(f"Setting '{key}' = {value}")
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings.
        
        Returns:
            Dictionary of all settings
        """
        return self.settings.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        self.settings = DEFAULT_SETTINGS.copy()
        logger.info("Settings reset to defaults")
    
    def _load_settings(self) -> None:
        """Load settings from file."""
        settings_path = Path(self.SETTINGS_FILE)
        
        try:
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    self.settings.update(loaded)
                logger.info(f"Loaded settings from {self.SETTINGS_FILE}")
            else:
                logger.debug("Settings file not found, using defaults")
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
    
    def save(self) -> None:
        """Save settings to file."""
        settings_path = Path(self.SETTINGS_FILE)
        
        try:
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2, default=str)
            
            logger.info(f"Saved settings to {self.SETTINGS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
