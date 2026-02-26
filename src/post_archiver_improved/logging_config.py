"""
Logging configuration and utilities for the post archiver.

This module provides centralized logging configuration with support for
different verbosity levels and colored output.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Formatter that adds color to log messages based on log level."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with color if output is a terminal."""
        formatted = super().format(record)

        # Only add color if outputting to a terminal
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, "")
            if color:
                formatted = f"{color}{formatted}{self.RESET}"

        return formatted


def setup_logging(
    verbose: bool = False,
    debug: bool = False,
    log_file: Path | None = None,
    logger_name: str = "post_archiver_improved",
) -> logging.Logger:
    """
    Set up logging configuration for the application.

    Args:
        verbose: Enable verbose output (INFO level)
        debug: Enable debug output (DEBUG level)
        log_file: Optional file path to also log to a file
        logger_name: Name for the logger instance

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)

    # Clear any existing handlers
    logger.handlers.clear()

    # Determine log level
    if debug:
        log_level = logging.DEBUG
    elif verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logger.setLevel(log_level)

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)

    # Format for console output
    console_format = "%(levelname)s: %(message)s"
    if debug:
        console_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    elif verbose:
        console_format = "%(asctime)s - %(levelname)s: %(message)s"

    console_formatter = ColoredFormatter(console_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)  # Always log everything to file

            # More detailed format for file output
            file_format = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
            file_formatter = logging.Formatter(file_format)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

        except OSError as e:
            logger.warning(f"Could not create log file {log_file}: {e}")

    # Prevent propagation to avoid duplicate messages
    logger.propagate = False

    return logger


def get_logger(name: str = "post_archiver_improved") -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
