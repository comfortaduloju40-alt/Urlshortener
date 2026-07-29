"""
Centralized logging setup.

Every module should do:
    from app.logger import get_logger
    logger = get_logger(__name__)

instead of configuring logging separately, so log format/level stays
consistent across the whole app and Railway's log viewer shows clean,
uniform output.
"""

import logging
import sys

from app.config import settings


def _configure_root_logger() -> None:
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL.upper())

    # Avoid duplicate handlers if this gets called more than once
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet down noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
