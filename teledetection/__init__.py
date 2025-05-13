"""Teledetection SDK module."""

# flake8: noqa

from importlib.metadata import version, PackageNotFoundError
from teledetection.sdk.signing import (
    sign,
    sign_inplace,
    sign_urls,
    sign_item,
    sign_asset,
    sign_item_collection,
    sign_url_put,
)  # noqa
from .sdk.oauth2 import OAuth2Session  # noqa
from .sdk.http import get_headers, get_userinfo, get_username

try:
    __version__ = version("teledetection")
except PackageNotFoundError:
    pass
