"""
LOGGING MODULE
--------------
Uses Loguru — a modern, structured logging library for Python.
Provides colored console output and optional file logging.
"""

import sys
from loguru import logger
from app.core.config import settings


def setup_logging():
    """Configure application-wide logging."""
    logger.remove()  # Remove default handler

    level = "DEBUG" if settings.DEBUG else "INFO"

    # Console logging with colors and structured format
    logger.add(
        sys.stdout,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # File logging (rotated daily, kept 7 days)
    logger.add(
        "logs/app.log",
        level="INFO",
        rotation="1 day",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    )

    logger.info(f"Logging initialized at level: {level}")
