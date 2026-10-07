"""
Command-Line Interface

Allows controlling cameras via command-line parameters,
inspired by the original PTZControl.cpp command-line handling.

Usage:
    python main.py --device COM3 --pan 1 --tilt -1 --zoom 0
    python main.py --device COM3 --preset 1 --action restore
    python main.py --device COM3 --preset 2 --action store
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from src.camera.camera_manager import CameraManager
from src.config.settings import Settings


logger = logging.getLogger(__name__)


class CommandLineInterface:
    """Command-line interface for camera control."""
    
    def __init__(self):
        """Initialize CLI."""
        self.settings = Settings()
        self.camera_manager = CameraManager()
    
    def parse_args(self) -> argparse.Namespace:
        """Parse command-line arguments."""
        parser = argparse.ArgumentParser(
            description="MerekaiPTZControl - PTZ Camera Control",
            epilog="""
Examples:
  python main.py --device COM3 --pan 1 --tilt 0 --zoom 5
  python main.py --device COM3 --preset 1 --action restore
  python main.py --device COM3 --focus auto
  python main.py --device COM3 --iris open --speed 5
            """,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Device selection
        parser.add_argument(
            "--device",
            help="Serial port device (e.g., COM3, /dev/ttyUSB0)"
        )
        
        # Pan/Tilt commands
        parser.add_argument(
            "--pan",
            type=int,
            help="Pan direction/steps: 1=right, -1=left, 0=stop"
        )
        
        parser.add_argument(
            "--tilt",
            type=int,
            help="Tilt direction/steps: 1=up, -1=down, 0=stop"
        )
        
        parser.add_argument(
            "--pan-speed",
            type=int,
            default=15,
            help="Pan speed (1-24, default 15)"
        )
        
        parser.add_argument(
            "--tilt-speed",
            type=int,
            default=15,
            help="Tilt speed (1-24, default 15)"
        )
        
        # Zoom commands
        parser.add_argument(
            "--zoom",
            choices=["in", "out", "stop"],
            help="Zoom: in (tele), out (wide), stop"
        )
        
        parser.add_argument(
            "--zoom-speed",
            type=int,
            default=5,
            help="Zoom speed (0-7, default 5)"
        )
        
        parser.add_argument(
            "--zoom-position",
            type=int,
            help="Absolute zoom position (0x0000-0xFFFF)"
        )
        
        # Focus commands
        parser.add_argument(
            "--focus",
            choices=["auto", "manual", "near", "far", "stop"],
            help="Focus mode or direction"
        )
        
        parser.add_argument(
            "--focus-speed",
            type=int,
            default=5,
            help="Focus speed (0-7, default 5)"
        )
        
        # Iris/Brightness commands
        parser.add_argument(
            "--iris",
            choices=["open", "close", "stop"],
            help="Iris: open (brighter), close (darker), stop"
        )
        
        parser.add_argument(
            "--iris-speed",
            type=int,
            default=5,
            help="Iris speed (0-7, default 5)"
        )
        
        # White balance commands
        parser.add_argument(
            "--white-balance",
            choices=["auto", "indoor", "outdoor"],
            help="White balance mode"
        )
        
        # Preset commands
        parser.add_argument(
            "--preset",
            type=int,
            help="Preset position (1-8)"
        )
        
        parser.add_argument(
            "--action",
            choices=["store", "restore"],
            help="Preset action: store (save) or restore (load)"
        )
        
        # Home command
        parser.add_argument(
            "--home",
            action="store_true",
            help="Move to home position"
        )
        
        # List devices
        parser.add_argument(
            "--list-devices",
            action="store_true",
            help="List available serial ports and exit"
        )
        
        # Settings
        parser.add_argument(
            "--timeout",
            type=float,
            default=2.0,
            help="Command timeout in seconds"
        )
        
        # Logging
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Logging level"
        )
        
        return parser.parse_args()
    
    def run(self) -> int:
        """Execute CLI commands."""
        args = self.parse_args()
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, args.log_level),
            format="%(levelname)s: %(message)s"
        )
        
        # List devices and exit
        if args.list_devices:
            self._list_devices()
            return 0
        
        # Require device for commands
        if not args.device:
            if not (args.list_devices):
                print("Error: --device is required (use --list-devices to see available ports)")
                return 1
        
        # Connect to device
        camera_name = f"CLI_Camera_{args.device.replace('/', '_').replace(':', '_')}"
        
        if not self.camera_manager.add_camera(
            camera_name,
            args.device,
            self.settings.get("camera_baudrate", 115200)
        ):
            logger.error(f"Failed to add camera on {args.device}")
            return 1
        
        if not self.camera_manager.connect_camera(camera_name):
            logger.error(f"Failed to connect to {args.device}")
            return 1
        
        logger.info(f"Connected to camera on {args.device}")
        
        # Execute commands
        camera = self.camera_manager.get_active_camera()
        if not camera:
            logger.error("No active camera")
            return 1
        
        try:
            if args.home:
                logger.info("Moving to home position")
                camera.pan_tilt_absolute(1, 1, 0, 0)
            
            if args.pan is not None or args.tilt is not None:
                pan_move = args.pan * 100 if args.pan else 0
                tilt_move = args.tilt * 100 if args.tilt else 0
                logger.info(f"Pan/Tilt: pan={pan_move}, tilt={tilt_move}, speed={args.pan_speed}/{args.tilt_speed}")
                camera.pan_tilt_relative(args.pan_speed, args.tilt_speed, pan_move, tilt_move)
            
            if args.zoom:
                if args.zoom == "in":
                    logger.info(f"Zoom in (speed {args.zoom_speed})")
                    camera.zoom_tele(args.zoom_speed)
                elif args.zoom == "out":
                    logger.info(f"Zoom out (speed {args.zoom_speed})")
                    camera.zoom_wide(args.zoom_speed)
                elif args.zoom == "stop":
                    logger.info("Zoom stop")
                    camera.zoom_stop()
            
            if args.zoom_position is not None:
                logger.info(f"Zoom to position {args.zoom_position:04X}")
                camera.zoom_absolute(args.zoom_position)
            
            if args.focus:
                if args.focus == "auto":
                    logger.info("Focus: auto")
                    camera.focus_auto()
                elif args.focus == "manual":
                    logger.info("Focus: manual")
                    camera.focus_manual()
                elif args.focus == "near":
                    logger.info(f"Focus near (speed {args.focus_speed})")
                    camera.focus_near(args.focus_speed)
                elif args.focus == "far":
                    logger.info(f"Focus far (speed {args.focus_speed})")
                    camera.focus_far(args.focus_speed)
                elif args.focus == "stop":
                    logger.info("Focus stop")
                    camera.focus_stop()
            
            if args.iris:
                if args.iris == "open":
                    logger.info(f"Iris open (speed {args.iris_speed})")
                    camera.iris_open(args.iris_speed)
                elif args.iris == "close":
                    logger.info(f"Iris close (speed {args.iris_speed})")
                    camera.iris_close(args.iris_speed)
                elif args.iris == "stop":
                    logger.info("Iris stop")
                    camera.iris_stop()
            
            if args.white_balance:
                if args.white_balance == "auto":
                    logger.info("White balance: auto")
                    camera.white_balance_auto()
                elif args.white_balance == "indoor":
                    logger.info("White balance: indoor")
                    camera.white_balance_indoor()
                elif args.white_balance == "outdoor":
                    logger.info("White balance: outdoor")
                    camera.white_balance_outdoor()
            
            if args.preset and args.action:
                preset_num = args.preset
                if args.action == "store":
                    logger.info(f"Storing preset {preset_num}")
                    # In real implementation, would query camera position
                elif args.action == "restore":
                    logger.info(f"Restoring preset {preset_num}")
                    # In real implementation, would move to stored position
        
        finally:
            # Disconnect
            self.camera_manager.disconnect_camera(camera_name)
            logger.info("Disconnected")
        
        return 0
    
    def _list_devices(self) -> None:
        """List available serial ports."""
        ports = self.camera_manager.get_available_ports()
        
        if not ports:
            print("No serial ports found")
            return
        
        print("Available Serial Ports:")
        print("-" * 40)
        for i, port in enumerate(ports, 1):
            print(f"{i}. {port}")


def main() -> int:
    """Entry point for CLI."""
    cli = CommandLineInterface()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
