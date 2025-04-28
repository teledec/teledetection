"""Some helpers."""

import os
import logging
import requests
import urllib3.util.retry

# Logger
LOGLEVEL = os.environ.get("LOGLEVEL") or "INFO"
logging.basicConfig(level=LOGLEVEL)


def create_session(retry_total: int = 5, retry_backoff_factor: float = 0.8):
    """Create a session for requests."""
    session = requests.Session()
    retry = urllib3.util.retry.Retry(
        total=retry_total,
        backoff_factor=retry_backoff_factor,
        status_forcelist=[404, 429, 500, 502, 503, 504],
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


def get_logger_for(name: str):
    """Get logger for a named module."""
    logger = logging.getLogger(name)
    logger.setLevel(level=LOGLEVEL)
    return logger
