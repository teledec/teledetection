"""Teledetection package Command Line Interface."""

import os
import tempfile
import subprocess
import getpass
from typing import Dict, List
import datetime
import click

from .sdk.logger import get_logger_for

from .sdk.model import ApiKey
from .sdk.http import OAuth2ConnectionMethod
from .sdk.utils import create_session


@click.group(
    help="Teledetection CLI",
    context_settings={
        "help_option_names": ["-h", "--help"],
        "max_content_width": 120,
    },
)
def tld() -> None:
    """Teledetection Command Line Interface."""


log = get_logger_for(__name__)
conn = OAuth2ConnectionMethod()


def _http(route: str, params: dict | None = None):
    """Perform an HTTP request."""
    session = create_session()
    ret = session.get(
        f"{conn.endpoint}{route}",
        timeout=5,
        params=params,
        headers=conn.get_headers(),
    )
    ret.raise_for_status()
    return ret


def _get_all_keys() -> List[str]:
    """Retrieve all API keys."""
    return _http("list_api_keys_with_metadata").json()


def _create_new_key(description: str) -> Dict[str, str]:
    """Create a new API key."""

    def _default_desc():
        """Default description."""
        return (
            f"Created by {getpass.getuser()} on "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

    return _http(
        "create_api_key", params={"description": description or _default_desc()}
    ).json()


def do_create_key(description: str):
    """Create a new API key."""
    log.info("New API key %s created", _create_new_key(description=description))


def do_list_keys():
    """List all generated API keys."""
    keys = _get_all_keys()
    if keys:
        log.info("All existing API keys:")
        log.info("Creation date      \tAccess key      \t[Description]")
        # Prints: 2025-05-06 09:22:50  zPL9GaQrokbMCQGe
        for key in keys:
            log.info(
                "%s\t%s\t%s",
                key["created"].split(".")[0],
                key["access-key"],
                key["description"],
            )
    else:
        log.info("No API key found.")


def do_revoke_key(access_key: str):
    """Revoke an API key."""
    _http(f"revoke_api_key?access_key={access_key}")
    log.info(f"API key {access_key} revoked")


def do_revoke_all_keys():
    """Revoke all API keys."""
    keys = _get_all_keys()
    for key in keys:
        do_revoke_key(key["access-key"])
    if not keys:
        log.info("No API key to revoke.")


def do_register_key(description: str):
    """Create and store a new API key."""
    new_key = _create_new_key(description=description)
    ApiKey.from_dict(new_key).to_config_dir()
    log.info("New API key %s created and stored in config directory", new_key)


def do_remove_key(dont_revoke: bool):
    """Delete the stored API key."""
    if not dont_revoke:
        do_revoke_key(ApiKey.from_config_dir().access_key)
    ApiKey.delete_from_config_dir()


API_KEY_OPS = {
    "create": lambda arg: do_create_key(description=arg),
    "revoke": lambda arg: do_revoke_key(access_key=arg),
    "revoke-all": lambda arg: do_revoke_all_keys(),
    "register": lambda arg: do_register_key(description=arg),
    "remove": lambda arg: do_remove_key(dont_revoke=any(arg)),
    "list": lambda arg: do_list_keys(),
}


@tld.command()
@click.argument(
    "operation",
    type=click.Choice(list(API_KEY_OPS.keys()), case_sensitive=False),
    required=False,
)
@click.argument("argument", default="")
@click.pass_context
def apikey(ctx, operation: str, argument: str):
    """Manage API keys.

    \b
    Other operations:
      list        : List all available API keys

    \b
    Operations on locally-stored key:
      register    : Register a new key
      remove      : Remove a key provided in argument

    \b
    Manually input keys:
      create      : Create a new API key
      revoke      : Revoke a specific key
      revoke-all  : Revoke all keys
    """
    if not operation:
        click.echo(ctx.get_help())
        ctx.exit(0)
    API_KEY_OPS[operation](argument)


try:
    from .upload import diff
    from .upload.stac import (
        StacTransactionsHandler,
        StacUploadTransactionsHandler,
        DEFAULT_S3_EP,
        DEFAULT_STAC_EP,
        DEFAULT_S3_STORAGE,
    )

    @tld.command()
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

    @tld.command()
    @click.option(
        "--stac_endpoint",
        help="Endpoint to which STAC objects will be sent",
        type=str,
        default=DEFAULT_STAC_EP,
    )
    @click.option("-c", "--col_id", type=str, help="STAC collection ID", required=True)
    @click.option("-i", "--item_id", type=str, default=None, help="STAC item ID")
    @click.option("-s", "--sign", is_flag=True, default=False, help="Sign assets HREFs")
    @click.option(
        "-p", "--pretty", is_flag=True, default=False, help="Pretty indent JSON"
    )
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

    @tld.command()
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
            StacTransactionsHandler(
                stac_endpoint=stac_endpoint, sign=False
            ).load_and_save(
                col_id=col_id, obj_pth=tf.name, item_id=item_id, pretty=True
            )
            editor = os.environ.get("EDITOR") or "vi"
            subprocess.run([editor, tf.name], check=False)
            StacTransactionsHandler(
                stac_endpoint=stac_endpoint, sign=False
            ).load_and_publish(obj_pth=tf.name)

    @tld.command()
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
        StacTransactionsHandler(
            stac_endpoint=stac_endpoint, sign=False
        ).delete_item_or_col(col_id=col_id, item_id=item_id)

    @tld.command()
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
            StacTransactionsHandler(
                stac_endpoint=stac_endpoint, sign=False
            ).client.get_collections()
        )
        print(f"Found {len(cols)} collection(s):")
        for col in sorted(cols, key=lambda x: x.id):
            print(f"\t{col.id}")

    @tld.command()
    @click.option(
        "--stac_endpoint",
        help="Endpoint to which STAC objects will be sent",
        type=str,
        default=DEFAULT_STAC_EP,
    )
    @click.option("-c", "--col_id", type=str, help="STAC collection ID", required=True)
    @click.option(
        "-m", "--max_items", type=int, help="Max number of items to display", default=20
    )
    @click.option("-s", "--sign", is_flag=True, default=False, help="Sign assets HREFs")
    def list_col_items(stac_endpoint: str, col_id: str, max_items: int, sign: bool):
        """List collection items."""
        items = StacTransactionsHandler(
            stac_endpoint=stac_endpoint, sign=sign
        ).get_items(col_id=col_id, max_items=max_items)
        print(f"Found {len(items)} item(s):")
        for item in items:
            print(f"\t{item.id}")

    @tld.command()
    @click.option(
        "--stac_endpoint",
        help="Endpoint to which STAC objects will be sent",
        type=str,
        default=DEFAULT_STAC_EP,
    )
    @click.option(
        "-p", "--col_path", type=str, help="Local collection path", required=True
    )
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
except ImportError:
    log.info(
        "Running CLI without upload support. To install it, use `pip install teledetection[upload]`"
    )
