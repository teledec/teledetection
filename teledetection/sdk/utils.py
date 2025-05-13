"""Some helpers."""

import requests
import urllib3.util.retry

from .settings import ENV


def create_session():
    """Create a session for requests."""
    session = requests.Session()
    retry = urllib3.util.retry.Retry(
        total=ENV.tld_retry_total,
        backoff_factor=ENV.tld_retry_backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session
