"""Wrapped logger — users can configure log level in prefs and grab logs from disk.

Never print() from addon code; always go through this logger.
"""

from __future__ import annotations

import logging
import sys


_LOGGER_NAME = "stage"
_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [Stage] [%(levelname)s] %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.propagate = False

    _logger = logger
    return logger


def set_level(level: str) -> None:
    """Update the addon-wide log level. Called from prefs when user changes it."""
    get_logger().setLevel(getattr(logging, level, logging.INFO))
