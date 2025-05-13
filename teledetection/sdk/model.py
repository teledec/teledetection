"""Models."""

import os
import json
from typing import Dict
from pydantic import BaseModel, Field, ConfigDict  # pylint: disable = no-name-in-module
from .logger import get_logger_for
from .settings import Settings, get_config_path

log = get_logger_for(__name__)


class Serializable(BaseModel):  # pylint: disable = R0903
    """Base class for serializable pyantic models."""

    model_config = ConfigDict(
        populate_by_name=True,
    )

    @classmethod
    def get_cfg_file_name(cls) -> str | None:
        """Get the config file name (without full path)."""
        name = f".{cls.__name__.lower()}"
        log.debug("Looking for config file for %s", name)
        cfg_pth = get_config_path()
        cfg_file = os.path.join(cfg_pth, name) if cfg_pth else None
        log.debug("Config file %sfound %s", "" if cfg_file else "not ", cfg_file or "")
        return cfg_file

    @classmethod
    def from_config_dir(cls):
        """Try to load from config directory."""
        cfg_file = cls.get_cfg_file_name()
        return cls.from_file(cfg_file) if cfg_file else None

    def to_config_dir(self):
        """Try to save to config files."""
        cfg_file = self.get_cfg_file_name()
        if cfg_file:
            self.to_file(cfg_file)

    @classmethod
    def from_dict(cls, dict: Dict):
        """Get the object from dict."""
        return cls(**dict)

    def to_dict(self) -> Dict[str, str]:
        """To dict."""
        return self.model_dump(by_alias=True)

    @classmethod
    def from_file(cls, file_path: str):
        """Load object from a file."""
        try:
            log.debug("Reading JSON file %s", file_path)
            with open(file_path, "r", encoding="utf-8") as file_handler:
                return cls(**json.load(file_handler))
        except (FileNotFoundError, IOError, json.decoder.JSONDecodeError) as err:
            log.debug("Cannot read object from config directory (%s).", err)

        return None

    def to_file(self, file_path: str):
        """Save the object to file."""
        try:
            log.debug("Writing JSON file %s", file_path)
            with open(file_path, "w", encoding="utf-8") as file_handler:
                json.dump(self.to_dict(), file_handler)
        except IOError as io_err:
            log.warning("Unable to save file %s (%s)", file_path, io_err)

    @classmethod
    def delete_from_config_dir(cls):
        """Delete the config file, if there."""
        cfg_file = cls.get_cfg_file_name()
        if cfg_file:
            os.remove(cfg_file)


class JWT(Serializable):
    """JWT model."""

    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_in: int
    token_type: str


class DeviceGrantResponse(BaseModel):  # pylint: disable = R0903
    """Device grant login response model."""

    verification_uri_complete: str
    device_code: str
    expires_in: int
    interval: int


class ApiKey(Serializable):
    """API key class."""

    access_key: str = Field(alias="access-key")
    secret_key: str = Field(alias="secret-key")

    @classmethod
    def from_env(cls):
        """Try to load from env."""
        env = Settings()
        if env.tld_access_key and env.tld_secret_key:
            return cls(
                access_key=env.tld_access_key,
                secret_key=env.tld_secret_key,
            )
        return None

    @classmethod
    def grab(cls):
        """Try to load an API key from env. or file."""
        return cls.from_env() or cls.from_config_dir()
