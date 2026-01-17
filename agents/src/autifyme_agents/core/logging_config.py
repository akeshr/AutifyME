"""Centralized logging configuration for AutifyME agents.

Provides structured JSON logging in production and human-readable logs in development.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Configure directories for different environments
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Initialize variables that may be None in serverless environments
LOGS_DIR: Path
MEDIA_DIR: Path
LOG_FILE: Path | None

# For serverless environments (Vercel), use /tmp for writable directories
# For local development, use project directories
try:
    # Test if we can write to project directories (local development)
    LOGS_DIR = PROJECT_ROOT / "logs"
    MEDIA_DIR = PROJECT_ROOT / "media_downloads"
    LOGS_DIR.mkdir(exist_ok=True)
    MEDIA_DIR.mkdir(exist_ok=True)
    LOG_FILE = LOGS_DIR / f"autifyme_agents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
except (OSError, PermissionError):
    # Serverless environment - use /tmp and disable file logging
    import tempfile

    TMP_DIR = Path(tempfile.gettempdir()) / "autifyme"
    LOGS_DIR = TMP_DIR / "logs"
    MEDIA_DIR = TMP_DIR / "media"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE = None  # Disable file logging in serverless


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with context."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured fields."""
        # Base message
        message = super().format(record)

        # Add context if available
        if hasattr(record, "extra_context"):
            context = record.extra_context
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} | {context_str}"

        return message


def setup_logging(level: str = "DEBUG", enable_file_logging: bool = True) -> None:
    """Configure application-wide logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to log to file in addition to console
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with color-coded output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    console_format = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    # File handler with detailed output (disabled in serverless environments)
    if enable_file_logging and LOG_FILE is not None:
        file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        file_format = StructuredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-20s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",  # Removed .%f - not supported by strftime
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)

        # Log startup message
        root_logger.info(f"Logging initialized - file: {LOG_FILE}")
    elif enable_file_logging and LOG_FILE is None:
        # Serverless environment - file logging disabled
        root_logger.info("Logging initialized - file logging disabled (serverless environment)")

    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, **context: Any) -> None:
    """Log a message with additional context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **context: Additional context to include in log
    """
    log_func = getattr(logger, level.lower())
    extra = {"extra_context": context}
    log_func(message, extra=extra)


# Initialize logging on module import (can be reconfigured later)
setup_logging(level="DEBUG", enable_file_logging=True)
