"""Signing module.

Revamp of Microsoft Planetary Computer SAS, using custom URL signing
endpoint instead.
"""

import collections.abc
import math
import re
import time
from copy import deepcopy
from datetime import datetime, timezone
from functools import singledispatch
from typing import Any, Dict, List, Mapping, TypeVar, cast
from enum import Enum
from urllib.parse import parse_qs, urlparse

import pystac_client
from pydantic import BaseModel, ConfigDict  # pylint: disable = no-name-in-module
from pystac import (
    Asset,
    Collection,
    Item,
    ItemCollection,
    STACObjectType,
)
from pystac.serialization.identify import identify_stac_object_type
from pystac_client import ItemSearch

from .http import session
from .settings import S3_STORAGE_DOMAIN, MAX_URLS, ENV
from .logger import get_logger_for


AssetLike = TypeVar("AssetLike", Asset, Dict[str, Any])

asset_xpr = re.compile(
    r"https:\/\/(?P<account>[A-z0-9-.]+?)"
    r"\.meso\.umontpellier\.fr\/(?P<blob>[^<]+)"  # ignore
)

log = get_logger_for(__name__)


class URLBase(BaseModel):  # pylint: disable = R0903
    """Base model for responses."""

    model_config = ConfigDict(populate_by_name=True)
    expiry: datetime


class SignedURL(URLBase):  # pylint: disable = R0903
    """Signed URL response."""

    href: str

    def ttl(self) -> float:
        """Return the number of seconds the token is still valid for."""
        return (self.expiry - datetime.now(timezone.utc)).total_seconds()


class SignedURLBatch(URLBase):  # pylint: disable = R0903
    """Signed URLs (batch of URLs) response."""

    hrefs: dict


# Cache of signing requests so we can reuse them
# Key is the signing URL, value is the S3 token
CACHE: Dict[str, SignedURL] = {}


@singledispatch
def sign(obj: Any, copy: bool = True) -> Any:
    """Sign the relevant URL with a S3 token allowing read access.

    All URLs belonging to supported objects are modified in-place, or returned
    by the function, depending on `copy`.
    Args:
        obj (Any): The object to sign. Must be one of:
            str (URL), Asset, Item, ItemCollection, or ItemSearch, or a
            mapping.
        copy (bool): Whether to sign the object in place, or make a copy.
            Has no effect for immutable objects like strings.

    Returns:
        Any: A copy of the object where all relevant URLs have been signed

    """
    raise TypeError(
        "Invalid type, must be one of: str, Asset, Item, ItemCollection, ItemSearch, or mapping"
    )


def sign_inplace(obj: Any) -> Any:
    """Sign the object in place.

    See :func:`teledetection.sign` for more.

    """
    return sign(obj, copy=False)


def is_vrt_string(string: str) -> bool:
    """Check whether a string looks like a VRT."""
    return string.strip().startswith("<VRTDataset") and string.strip().endswith(
        "</VRTDataset>"
    )


@sign.register(str)
def sign_string(url: str, copy: bool = True) -> str:
    """Sign a URL or VRT-like string containing URLs with a S3 Token.

    Signing with a S3 token allows read access to files in blob storage.

    Args:
        url (str): The HREF of the asset as a URL or a GDAL VRT

            Single URLs can be found on a STAC Item's Asset ``href`` value.
            Only URLs to assets in S3 Storage are signed, other URLs are
            returned unmodified.

            GDAL VRTs can combine many data sources into a single mosaic.
            A VRT can be  built quickly from the GDAL STACIT driver
            https://gdal.org/drivers/raster/stacit.html. Each URL to S3 Storage
            within the VRT is signed.
        copy (bool): No effect.

    Returns:
        str: The signed HREF or VRT

    """
    if is_vrt_string(url):
        return sign_vrt_string(url)
    return sign_urls(urls=[url])[url]


class SignURLRoute(Enum):
    """Different routes used for sign_urls."""

    SIGN_URLS_GET = "sign_urls"
    SIGN_URLS_PUT = "sign_urls_put"


def _generic_sign_urls(urls: List[str], route: SignURLRoute) -> Dict[str, str]:
    """Sign URLs with a S3 Token.

    Signing URL allows read access to files in storage.

    Args:
        urls: List of HREF to sign

            Single URLs can be found on a STAC Item's Asset ``href`` value.
            Only URLs to assets in S3 Storage are signed, other URLs are
            returned unmodified.
        route: API route

    Returns:
        dict of signed HREF: key = original URL, value = signed URL

    """
    signed_urls = {}
    for url in urls:
        stripped_url = url.rstrip("/")
        parsed_url = urlparse(stripped_url)
        if not parsed_url.netloc.endswith(S3_STORAGE_DOMAIN):
            # Outside our domain
            signed_urls[url] = url
        # elif parsed_url.netloc == "????":
        #     # special case for public assets storing thumbnails...
        #     return url
        else:
            parsed_qs = parse_qs(parsed_url.query)
            if set(parsed_qs) & {
                "X-Amz-Security-Token",
                "X-Amz-Signature",
                "X-Amz-Credential",
            }:
                #  looks like we've already signed it
                signed_urls[url] = url

    not_signed_urls = [url for url in urls if url not in signed_urls]
    signed_urls.update(
        {
            url: signed_url.href
            for url, signed_url in _generic_get_signed_urls(
                urls=not_signed_urls, route=route
            ).items()
        }
    )
    return signed_urls


def sign_urls(urls: List[str]) -> Dict[str, str]:
    """Sign multiple URLs for GET."""
    return _generic_sign_urls(urls=urls, route=SignURLRoute(SignURLRoute.SIGN_URLS_GET))


def sign_urls_put(urls: List[str]) -> Dict[str, str]:
    """Sign multiple URLs for PUT."""
    return _generic_sign_urls(urls=urls, route=SignURLRoute(SignURLRoute.SIGN_URLS_PUT))


def sign_url_put(url: str) -> str:
    """Sign a single URL for PUT."""
    urls = sign_urls_put([url])
    return urls[url]


def sign_vrt_string(vrt: str, copy: bool = True) -> str:  # pylint: disable = W0613  # noqa: E501
    """Sign a VRT-like string containing URLs from the storage.

    Signing URLs allows read access to files in storage.

    Args:
        vrt (str): The GDAL VRT

            GDAL VRTs can combine many data sources into a single mosaic. A VRT
            can be built quickly from the GDAL STACIT driver
            https://gdal.org/drivers/raster/stacit.html. Each URL to S3 Storage
            within the VRT is signed.
        copy (bool): No effect.

    Returns:
        str: The signed VRT

    """
    urls = []

    def _repl_vrt(m: re.Match):
        urls.append(m.string[slice(*m.span())])

    asset_xpr.sub(_repl_vrt, vrt)
    signed_urls = sign_urls(urls)

    # The "&" needs to be encoded in signed URLs inside the .vrt
    for url, signed_url in signed_urls.items():
        signed_urls[url] = signed_url.replace("&", "&Amp;")

    # Replace urls with signed urls (single pass)
    rep = dict((re.escape(k), v) for k, v in signed_urls.items())
    pattern = re.compile("|".join(rep.keys()))
    return pattern.sub(lambda m: rep[re.escape(m.group(0))], vrt)


@sign.register(Item)
def sign_item(item: Item, copy: bool = True) -> Item:
    """Sign all assets within a PySTAC item.

    Args:
        item (Item): The Item whose assets that will be signed
        copy (bool): Whether to copy (clone) the item or mutate it inplace.

    Returns:
        Item: An Item where all assets' HREFs have
        been replaced with a signed version. In addition, an "expiry"
        property is added to the Item properties indicating the earliest
        expiry time for any assets that were signed.

    """
    if copy:
        item = item.clone()
    urls = [asset.href for asset in item.assets.values()]
    signed_urls = sign_urls(urls=urls)
    for key, asset in item.assets.items():
        item.assets[key].href = signed_urls[asset.href]
    return item


@sign.register(Asset)
def sign_asset(asset: Asset, copy: bool = True) -> Asset:
    """Sign a PySTAC asset.

    Args:
        asset (Asset): The Asset to sign
        copy (bool): Whether to copy (clone) the asset or mutate it inplace.

    Returns:
        Asset: An asset where the HREF is replaced with a
        signed version.

    """
    if copy:
        asset = asset.clone()
    asset.href = sign_urls([asset.href])[asset.href]
    return asset


@sign.register(ItemCollection)
def sign_item_collection(
    item_collection: ItemCollection, copy: bool = True
) -> ItemCollection:
    """Sign a PySTAC item collection.

    Args:
        item_collection (ItemCollection): The ItemCollection whose assets will
            be signed
        copy (bool): Whether to copy (clone) the ItemCollection or mutate it
            inplace.

    Returns:
        ItemCollection: An ItemCollection where all assets'
        HREFs for each item have been replaced with a signed version. In
        addition, an "expiry" property is added to the Item properties
        indicating the earliest expiry time for any assets that were signed.

    """
    if copy:
        item_collection = item_collection.clone()
    urls = [asset.href for item in item_collection for asset in item.assets.values()]
    signed_urls = sign_urls(urls=urls)
    for item in item_collection:
        for key, asset in item.assets.items():
            item.assets[key].href = signed_urls[asset.href]
    return item_collection


@sign.register(ItemSearch)
def _search_and_sign(search: ItemSearch, copy: bool = True) -> ItemCollection:
    """Perform a PySTAC Client search, and sign the resulting item collection.

    Args:
        search (ItemSearch): The ItemSearch whose resulting item assets will
            be signed
        copy (bool): No effect.

    Returns:
        ItemCollection: The resulting ItemCollection of the search where all
            assets' HREFs for each item have been replaced with a signed
            version. In addition, a "expiry" property is added to the Item
            properties indicating the earliest expiry time for any assets that
            were signed.

    """
    if pystac_client.__version__ >= "0.5.0":
        items = search.item_collection()
    else:
        items = search.get_all_items()
    return sign(items)


@sign.register(Collection)
def sign_collection(collection: Collection, copy: bool = True) -> Collection:
    """Sign a collection.

    Args:
        collection: STAC Collection
        copy: copy or not the input

    Returns:
        signed (Collection): the STAC collection, now with signed URLs.

    """
    if copy:
        # https://github.com/stac-utils/pystac/pull/834 fixed asset dropping
        assets = collection.assets
        collection = collection.clone()
        if assets and not collection.assets:
            collection.assets = deepcopy(assets)

    urls = [collection.assets[key].href for key in collection.assets]
    signed_urls = sign_urls(urls=urls)
    for key, asset in collection.assets.items():
        collection.assets[key].href = signed_urls[asset.href]
    return collection


@sign.register(collections.abc.Mapping)
def sign_mapping(mapping: Mapping, copy: bool = True) -> Mapping:
    """Sign a mapping.

    Args:
        mapping (Mapping):

        The mapping (e.g. dictionary) to sign. This method can sign

            * Kerchunk-style references, which signs all URLs under the
              ``templates`` key. See https://fsspec.github.io/kerchunk/
              for more.
            * STAC items
            * STAC collections
            * STAC ItemCollections

        copy: Whether to copy (clone) the mapping or mutate it inplace.

    Returns:
        signed (Mapping): The dictionary, now with signed URLs.

    """
    if copy:
        mapping = deepcopy(mapping)

    types = (STACObjectType.ITEM, STACObjectType.COLLECTION)
    if all(key in mapping for key in ["version", "templates", "refs"]):
        urls = list(mapping["templates"].values())
        signed_urls = sign_urls(urls=urls)
        for key, url in mapping["templates"].items():
            mapping["templates"][key] = signed_urls[url]

    elif identify_stac_object_type(cast(Dict[str, Any], mapping)) in types:
        urls = [val["href"] for val in mapping["assets"].values()]
        signed_urls = sign_urls(urls=urls)
        for val in mapping["assets"].values():
            url = val["href"]
            val["href"] = signed_urls[url]

    elif mapping.get("type") == "FeatureCollection" and mapping.get("features"):
        urls = [
            val["href"]
            for feat in mapping["features"]
            for val in feat.get("assets", {}).values()
        ]
        signed_urls = sign_urls(urls=urls)
        for feature in mapping["features"]:
            for val in feature.get("assets", {}).values():
                url = val["href"]
                val["href"] = signed_urls[url]

    return mapping


sign_reference_file = sign_mapping


def _generic_get_signed_urls(
    urls: List[str],
    route: SignURLRoute,
) -> Dict[str, SignedURL]:
    """Get multiple signed URLs.

    This will use the URL from the cache if it's present and not too close
    to expiring. The generated URL will be placed in the cache.

    Args:
        urls: urls
        route: route (API)

    Returns:
        SignedURL: the signed URL

    """
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    log.debug("Get signed URLs for %s", urls)
    start_time = time.time()

    signed_urls = {}
    for url in urls:
        signed_url_in_cache = CACHE.get(url)
        if signed_url_in_cache and route == SignURLRoute.SIGN_URLS_GET:
            log.debug("URL %s already in cache", url)
            ttl = signed_url_in_cache.ttl()
            log.debug("URL %s TTL is %s", url, ttl)
            if ttl > ENV.tld_ttl_margin:
                log.debug(
                    "Using cache (%s > %s)",
                    ttl,
                    ENV.tld_ttl_margin,
                )
                signed_urls[url] = signed_url_in_cache
    not_signed_urls = [url for url in urls if url not in signed_urls]
    log.debug("Already signed URLs:\n %s", signed_urls)
    log.debug("Not signed URLs:\n %s", not_signed_urls)

    if not_signed_urls:
        # Refresh the token if there's less than
        # `settings.teledetection_ttl_margin seconds` remaining, in order to
        # give a small amount of time to do stuff with the url
        n_urls = len(not_signed_urls)
        log.debug("Number of URLs to sign: %s", n_urls)
        n_chunks = math.ceil(n_urls / MAX_URLS)
        log.debug("Number of chunks of URLs to sign: %s", n_chunks)
        for i_chunk in range(n_chunks):
            log.debug("Processing chunk %s/%s", i_chunk + 1, n_chunks)
            chunk_start = i_chunk * MAX_URLS
            chunk_end = min(chunk_start + MAX_URLS, n_urls)
            not_signed_urls_chunk = not_signed_urls[chunk_start:chunk_end]
            params: Dict[str, Any] = {"urls": not_signed_urls_chunk}
            if ENV.tld_url_duration:
                params["duration_seconds"] = ENV.tld_url_duration
            response = session.post(route=route.value, params=params)
            signed_url_batch = SignedURLBatch(**response.json())
            if not signed_url_batch:
                raise ValueError(
                    f"No signed url batch found in response: {response.json()}"
                )
            if not all(key in signed_url_batch.hrefs for key in not_signed_urls_chunk):
                raise ValueError(
                    f"URLs to sign are {not_signed_urls_chunk} but returned "
                    f"signed URLs"
                    f"are for {signed_url_batch.hrefs.keys()}"
                )
            for url, href in signed_url_batch.hrefs.items():
                signed_url = SignedURL(expiry=signed_url_batch.expiry, href=href)
                if route == SignURLRoute.SIGN_URLS_GET:
                    # Only put GET urls in cache
                    CACHE[url] = signed_url
                signed_urls[url] = signed_url
        log.debug(
            "Got signed urls %s in %s seconds",
            signed_urls,
            f"{time.time() - start_time:.2f}",
        )

    return signed_urls
