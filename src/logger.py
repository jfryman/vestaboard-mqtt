"""Centralized logging configuration for Vestaboard MQTT Bridge.

This module provides a singleton-style logging configuration.
Call configure_logging() once at application startup, then use
standard logging.getLogger(__name__) throughout the codebase.
"""

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import AppConfig

# Module-level constants
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(config: "AppConfig") -> None:
    """Configure application-wide logging from AppConfig.

    This should be called once at application startup. After calling this,
    all modules can use logging.getLogger(__name__) and will automatically
    use the configured format and level.

    Args:
        config: Application configuration

    Example:
        >>> from .config import AppConfig
        >>> config = AppConfig.from_env()
        >>> configure_logging(config)
        >>> logger = logging.getLogger(__name__)
        >>> logger.info("Application started")
    """
    # Parse log level
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create and configure console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT))

    # Attach handler to root logger
    root_logger.addHandler(handler)
