"""STAC stuff."""

import os
import re
import shutil
import json
from dataclasses import dataclass
from typing import List, cast
from urllib.parse import urljoin

import pystac
import pystac_client
import requests
from requests.exceptions import HTTPError
from requests.adapters import HTTPAdapter, Retry
from pystac import Collection, Item, ItemCollection
from rich.pretty import pretty_repr

from teledetection.sdk.logger import get_logger_for
from teledetection.sdk.http import get_headers
from teledetection.sdk.signing import sign, sign_inplace
from .transfer import push
from . import raster

logger = get_logger_for(__name__)

DEFAULT_STAC_EP = "https://api.stac.teledetection.fr"
DEFAULT_S3_EP = "https://s3-data.meso.umontpellier.fr"
DEFAULT_S3_STORAGE = "sm1-gdc-ext"


class STACObjectUnresolved(Exception):
    """Unresolved STAC object exception."""


class UnconsistentCollectionIDs(Exception):
    """Inconsistent STAC collection exception."""


class UnconsistentAssetNaming(Exception):
    """Inconsistent Asset Naming exception."""


class LogException(Exception):
    """Inconsistent Asset Naming exception."""


def _check_naming_is_compliant(s: str, allow_dot=False, allow_slash=False):
    _s = re.sub(r"[-|_]", r"", s)
    if allow_slash:
        _s = re.sub(r"\/", r"", _s)
    if allow_dot:
        _s = re.sub(r"\.", r"", _s)
    if not _s.isalnum():
        raise UnconsistentAssetNaming(
            f"{_s} does not only contain alphanumeric or - or _ chars"
        )


def create_session():
    """Create a requests session."""
    sess = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[
            408,
            419,
            425,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=frozenset(["PUT", "POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    sess.mount("http://", adapter=adapter)
    sess.mount("https://", adapter=adapter)
    return sess


def asset_exists(asset_url: str) -> bool:
    """Check that the item provided in parameter exists and is accessible."""
    sess = create_session()
    asset_url_signed = sign(asset_url)
    res = sess.get(asset_url_signed, stream=True)
    if res.status_code == 200:
        logger.info("Asset %s already exists.", asset_url)
        return True
    return False


def post_or_put(url: str, data: dict):
    """Post or put data to url."""
    headers = get_headers()
    sess = create_session()

    resp = sess.post(url, json=data, headers=headers, timeout=10)

    if resp.status_code == 409:
        # Exists, so update
        logger.info("Item at %s already exists, doing a PUT", url)
        resp = sess.put(
            f"{url}/{data['id']}",
            json=data,
            headers=headers,
            timeout=10,
        )
        # Unchanged may throw a 404
        if not resp.status_code == 404:
            resp.raise_for_status()

    try:
        resp.raise_for_status()
    except HTTPError as e:
        try:
            logger.error("Server returned: %s", pretty_repr(resp.json()))
        except LogException:
            logger.error("Server returned: %s", resp.text)
        raise e


def load_stac_obj(obj_pth: str) -> Collection | ItemCollection | Item:
    """Load a STAC object serialized on disk."""
    for obj_name, cls in {
        "collection": Collection,
        "item collection": ItemCollection,
        "item": Item,
    }.items():
        logger.debug("Try to read file %s", obj_pth)
        try:
            obj = getattr(cls, "from_file")(obj_pth)
            logger.info("Loaded %s from file %s", obj_name, obj_pth)
            logger.debug(obj.to_dict())
            return obj
        except pystac.errors.STACTypeError:
            pass

    raise STACObjectUnresolved(f"Cannot resolve STAC object ({obj_pth})")


def get_assets_root_dir(items: List[Item]) -> str:
    """Get the common prefix of all items assets paths.

    If the the common prefix is not a folder (/tmp/test1/a.tif, /tmp/test2/b.tif), returns /tmp.
    """
    prefix = os.path.commonpath(
        [asset.href for item in items for asset in item.assets.values()]
    )
    if os.path.isdir(prefix):
        return prefix + "/"
    return os.path.dirname(prefix) + "/"


def check_items_col_id(items: List[Item]):
    """Check that items have the same col_id."""
    if len(set(item.collection_id for item in items)) > 1:
        raise UnconsistentCollectionIDs("Collection ID must be the same for all items!")


def get_col_href(col: Collection):
    """Retrieve collection href."""
    for link in col.links:
        if link.rel == "self":
            return link.href
    return ""


def get_col_items(col: Collection) -> List[Item]:
    """Retrieve collection items."""
    col_href = get_col_href(col=col)
    return [
        cast(
            Item,
            load_stac_obj(
                os.path.join(os.path.dirname(col_href), link.href[2:])
                if link.href.startswith("./")
                else link.href
            ),
        )
        for link in col.links
        if link.rel == "item"
    ]


@dataclass
class StacTransactionsHandler:
    """Handle STAC and storage transactions."""

    stac_endpoint: str
    sign: bool

    @property
    def client(self):
        """STAC API client."""
        return pystac_client.Client.open(
            self.stac_endpoint,
            modifier=sign_inplace if self.sign else None,
        )

    def delete_item_or_col(self, col_id: str, item_id: str = ""):
        """Delete an item or a collection."""
        logger.info("Deleting %s%s", col_id, f"/{item_id}" if item_id else "")
        if item_id:
            url = f"{self.stac_endpoint}/collections/{col_id}/items/{item_id}"
        else:
            url = f"{self.stac_endpoint}/collections/{col_id}"
        resp = requests.delete(
            url,
            headers=get_headers(),
            timeout=5,
        )
        if resp.status_code != 200:
            logger.warning("Deletion failed (%s)", resp.text)

    def get_items(self, col_id: str, max_items: int = 10):
        """Get items in a collection."""
        logger.info("Get collection %s items", col_id)
        res = self.client.search(collections=[col_id], max_items=max_items)
        return list(res.items())

    def get_item(self, col_id: str, item_id: str) -> Item:
        """Retrieve a remote item."""
        logger.info("Retrieve item %s from collection %s", item_id, col_id)
        col = self.client.get_collection(col_id)
        if not col:
            raise ValueError(f"Collection {col_id} not found")
        item = col.get_item(item_id)
        if not item:
            raise ValueError(f"Item {item_id} (from collection {col_id}) not found")
        return item

    def publish_collection(self, col: Collection):
        """Publish an empty collection."""
        _check_naming_is_compliant(col.id)
        logger.info('Publishing collection "%s"', col.id)
        post_or_put(url=urljoin(self.stac_endpoint, "/collections"), data=col.to_dict())

    def publish_item(self, item: Item):
        """Publish an item."""
        _check_naming_is_compliant(item.id)
        col_id = item.collection_id
        logger.info('Publishing item "%s" in collection "%s"', item.id, col_id)
        post_or_put(
            urljoin(self.stac_endpoint, f"collections/{col_id}/items"),
            item.to_dict(transform_hrefs=False),
        )

    def update_collection_extent(self, col_id: str):
        """Update collection extent."""
        logger.info("Updating collection extent")
        results = self.client.search(limit=1000, collections=[col_id])
        col = self.client.get_collection(col_id)
        col.extent = pystac.Extent.from_items(items=list(results.items()))
        col.clear_links("items")
        self.publish_collection(col=col)

    def load_and_save(
        self, col_id: str, obj_pth: str, item_id: str = "", pretty: bool = True
    ):
        """Load and save locally (as .json file) the remote STAC object."""
        obj = (
            self.get_item(col_id=col_id, item_id=item_id)
            if item_id
            else self.client.get_collection(col_id)
        )
        logger.info("Writing file %s", obj_pth)
        with open(obj_pth, "w", encoding="utf-8") as file:
            json.dump(obj.to_dict(), file, indent=2 if pretty else None)

    def load_and_publish(self, obj_pth: str):
        """Load and publish the serialized STAC object."""
        obj = load_stac_obj(obj_pth=obj_pth)
        if isinstance(obj, Item):
            self.publish_item(item=obj)
        elif isinstance(obj, Collection):
            self.publish_collection(col=obj)
        elif isinstance(obj, ItemCollection):
            for item in obj.items:
                self.publish_item(item=item)
        else:
            raise TypeError(
                f"Invalid type, must be ItemCollection or Collection (got {type(obj)})"
            )


@dataclass
class StacUploadTransactionsHandler(StacTransactionsHandler):
    """Handle STAC and storage transactions."""

    storage_endpoint: str
    storage_bucket: str
    assets_overwrite: bool
    keep_cog_dir: str = ""

    def publish_item_and_push_assets(self, item: Item, assets_root_dir: str):
        """Publish an item and push all its assets.

        Args:
            item: Stac item to publish
            assets_root_dir: Common path to all files, defined as assets root dir
        """
        tgt_root_url = urljoin(
            self.storage_endpoint, f"{self.storage_bucket}/{item.collection_id}/"
        )

        logger.debug("Itemid = %s", item.id)

        _check_naming_is_compliant(self.storage_bucket)
        _check_naming_is_compliant(item.id)
        for _, asset in item.assets.items():
            local_filename = asset.href
            logger.debug("Local file: %s", local_filename)

            file_relative_path = local_filename.replace(assets_root_dir, "")
            target_url = urljoin(tgt_root_url, file_relative_path)

            # Check that url part after storage bucket is compliant
            _check_naming_is_compliant(
                file_relative_path,
                allow_dot=True,
                allow_slash=True,
            )
            logger.debug("Target file: %s", target_url)

            # Add raster metadata to asset
            logger.debug("Updating assets metadata for rasters...")
            if raster.is_raster(local_filename):
                raster.apply_proj_extension(asset)
                raster.apply_raster_extension(asset)
                asset.media_type = pystac.MediaType.COG

            # Skip when target file exists and overwrite is not enabled
            if not self.assets_overwrite:
                if asset_exists(target_url):
                    asset.href = target_url
                    continue

            # Check is_cog, converts if not
            cogconv = False
            if raster.is_raster(local_filename):
                if not raster.is_cog(local_filename):
                    orig_filename = local_filename
                    local_filename = raster.convert_to_cog(
                        orig_filename,
                        keep_cog_dir=self.keep_cog_dir,
                    )
                    cogconv = True

            # Upload file
            logger.info("Uploading %s to %s...", local_filename, target_url)
            try:
                push(local_filename=local_filename, target_url=target_url)
            except Exception as e:
                logger.error(e)
                raise e

            # Update assets hrefs
            logger.debug("Updating assets HREFs ...")
            asset.href = target_url

            # Delete temp cog
            if cogconv and not self.keep_cog_dir:
                logger.debug("Deleting temporary COG ...")
                shutil.rmtree(os.path.dirname(local_filename))
                local_filename = orig_filename

        # Add published metadata to item
        logger.debug("Updating item metadata ...")
        raster.apply_published_extension(item)

        # Push item
        self.publish_item(item=item)

    def publish_items_and_push_assets(self, items: List[Item]):
        """Publish items."""
        if not items:
            logger.info("No item to publish.")
            return
        check_items_col_id(items=items)
        assets_root_dir = get_assets_root_dir(items=items)
        logger.debug("Assets root directory: %s", assets_root_dir)
        for item in items:
            self.publish_item_and_push_assets(
                item=item, assets_root_dir=assets_root_dir
            )
        # Update collection extent
        col_id = items[0].collection_id
        if not col_id:
            raise UnconsistentCollectionIDs(
                f"Collection id is None for item {items[0].id}"
            )
        self.update_collection_extent(col_id=col_id)

    def publish_collection_with_items(self, col: Collection):
        """Publish a collection and all its items."""
        items = get_col_items(col=col)
        check_items_col_id(items)
        self.publish_collection(col=col)
        self.publish_items_and_push_assets(items=items)

    def publish_item_collection(self, item_collection: ItemCollection):
        """Publish an item collection and all of its items."""
        self.publish_items_and_push_assets(items=item_collection.items)

    def load_and_publish(self, obj_pth: str):
        """Load and publish the serialized STAC object."""
        obj = load_stac_obj(obj_pth=obj_pth)
        if isinstance(obj, Item):
            self.publish_items_and_push_assets(items=[obj])
        elif isinstance(obj, Collection):
            self.publish_collection_with_items(col=obj)
        elif isinstance(obj, ItemCollection):
            self.publish_item_collection(item_collection=obj)
        else:
            raise TypeError(
                f"Invalid type, must be ItemCollection or Collection (got {type(obj)})"
            )
