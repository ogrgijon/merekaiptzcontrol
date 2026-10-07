"""
MerekaiPTZControl Application Entry Point

Main entry point for the MerekaiPTZControl camera control application.
"""

import sys
import logging

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from src.app_paths import app_data_dir, resource_path
from src.ui.main_window import MainWindow


# Configure logging
def setup_logging():
    """Setup application logging."""
    log_dir = app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "merekaiptzcontrol.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("MerekaiPTZControl application started")
    logger.info("=" * 60)
    
    return logger


def main():
    """Application entry point."""
    logger = setup_logging()
    
    try:
        # Create application
        app = QApplication(sys.argv)
        
        # Set application metadata
        app.setApplicationName("MerekaiPTZControl")
        app.setApplicationVersion("1.0.0")
        app.setApplicationDisplayName("MerekaiPTZControl - PTZ Camera Control")
        app.setWindowIcon(QIcon(str(resource_path("resources/merekaiptzcontrol.png"))))
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Main window displayed")
        
        # Run application
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
