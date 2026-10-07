"""Default configuration values for MerekaiPTZControl."""

DEFAULT_SETTINGS = {
    # Camera settings
    "camera_baudrate": 115200,
    "camera_timeout": 2.0,
    "camera_port": None,
    
    # Pan/Tilt settings
    "default_pan_speed": 15,
    "default_tilt_speed": 15,
    "pan_min": -2448,
    "pan_max": 2448,
    "tilt_min": -1296,
    "tilt_max": 1296,
    
    # Zoom settings
    "default_zoom_speed": 5,
    "zoom_min": 0x0000,
    "zoom_max": 0xFFFF,
    
    # Focus settings
    "default_focus_speed": 5,
    "focus_auto": True,
    
    # Iris settings
    "iris_auto": False,
    "iris_manual_level": 50,
    
    # White balance
    "white_balance_mode": "auto",  # auto, indoor, outdoor, manual
    
    # Exposure
    "exposure_compensation": 0.0,
    
    # UI settings
    "window_geometry": None,
    "window_state": None,
    "theme": "light",
    "language": "en",
    "camera_setting_matrix_names": {},
    "camera_setting_matrix_disabled": {},
    
    # Motor/Movement settings (from old C++ app)
    "motor_interval_timer": 70,  # ms between motor commands
    "use_extension_unit_motion_control": False,  # Use USB-specific controls
    "auto_repeat_delay": 35,  # ms for auto-repeat
    "auto_repeat_initial_delay": 150,  # ms before auto-repeat starts
    
    # Preset settings
    "max_presets": 8,  # 8 memory positions like original
    "preset_file": "dev/camera_presets.json",
    
    # Keyboard settings
    "enable_keyboard_shortcuts": True,
    "enable_global_hotkeys": False,  # System-wide hotkeys
    
    # Logging
    "log_level": "INFO",
    "log_file": "merekaiptzcontrol.log",
}

# Camera-specific profiles
CAMERA_PROFILES = {
    "ptz_pro": {
        "name": "PTZ PRO",
        "baudrate": 115200,
        "pan_range": (-2448, 2448),
        "tilt_range": (-1296, 1296),
        "zoom_range": (0x0000, 0xFFFF),
    },
    "ptz_pro2": {
        "name": "PTZ PRO 2",
        "baudrate": 115200,
        "pan_range": (-2448, 2448),
        "tilt_range": (-1296, 1296),
        "zoom_range": (0x0000, 0xFFFF),
    },
    "rally": {
        "name": "RALLY",
        "baudrate": 115200,
        "pan_range": (-2448, 2448),
        "tilt_range": (-1296, 1296),
        "zoom_range": (0x0000, 0xFFFF),
    },
}
