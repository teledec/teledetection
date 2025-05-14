"""Push test module."""

import os
import time
import datetime
import requests
import pystac_client

from utils import run_cli_cmd, should_fail

import teledetection
from teledetection.cli import (
    _create_new_key,
    _get_all_keys,
    apikey,
)
from teledetection.sdk.logger import get_logger_for


STAC_ENDPOINT = "https://api.stac.teledetection.fr"

log = get_logger_for(__name__)


def _search(collection, bbox, asset_key):
    """STAC search."""
    start = time.time()
    api = pystac_client.Client.open(
        STAC_ENDPOINT,
        modifier=teledetection.sign_inplace,
    )
    res = api.search(
        bbox=bbox,
        datetime=["2017-01-01", "2022-12-31"],
        collections=[collection],
    )
    nb = 100
    for i, item in enumerate(res.items()):
        log.info(i)
        if i == nb:
            break
        url = item.assets[asset_key].href
        assert "Amz" in url

    elapsed = time.time() - start
    log.info(f"Took {round(elapsed, 2)} s")

    response = requests.get(url, timeout=5, stream=True)
    response.raise_for_status()


def _spot67():
    """Test spot-6/7 collection."""
    _search(bbox=[-3.75, 30, 10, 60], collection="spot-6-7-drs", asset_key="src_xs")


def _super_s2():
    """Test Super-S2 collection."""
    _search(
        bbox=[3.75, 43.58, 3.95, 43.67],
        collection="super-sentinel-2-l2a",
        asset_key="img",
    )


def _misc():
    """Various tests."""

    def test_userinfo():
        """Test userinfo method."""
        log.info("User infos: %s", teledetection.get_userinfo())

    def test_username():
        """Test userinfo method."""
        log.info("Username: %s", teledetection.get_username())

    test_userinfo()
    test_username()


def _headers(key: str):
    """Get headers test."""
    headers = teledetection.get_headers()
    log.info("Got headers")
    assert headers
    assert headers.get(key)


def _perform(key: str):
    """Perform tests."""
    _headers(key)
    _misc()
    _super_s2()
    _spot67()


def _oauth2_needing_reauth():
    """Some tests that need OAuth2 reauth."""
    # Save a JTW
    oauth2 = teledetection.sdk.oauth2
    good_jwt = teledetection.sdk.model.JWT.from_config_dir()

    # Screw saved JTW (expiry dates)
    jwt = good_jwt.model_copy()
    jwt.expires_in = 0
    jwt.to_config_dir()
    time.sleep(1)
    assert oauth2.OAuth2Session().get_access_token()

    # Screw saved JTW (tokens)
    jwt = good_jwt.model_copy()
    jwt.access_token += "corrupted"
    jwt.refresh_token += "corrupted"
    jwt.to_config_dir()
    assert oauth2.OAuth2Session().get_access_token()

    log.warning(
        """
        ****************************************************************************

        Simulate an expired authentication !
        You developer will have to wait! sorry...

        DO NOT LOGIN PLEASE, THIS TEST IS PURPOSELY INTENDED TO FAIL

        ****************************************************************************
        """
    )
    right_cfg_dir = teledetection.sdk.settings.get_config_path()
    cfg_dir_cpy = f"{right_cfg_dir}_old"
    os.rename(right_cfg_dir, cfg_dir_cpy)
    oauth2_sess = oauth2.OAuth2Session()
    oauth2_sess.jwt = None
    should_fail(oauth2_sess.get_access_token, [], oauth2.ExpiredAuthLinkError)
    os.rename(cfg_dir_cpy, right_cfg_dir)


def test_sdk():
    """Test SDK auth with various authentication methods."""
    # QR-code will be shown there. An OAuth2 token will be generated.
    log.info("Testing key management")

    # Revoke all keys from CLI
    run_cli_cmd(apikey, ["revoke-all"])
    assert len(_get_all_keys()) == 0

    # Test CLI's list with 0 key
    run_cli_cmd(apikey, ["list"])

    # Create new key from CLI
    run_cli_cmd(apikey, ["create"])
    keys = _get_all_keys()
    assert isinstance(keys, list)
    assert len(keys) == 1
    run_cli_cmd(apikey, ["create", "my super key123"])
    keys = _get_all_keys()
    assert isinstance(keys, list)
    assert len(keys) == 2

    # Revoke a key from CLI
    key = _create_new_key(description="key to be deleted")
    access_key = key["access-key"]
    run_cli_cmd(apikey, ["revoke", access_key])
    assert access_key not in _get_all_keys()

    # Register key with CLI
    run_cli_cmd(apikey, ["register"])

    # Remove key with CLI
    run_cli_cmd(apikey, ["remove"])

    # List keys with CLI
    run_cli_cmd(apikey, ["list"])

    log.info("Testing SDK with OAuth2")

    # Apply configuration (none here, because we have removed all the
    # API keys, so now we only rely on the OAuth2 JWT token)
    teledetection.sdk.http.session.prepare_connection_method()

    # Tests and expect authorization bearer in headers
    _perform("authorization")

    log.info("Test SDK with API Key from env. var.")

    # Create a key, get the key as dict
    key = _create_new_key(description="")
    assert key

    # Put the key in env. var.
    os.environ["TLD_ACCESS_KEY"] = key["access-key"]
    os.environ["TLD_SECRET_KEY"] = key["secret-key"]

    # Ensure environment variables are used
    teledetection.sdk.http.session.prepare_connection_method()

    # Tests and expect access key in headers
    _perform("access-key")

    # Remove key
    run_cli_cmd(apikey, ["revoke", key["access-key"]])
    os.environ.pop("TLD_ACCESS_KEY")
    os.environ.pop("TLD_SECRET_KEY")

    log.info("Testing SDK with API key")

    # Create a new API key stored in the .config folder
    run_cli_cmd(apikey, ["register"])

    # Ensure that the API key is used, even when the .jwt
    # is here after the OAuth2 connection.
    teledetection.sdk.http.session.prepare_connection_method()

    # Tests and expect access key in headers
    _perform("access-key")

    # Delete locally stored key
    run_cli_cmd(apikey, ["remove"])

    # Switch back to OAuth2
    teledetection.sdk.http.session.prepare_connection_method()

    if os.environ.get("SKIP_AUTH_LINK") not in ("on", "true", "ON", "TRUE", "1"):
        _oauth2_needing_reauth()


def test_cfg_dir():
    """Test config dir."""
    assert os.path.exists(teledetection.sdk.settings.get_config_path())


def test_http():
    """Test http module."""
    http = teledetection.sdk.http
    assert isinstance(http.BareConnectionMethod().get_headers(), dict)
    assert not http.BareConnectionMethod().get_headers()

    assert teledetection.sdk.http.get_headers()
    assert teledetection.sdk.http.get_userinfo()
    assert teledetection.sdk.http.get_username()

    # Revoke all API keys
    run_cli_cmd(apikey, ["revoke-all"])

    http_sess = http.HTTPSession()
    http.ENV.tld_disable_auth = True
    assert isinstance(http_sess.get_method(), http.BareConnectionMethod)

    http_sess = http.HTTPSession()
    http.ENV.tld_disable_auth = False
    assert isinstance(http_sess.get_method(), http.OAuth2ConnectionMethod)

    should_fail(
        http_sess.post,
        {"route": "nonexistent-route", "params": {}},
        requests.exceptions.HTTPError,
    )


def test_should_fail():
    """Test should_fail function."""

    def no_error():
        print("yo")

    try:
        should_fail(no_error, [], ValueError)
    except AssertionError:
        # Message "this test should fail"
        pass


def test_model():
    """Model tests."""
    model = teledetection.sdk.model
    file = "/non-existent-dir/file.json"
    model.Serializable().to_file(file)


def test_oauth2():
    """OAuth2 tests."""
    oauth2 = teledetection.sdk.oauth2

    # Not implemented error
    gmb = oauth2.GrantMethodBase()
    gmb.client_id = "client"
    should_fail(gmb.get_first_token, [], NotImplementedError)

    # Simulate a failure in refresh token
    teledetection.sdk.utils.ENV.tld_retry_total = 2
    jwt = teledetection.sdk.model.JWT(
        access_token="",
        expires_in=0,
        refresh_token="",
        refresh_expires_in=0,
        token_type="",
    )
    should_fail(gmb.refresh_token, [jwt], oauth2.RefreshTokenError)

    # Test working refresh token
    oauth2_sess = oauth2.OAuth2Session()
    oauth2_sess._refresh_if_needed()  # pylint: disable=protected-access

    # Simulate a failure in get first token
    oauth2_sess.grant.client_id = "not-existing-client-id"
    oauth2_sess.grant._token_endpoint = None  # pylint: disable=protected-access
    should_fail(oauth2_sess.grant.get_first_token, [], ConnectionError)

    # Save no jwt
    oauth2.OAuth2Session().save_token(datetime.datetime.now())


def _check_signed(s: str):
    """Check that s contains signature."""
    assert all(
        word in s
        for word in (
            "X-Amz-Algorithm",
            "X-Amz-Credential",
            "X-Amz-Date",
            "X-Amz-Expires",
            "X-Amz-SignedHeaders",
            "X-Amz-Signature",
        )
    )


def test_sign():
    """Test signing module."""
    should_fail(teledetection.sign, [1234], TypeError)
    assert teledetection.sdk.signing.is_vrt_string("<VRTDataset...</VRTDataset>")

    # Get an asset href
    api = pystac_client.Client.open(
        STAC_ENDPOINT,
        modifier=teledetection.sign_inplace,
    )
    res = api.search()
    item = next(res.items())
    href = item.assets[list(item.assets.keys())[0]].href

    # Asset signing (copy)
    for asset in item.assets.values():
        asset_clone = teledetection.sign(asset)
        _check_signed(asset_clone.href)

    # Item signing (copy)
    item_clone = teledetection.sign(item)
    for asset in item_clone.assets.values():
        _check_signed(asset.href)

    # Item signing (in place)
    teledetection.sign_inplace(item)
    for asset in item.assets.values():
        _check_signed(asset.href)

    # Asset signing (in place)
    item = next(res.items())
    for asset in item.assets.values():
        teledetection.sign_inplace(asset)
        _check_signed(asset.href)

    # URL signing
    _check_signed(teledetection.sign(href))

    # VRT string signing
    vrt_like = f"<VRTDataset>...dummy VRT here...{href}</VRTDataset>"
    _check_signed(teledetection.sign(vrt_like))

    # URL outside domain signing
    url_out = "https://something-else-outside.org/file.tif"
    assert teledetection.sign(url_out) == url_out
