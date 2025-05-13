"""This module is used to upload files using HTTP requests."""

from teledetection.sdk.signing import sign_url_put
from teledetection.sdk.utils import create_session


def push(local_filename: str, target_url: str):
    """Publish a local file to the cloud."""
    remote_presigned_url = sign_url_put(target_url)

    session = create_session()

    with open(local_filename, "rb") as f:
        ret = session.put(remote_presigned_url, data=f, timeout=10)

    if ret.status_code == 200:
        return remote_presigned_url

    ret.raise_for_status()
    return ""
