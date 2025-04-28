"""Theia-dumper Command Line Interface."""

import os
import tempfile
import subprocess
import click
from typing import Dict, List

from .sdk.model import ApiKey
from .sdk.http import OAuth2ConnectionMethod
from .sdk.utils import get_logger_for, create_session
from .upload import diff
from .upload.stac import (
    StacTransactionsHandler,
    StacUploadTransactionsHandler,
    DEFAULT_S3_EP,
    DEFAULT_STAC_EP,
    DEFAULT_S3_STORAGE,
)


@click.group(help="Teledetection CLI")
def app() -> None:
    """Teledetection Command Line Interface."""


log = get_logger_for(__name__)
conn = OAuth2ConnectionMethod()


def _http(route: str):
    """Perform an HTTP request."""
    session = create_session()
    ret = session.get(
        f"{conn.endpoint}{route}",
        timeout=5,
        headers=conn.get_headers(),
    )
    ret.raise_for_status()
    return ret


def _create_key() -> Dict[str, str]:
    """Create an API key."""
    return _http("create_api_key").json()


def _list_keys() -> List[str]:
    """List all generated API keys."""
    return _http("list_api_keys").json()


def _revoke_key(key: str):
    """Revoke an API key."""
    _http(f"revoke_api_key?access_key={key}")
    log.info(f"API key {key} revoked")


@app.command(help="Create and show a new API key")
def create_key():
    """Create and show a new API key."""
    log.info(f"Got a new API key: {_create_key()}")


@app.command(help="List all API keys")
def list_keys():  # [redefined-builtin]
    """List all API keys."""
    log.info(f"All generated API keys: {_list_keys()}")


@app.command(help="Revoke all API keys")
def revoke_all_keys():
    """Revoke all API keys."""
    keys = _list_keys()
    for key in keys:
        _revoke_key(key)
    if not keys:
        log.info("No API key found.")


@app.command(help="Revoke an API key")
@click.argument("access_key")
def revoke_key(access_key: str):
    """Revoke an API key."""
    _revoke_key(access_key)


@app.command(help="Get and store an API key")
def register_key():
    """Get and store an API key."""
    _ck = _create_key()
    log.info(_ck)
    ApiKey.from_dict(_ck).to_config_dir()
    log.info("API key successfully created and stored")


@app.command(help="Delete the stored API key")
@click.option("--dont-revoke", default=False)
def delete_key(dont_revoke: bool):
    """Delete the stored API key."""
    if not dont_revoke:
        _revoke_key(ApiKey.from_config_dir().access_key)
    ApiKey.delete_from_config_dir()


@app.command()
@click.argument("stac_obj_path")
@click.option(
    "--stac_endpoint",
    help="Endpoint to which STAC objects will be sent",
    type=str,
    default=DEFAULT_STAC_EP,
)
@click.option(
    "--storage_endpoint",
    type=str,
    help="Storage endpoint assets will be sent to",
    default=DEFAULT_S3_EP,
)
@click.option(
    "-b",
    "--storage_bucket",
    help="Storage bucket assets will be sent to",
    type=str,
    default=DEFAULT_S3_STORAGE,
)
@click.option(
    "-o",
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite assets if already existing",
)
@click.option(
    "--keep_cog_dir",
    help="Set a directory to keep converted COG files",
    type=str,
    nargs=1,
    default="",
)
def publish(
    stac_obj_path: str,
    stac_endpoint: str,
    storage_endpoint: str,
    storage_bucket: str,
    overwrite: bool,
    keep_cog_dir: str,
):
    """Publish a STAC object (collection or item collection)."""
    StacUploadTransactionsHandler(
        stac_endpoint=stac_endpoint,
        sign=False,
        storage_endpoint=storage_endpoint,
        storage_bucket=storage_bucket,
        assets_overwrite=overwrite,
        keep_cog_dir=keep_cog_dir,
    ).load_and_publish(stac_obj_path)


@app.command()
@click.option(
    "--stac_endpoint",
    help="Endpoint to which STAC objects will be sent",
    type=str,
    default=DEFAULT_STAC_EP,
)
@click.option("-c", "--col_id", type=str, help="STAC collection ID", required=True)
@click.option("-i", "--item_id", type=str, default=None, help="STAC item ID")
@click.option("-s", "--sign", is_flag=True, default=False, help="Sign assets HREFs")
@click.option("-p", "--pretty", is_flag=True, default=False, help="Pretty indent JSON")
@click.option("-o", "--out_json", type=str, help="Output .json file", required=True)
def grab(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    stac_endpoint: str,
    col_id: str,
    item_id: str,
    sign: bool,
    pretty: bool,
    out_json: str,
):
    """Grab a STAC object (collection, or item) and save it as .json."""
    StacTransactionsHandler(stac_endpoint=stac_endpoint, sign=sign).load_and_save(
        col_id=col_id, obj_pth=out_json, item_id=item_id, pretty=pretty
    )


@app.command()
@click.option(
    "--stac_endpoint",
    help="Endpoint to which STAC objects will be sent",
    type=str,
    default=DEFAULT_STAC_EP,
)
@click.option("-c", "--col_id", type=str, help="STAC collection ID", required=True)
@click.option("-i", "--item_id", type=str, default=None, help="STAC item ID")
def edit(stac_endpoint: str, col_id: str, item_id: str):
    """Edit a STAC object (collection, or item)."""
    with tempfile.NamedTemporaryFile(suffix=".json") as tf:
        StacTransactionsHandler(stac_endpoint=stac_endpoint, sign=False).load_and_save(
            col_id=col_id, obj_pth=tf.name, item_id=item_id, pretty=True
        )
        editor = os.environ.get("EDITOR") or "vi"
        subprocess.run([editor, tf.name], check=False)
        StacTransactionsHandler(stac_endpoint=stac_endpoint, sign=False).load_and_publish(
            obj_pth=tf.name
        )


@app.command()
@click.option(
    "--stac_endpoint",
    help="Endpoint to which STAC objects will be sent",
    type=str,
    default=DEFAULT_STAC_EP,
)
@click.option("-c", "--col_id", type=str, help="STAC collection ID", required=True)
@click.option("-i", "--item_id", type=str, default=None, help="STAC item ID")
def delete(
    stac_endpoint: str,
    col_id: str,
    item_id: str,
):
    """Delete a STAC object (collection or item)."""
    StacTransactionsHandler(stac_endpoint=stac_endpoint, sign=False).delete_item_or_col(
        col_id=col_id, item_id=item_id
    )


@app.command()
@click.option(
    "--stac_endpoint",
    help="Endpoint to which STAC objects will be sent",
    type=str,
    default=DEFAULT_STAC_EP,
)
def list_cols(
    stac_endpoint: str,
):
    """List collections."""
    cols = list(
        StacTransactionsHandler(stac_endpoint=stac_endpoint, sign=False).client.get_collections()
    )
    print(f"Found {len(cols)} collection(s):")
    for col in sorted(cols, key=lambda x: x.id):
        print(f"\t{col.id}")


@app.command()
@click.option(
    "--stac_endpoint",
    help="Endpoint to which STAC objects will be sent",
    type=str,
    default=DEFAULT_STAC_EP,
)
@click.option("-c", "--col_id", type=str, help="STAC collection ID", required=True)
@click.option("-m", "--max_items", type=int, help="Max number of items to display", default=20)
@click.option("-s", "--sign", is_flag=True, default=False, help="Sign assets HREFs")
def list_col_items(stac_endpoint: str, col_id: str, max_items: int, sign: bool):
    """List collection items."""
    items = StacTransactionsHandler(stac_endpoint=stac_endpoint, sign=sign).get_items(
        col_id=col_id, max_items=max_items
    )
    print(f"Found {len(items)} item(s):")
    for item in items:
        print(f"\t{item.id}")


@app.command()
@click.option(
    "--stac_endpoint",
    help="Endpoint to which STAC objects will be sent",
    type=str,
    default=DEFAULT_STAC_EP,
)
@click.option("-p", "--col_path", type=str, help="Local collection path", required=True)
@click.option(
    "-r",
    "--remote_id",
    type=str,
    help="Remote collection ID. If not specified, will use local collection ID",
    required=False,
)
def collection_diff(
    stac_endpoint: str,
    col_path: str,
    remote_id: str = "",
):
    """List collection items."""
    diff.compare_local_and_upstream(
        StacTransactionsHandler(stac_endpoint=stac_endpoint, sign=False),
        col_path,
        remote_id,
    )
