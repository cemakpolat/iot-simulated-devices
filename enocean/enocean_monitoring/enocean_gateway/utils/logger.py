# src/utils/logger.py
"""
Logging utility for EnOcean Gateway
"""

import logging
import sys
from datetime import datetime
from typing import Optional


class Logger:
    """Custom logger with debug mode support"""

    def __init__(self, debug: bool = False, name: str = "EnOceanGateway"):
        self.debug_mode = debug
        self.name = name

        # Set up Python logging if debug mode is enabled
        if self.debug_mode:
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                stream=sys.stdout
            )
            self.logger = logging.getLogger(name)
        else:
            self.logger = None

    def _print_with_timestamp(self, level: str, message: str):
        """Print message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def info(self, message: str):
        """Log info message"""
        if self.logger:
            self.logger.info(message)
        else:
            print(message)

    def debug(self, message: str):
        """Log debug message"""
        if self.debug_mode:
            if self.logger:
                self.logger.debug(message)
            else:
                self._print_with_timestamp("DEBUG", message)

    def warning(self, message: str):
        """Log warning message"""
        if self.logger:
            self.logger.warning(message)
        else:
            self._print_with_timestamp("WARNING", message)

    def error(self, message: str):
        """Log error message"""
        if self.logger:
            self.logger.error(message)
        else:
            self._print_with_timestamp("ERROR", message)

    def success(self, message: str):
        """Log success message (info level with ✅)"""
        self.info(f"✅ {message}")

    def failure(self, message: str):
        """Log failure message (error level with ❌)"""
        self.error(f"❌ {message}")