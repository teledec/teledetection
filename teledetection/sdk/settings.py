"""Settings from environment variables."""

import os
from pydantic_settings import BaseSettings
from pydantic.types import NonNegativeInt, PositiveInt, PositiveFloat
from pydantic import field_validator
import appdirs  # type: ignore
from .logger import get_logger_for

log = get_logger_for(__name__)

# Constants
APP_NAME = "teledetection"
MAX_URLS = 64
S3_STORAGE_DOMAIN = "meso.umontpellier.fr"
DEFAULT_SIGNING_ENDPOINT = "https://signing.stac.teledetection.fr"


class Settings(BaseSettings):
    """Environment variables."""

    tld_ttl_margin: NonNegativeInt = 1800
    tld_url_duration: NonNegativeInt = 0
    tld_config_dir: str = ""
    tld_access_key: str = ""
    tld_secret_key: str = ""
    tld_retry_total: PositiveInt = 10
    tld_retry_backoff_factor: PositiveFloat = 0.8
    tld_disable_auth: bool = False
    tld_signing_endpoint: str = DEFAULT_SIGNING_ENDPOINT

    @field_validator("tld_signing_endpoint", mode="after")
    @classmethod
    def val_endpoint_after(cls, val):
        """Post initialization."""
        if not val.lower().startswith(("http://", "https://")):
            raise ValueError(f"{val} must start with http[s]://")
        if not val.endswith("/"):
            val += "/"
        return val


ENV = Settings()


def get_config_path() -> str | None:
    """Get path to config directory (usually in ~/.config/)."""
    log.debug("Get config path")
    cfg_path = ENV.tld_config_dir or appdirs.user_config_dir(appname=APP_NAME)
    if not os.path.exists(cfg_path):
        try:
            os.makedirs(cfg_path)
            log.debug("Config dir created in %s", cfg_path)
        except PermissionError:
            log.warning("Unable to use config dir %s", cfg_path)
            cfg_path = None
    else:
        log.debug("Using existing config dir %s", cfg_path)
    return cfg_path
