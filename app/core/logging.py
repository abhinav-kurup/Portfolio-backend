# app/core/logging.py

import logging
import sys
from app.core.config import settings

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("portfolio")

    if logger.handlers:
        return logger                         # already set up, return existing

    level = logging.DEBUG if settings.DEBUG else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False

    return logger