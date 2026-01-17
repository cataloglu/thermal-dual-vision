"""Logging module for Smart Motion Detector."""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str = "smart_motion",
    level: str = "INFO",
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Setup and return a configured logger.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_string: Custom format string

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers - check if StreamHandler already exists
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            # StreamHandler already exists with same stream, update level and return
            handler.setLevel(getattr(logging, level.upper(), logging.INFO))
            logger.setLevel(getattr(logging, level.upper(), logging.INFO))
            return logger

    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Create formatter
    if format_string is None:
        format_string = "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)

    # Add handler
    logger.addHandler(handler)

    return logger


# Default logger instance
logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger with the given name.

    Args:
        name: Logger name (will be prefixed with 'smart_motion.')

    Returns:
        Logger instance
    """
    return logging.getLogger(f"smart_motion.{name}")
