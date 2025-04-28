"""Push test module."""

import os
import time
import shutil
import requests
import pystac
import pystac_client
from click.testing import CliRunner

import teledetection
from teledetection.sdk.utils import get_logger_for


logger = get_logger_for(__name__)



ENDPOINT = "https://stacapi-cdos.apps.okd.crocc.meso.umontpellier.fr"


def _push():
    import teledetection
    LOCAL_FILENAME = "/tmp/toto.txt"

    with open(LOCAL_FILENAME, "w", encoding="utf-8") as f:
        f.write("hello world")

    TARGET_URL = "https://s3-data.meso.umontpellier.fr/sm1-gdc-tests/titi.txt"

    teledetection.push(local_filename=LOCAL_FILENAME, target_url=TARGET_URL)
    print("push OK")

    signed_url = teledetection.sign(TARGET_URL)
    print("sign OK")

    res = requests.get(signed_url, stream=True, timeout=10)
    assert res.status_code == 200, "Get NOK"
    print("get OK")

    print("Done")


def _spot67():
    import teledetection

    start = time.time()
    api = pystac_client.Client.open(
        ENDPOINT,
        modifier=teledetection.sign_inplace,
    )
    res = api.search(
        bbox=[-3.75, 30, 10, 60],
        datetime=["2017-01-01", "2022-12-31"],
        collections=["spot-6-7-drs"],
    )
    urls = [item.assets["src_xs"].href for item in res.items()]
    print(f"{len(urls)} items found")
    assert len(urls) > 1000

    assert "Amz" in urls[0]

    print(urls[0])

    elapsed = time.time() - start
    print(f"Took {round(elapsed, 2)} s")


def _super_s2():
    import teledetection

    api = pystac_client.Client.open(
        ENDPOINT,
        modifier=teledetection.sign_inplace,
    )
    res = api.search(
        bbox=[3.75, 43.58, 3.95, 43.67],
        datetime=["2017-01-01", "2022-12-31"],
        collections=["super-sentinel-2-l2a"],
    )
    urls = [item.assets["img"].href for item in res.items()]
    assert len(urls) == 672

    # ItemCollection (bug #17)
    ic: pystac.ItemCollection = pystac.item_collection.ItemCollection(res.items())
    teledetection.sign_inplace(ic)

    item = ic.items[0]
    _, asset = next(iter(item.get_assets().items()))

    response = requests.get(asset.href, timeout=5)
    response.raise_for_status()


def _misc():
    def test_userinfo():
        """Test userinfo method."""
        print(teledetection.get_userinfo())

    def test_username():
        """Test userinfo method."""
        print(teledetection.get_username())

    test_userinfo()
    test_username()


def _headers(key: str):
    headers = teledetection.get_headers()
    print(f"Got headers: {headers}")
    assert headers
    assert headers.get(key)


def _rm_appdir():
    shutil.rmtree(teledetection.sdk.settings.get_config_path())


def test_sdk_oauth2():

    logger.info("Testing SDK with OAuth2")

    _rm_appdir()

    _misc()
    _headers("authorization")
    _push()
    _super_s2()
    _spot67()


def test_cfg_dir():
    assert os.path.exists(teledetection.sdk.settings.get_config_path())


def test_sdk():

    logger.info("Testing SDK with API key")

    _rm_appdir()
    
    runner = CliRunner()
    from teledetection.cli import register_key, delete_key
    runner.invoke(register_key, [])

    teledetection.sdk.http.session.prepare_connection_method()

    _misc()
    _headers("access-key")
    _push()
    _super_s2()
    _spot67()

    assert runner.invoke(delete_key, [])

def test_sdk_apikey_from_env():
    _rm_appdir()

    key = teledetection.cli._create_key()
    assert key
    
    import os
    os.environ["TLD_ACCESS_KEY"] = key["access-key"]
    os.environ["TLD_SECRET_KEY"] = key["secret-key"]

    teledetection.sdk.http.session.prepare_connection_method()

    _misc()
    _headers("access-key")
    _push()
    _super_s2()
    _spot67()

    os.environ.pop("TLD_ACCESS_KEY")
    os.environ.pop("TLD_SECRET_KEY")
    
