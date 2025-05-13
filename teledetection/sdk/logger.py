"""Logger module."""

import os
import logging

# Logger
LOGLEVEL = os.environ.get("LOGLEVEL") or "INFO"
logging.basicConfig(level=LOGLEVEL)


def get_logger_for(name: str):
    """Get logger for a named module."""
    logger = logging.getLogger(name)
    logger.setLevel(level=LOGLEVEL)
    return logger
