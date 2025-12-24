"""Test settings."""

import os
from utils import should_fail
from teledetection.sdk.settings import Settings


def test_tld_signing_endpoint():
    """Test the validity of tld_signing_endpoint."""
    os.environ["TLD_SIGNING_ENDPOINT"] = "ghttp://toto.org"
    should_fail(Settings, [], ValueError)
    os.environ["TLD_SIGNING_ENDPOINT"] = "http://toto.org"
    s = Settings()
    assert s.tld_signing_endpoint == "http://toto.org/"
    os.environ.pop("TLD_SIGNING_ENDPOINT", None)


def test_cfg_path():
    """Test the config path retrieval."""
    cfg_dir = "/tmp/config"
    os.environ["TLD_CONFIG_DIR"] = cfg_dir
    s = Settings()
    assert s.tld_config_dir == cfg_dir
    cfg_dir = "/tmp"
    os.environ["TLD_CONFIG_DIR"] = cfg_dir
    s = Settings()
    assert s.tld_config_dir == cfg_dir
    os.environ.pop("TLD_CONFIG_DIR", None)
