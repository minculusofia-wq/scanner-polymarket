"""
Centralized logging configuration for Polymarket Scanner Bot
"""
import logging
import os
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for development"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        # Add color if terminal supports it
        if sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (usually __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or "polymarket")

    # Only configure if not already configured
    if not logger.handlers:
        # Get log level from environment
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Use colored formatter for development, plain for production
        if os.getenv("ENV", "development") == "production":
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = ColoredFormatter(
                '[%(levelname)s] %(name)s: %(message)s'
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Prevent propagation to root logger
        logger.propagate = False

    return logger


# Default logger instance
logger = get_logger("polymarket")
