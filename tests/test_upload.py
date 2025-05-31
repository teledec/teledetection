"""Test file."""

import os
import glob
import shutil
import tempfile
import urllib.request
from datetime import datetime

import pystac
import pystac_client
import pytest
import requests

from utils import run_cli_cmd


from teledetection import sign, sign_inplace
from teledetection.upload import raster, stac, diff, transfer
from teledetection.cli import (
    collection_diff,
    grab,
    list_col_items,
    list_cols,
    publish,
    DEFAULT_S3_EP,
)
from teledetection.sdk.logger import get_logger_for


log = get_logger_for(__name__)

STAC_ENDPOINT = "https://api-dev.stac.teledetection.fr"
DEFAULT_COL_HREF = "http://hello.fr/collections/collection-for-tests"
IMAGE_HREF = (
    "https://gitlab.orfeo-toolbox.org/orfeotoolbox/"
    "otb/-/raw/develop/Data/Input/Capitole_Rasterization.tif"
)
COL_ID = "test-collection-for-upload"
items_ids = ["item_1", "item_2"]
RASTER_FILE1 = "/tmp/raster1.tif"
RASTER_FILE2 = "/tmp/folder1/raster2.tif"
RASTER_FILE3 = "/tmp/folder/raster3.tif"
STORAGE_BUCKET = "sm1-gdc-tests"

handler = stac.StacUploadTransactionsHandler(
    stac_endpoint=STAC_ENDPOINT,
    storage_endpoint=DEFAULT_S3_EP,
    storage_bucket=STORAGE_BUCKET,
    assets_overwrite=True,
    sign=False,
)

with open(RASTER_FILE1, "wb") as f:
    r = requests.get(IMAGE_HREF, timeout=5)
    f.write(r.content)
os.makedirs(os.path.dirname(RASTER_FILE2), exist_ok=True)
shutil.copyfile(RASTER_FILE1, RASTER_FILE2)
os.makedirs(os.path.dirname(RASTER_FILE3), exist_ok=True)
shutil.copyfile(RASTER_FILE1, RASTER_FILE3)

COL_BBOX = [0.0, 0.0, 0.0, 0.0]
BBOX_ALL = [
    3.6962018175925073,
    43.547450099338604,
    9.036414917971516,
    48.75431706444037,
]
COORDS1 = [
    [4.032730583418401, 43.547450099338604],
    [4.036414917971517, 43.75162726634343],
    [3.698685718905037, 43.75431706444037],
    [3.6962018175925073, 43.55012996681564],
    [4.032730583418401, 43.547450099338604],
]
COORDS2 = [[coord + 5 for coord in coords] for coords in COORDS1]


def clear():
    """Clear all test items and collection."""
    for item_id in items_ids:
        handler.delete_item_or_col(col_id=COL_ID, item_id=item_id)
    handler.delete_item_or_col(col_id=COL_ID)


def remote_col_test(expected_bbox):
    """Run tests on a remote collection."""
    api = pystac_client.Client.open(STAC_ENDPOINT)
    col = api.get_collection(COL_ID)
    extent = col.extent.spatial.bboxes
    assert len(extent) == 1
    assert tuple(extent[0]) == tuple(expected_bbox), (
        f"expected BBOX: {expected_bbox}, got {extent[0]}"
    )

    # Check that assets are accessible once signed
    for i in col.get_items():
        for asset_key, asset in i.get_assets().items():
            assert stac.asset_exists(asset.href)
            assert "?" not in asset.href, f"The asset URL looks signed: {asset.href}"
            assert asset.media_type == pystac.MediaType.COG, (
                f"wrong media_type for asset {i.id} [{asset_key}]"
            )
            sign_inplace(asset)
            urllib.request.urlretrieve(asset.href, "/tmp/a.tif")
            assert raster.is_cog("/tmp/a.tif")


def create_item(item_id: str):
    """Create a STAC item."""
    coordinates = COORDS1 if item_id == "item_1" else COORDS2

    # Check is COG
    assert not raster.is_cog(RASTER_FILE1)
    assert not raster.is_cog(RASTER_FILE2)
    assert not raster.is_cog(RASTER_FILE3)

    item = pystac.Item(
        id=item_id,
        geometry={
            "type": "Polygon",
            "coordinates": [coordinates],
        },
        bbox=[
            min(coords[0] for coords in coordinates),
            min(coords[1] for coords in coordinates),
            max(coords[0] for coords in coordinates),
            max(coords[1] for coords in coordinates),
        ],
        datetime=datetime.now().replace(year=1999),
        properties={},
        assets={
            "ndvi": pystac.Asset(href=RASTER_FILE1),
            "crswir": pystac.Asset(href=RASTER_FILE2),
            "ndwi": pystac.Asset(href=RASTER_FILE3),
        },
    )

    return item


def create_collection(col_href: str):
    """Create an empty STAC collection."""
    spat_extent = pystac.SpatialExtent([COL_BBOX])
    temp_extent = pystac.TemporalExtent(intervals=[[None, None]])  # type: ignore
    col = pystac.Collection(
        id=COL_ID,
        extent=pystac.Extent(spat_extent, temp_extent),
        description="Some description",
        title="Dummy collection for teledetection-upload tests",
        href=col_href,
        providers=[
            pystac.Provider("INRAE"),
        ],
    )
    return col


def create_items_and_collection(relative, items=None, col_href=DEFAULT_COL_HREF):
    """Create two STAC items attached to one collection."""
    # Create items
    items = items or [create_item(item_id=item_id) for item_id in items_ids]

    # Attach items to collection
    col = create_collection(col_href)
    for item in items:
        col.add_item(item)
    if relative:
        col.make_all_asset_hrefs_relative()
    else:
        col.make_all_asset_hrefs_absolute()

    return col, items


def generate_collection(root_dir, relative=True, items=None):
    """Generate and save a STAC collection in {root_dir}/collection.json."""
    col, _ = create_items_and_collection(relative, items=items)
    col.normalize_hrefs(root_dir)
    col.save(
        catalog_type=pystac.CatalogType.RELATIVE_PUBLISHED
        if relative
        else pystac.CatalogType.ABSOLUTE_PUBLISHED
    )


def generate_item_collection(file_pth, relative=True):
    """Generate and save a STAC item_collection in {file_pth}."""
    _, items = create_items_and_collection(relative)
    icol = pystac.item_collection.ItemCollection(items=items)
    icol.save_object(file_pth)


def test_push():
    """Push a file remotely."""
    local_file = "/tmp/toto.txt"

    with open(local_file, "w", encoding="utf-8") as file_handle:
        file_handle.write("hello world")

    target_url = "https://s3-data.meso.umontpellier.fr/sm1-gdc-tests/titi.txt"

    transfer.push(local_filename=local_file, target_url=target_url)
    log.info("push OK")

    signed_url = sign(target_url)
    log.info("sign OK")

    res = requests.get(signed_url, stream=True, timeout=10)
    assert res.status_code == 200, "Get NOK"
    log.info("get OK")

    log.info("Done")


@pytest.mark.parametrize("overwrite", [["-o"], []])
@pytest.mark.parametrize("keep_cog_dir", [True, False])
def test_publish_w_cli(overwrite: list, keep_cog_dir: bool):
    """Handle the STAC object with CLI."""
    log.info("Testing CLI with ovr=%s and keep_cog_dir=%s", overwrite, keep_cog_dir)
    cog_dir = "/tmp/cog"
    with tempfile.TemporaryDirectory() as tmpdir:
        generate_collection(tmpdir)
        run_cli_cmd(
            publish,
            [
                os.path.join(tmpdir, "collection.json"),
                "--stac_endpoint",
                STAC_ENDPOINT,
                "--storage_endpoint",
                DEFAULT_S3_EP,
                "-b",
                STORAGE_BUCKET,
            ]
            + overwrite
            + (["--keep_cog_dir", cog_dir] if keep_cog_dir else []),
        )
        if keep_cog_dir and overwrite:
            files = glob.glob(f"{cog_dir}/*.tif")
            assert files
            shutil.rmtree(cog_dir)
        remote_col_test(BBOX_ALL)
        clear()


@pytest.mark.parametrize("assets_overwrite", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_item_collection(assets_overwrite, relative):
    """Test item collection."""
    handler.assets_overwrite = assets_overwrite
    # we need to create an empty collection before
    col = create_collection(DEFAULT_COL_HREF)
    handler.publish_collection(col)

    with tempfile.NamedTemporaryFile() as tmp:
        generate_item_collection(tmp.name, relative=relative)
        handler.load_and_publish(tmp.name)
        remote_col_test(BBOX_ALL)
        clear()


@pytest.mark.parametrize("assets_overwrite", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_collection(assets_overwrite, relative):
    """Test collection."""
    handler.assets_overwrite = assets_overwrite
    with tempfile.TemporaryDirectory() as tmpdir:
        generate_collection(tmpdir, relative=relative)
        col_pth = os.path.join(tmpdir, "collection.json")
        handler.load_and_publish(col_pth)
        remote_col_test(BBOX_ALL)
        clear()


@pytest.mark.parametrize("assets_overwrite", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_collection_multipart(assets_overwrite, relative):
    """Test collection."""
    log.info(f"\nRelative: {relative}")
    handler.assets_overwrite = assets_overwrite
    for item_id in items_ids:
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_collection(tmpdir, relative=relative, items=[create_item(item_id)])
            col_pth = os.path.join(tmpdir, "collection.json")
            handler.load_and_publish(col_pth)
    remote_col_test(BBOX_ALL)
    clear()


def test_get():
    """Test get collections, items, etc."""

    for col in handler.client.get_collections():
        col_from_handler = handler.client.get_collection(col.id)
        assert col_from_handler
        assert isinstance(col_from_handler, pystac.Collection)
        items = handler.get_items(col_id=col.id, max_items=1)  # test get_items()
        assert isinstance(items, list)
        for item in items:
            item_from_handler = handler.get_item(
                col_id=col.id, item_id=item.id
            )  # test get_item()
            assert item_from_handler
            assert isinstance(item_from_handler, pystac.Item)


def test_diff():
    """Test diff."""

    col1, items = create_items_and_collection(
        relative=True, col_href="/tmp/collection.json"
    )
    col2 = col1.full_copy()

    item = items[0].full_copy()
    item.id += "_test"
    col2.add_item(item, item.id)

    item = items[0].full_copy()
    item.id += "_test_other"
    col1.add_item(item, item.id)

    diff.generate_items_diff(col1, col2)
    diff.collections_defs_are_different(col1, col2)

    col1_filepath = "/tmp/col1.json"
    col1.set_self_href(col1_filepath)
    col1.save(catalog_type=pystac.CatalogType.RELATIVE_PUBLISHED)

    diff.compare_local_and_upstream(
        stac.StacTransactionsHandler(stac.DEFAULT_STAC_EP, sign=False),
        col1_filepath,
        "costarica-sentinel-2-l3-seasonal-spectral-indices-M",
    )


def test_cli_list_cols():
    """Test list cols."""
    run_cli_cmd(list_cols)
    run_cli_cmd(list_col_items, ["--col_id", "spot-6-7-drs"])


def test_cli_grab():
    """Test CLI grab."""
    run_cli_cmd(grab, ["--col_id", "spot-6-7-drs", "--out_json", "/tmp/col.json"])
    run_cli_cmd(
        grab, ["--col_id", "spot-6-7-drs", "--out_json", "/tmp/col.json", "--pretty"]
    )
    run_cli_cmd(
        grab,
        [
            "--col_id",
            "spot-6-7-drs",
            "--item_id",
            "SPOT7_MS_201805051026429_SPOT7_P_201805051026429_1",
            "--out_json",
            "/tmp/item.json",
        ],
    )
    run_cli_cmd(
        grab,
        [
            "--col_id",
            "spot-6-7-drs",
            "--item_id",
            "SPOT7_MS_201805051026429_SPOT7_P_201805051026429_1",
            "--out_json",
            "/tmp/item.json",
            "--pretty",
        ],
    )


def test_cli_diff():
    """Test diff."""
    run_cli_cmd(
        collection_diff, ["--remote_id", "spot-6-7-drs", "--col_path", "/tmp/col.json"]
    )
