"""This module is used to upload files using HTTP requests."""

from .signing import sign_url_put
from .utils import create_session


def push(
    local_filename: str,
    target_url: str,
    retry_total: int = 5,
    retry_backoff_factor: float = 0.8,
):
    """Publish a local file to the cloud."""
    remote_presigned_url = sign_url_put(target_url)

    session = create_session(
        retry_total=retry_total,
        retry_backoff_factor=retry_backoff_factor,
    )

    with open(local_filename, "rb") as f:
        ret = session.put(remote_presigned_url, data=f, timeout=10)

    if ret.status_code == 200:
        return remote_presigned_url

    ret.raise_for_status()
    return ""
