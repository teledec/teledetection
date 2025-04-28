"""Utils file."""

from teledetection import cli


STAC_EP_DEV = "https://stacapi-dev.stac.teledetection.fr"
S3_SIGNING_EP_DEV = "https://s3-signing-dev.stac.teledetection.fr/"


def set_test_stac_ep() -> None:
    """Change stac endpoint for tests."""
    cli.DEFAULT_STAC_EP = STAC_EP_DEV
