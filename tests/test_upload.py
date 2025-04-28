"""Test file."""

import os
import shutil
import tempfile
import urllib.request
from datetime import datetime

import pystac
import pystac_client
import pytest
import requests
import utils  # type: ignore

from teledetection import cli, sign_inplace
from teledetection.upload import raster, stac

utils.set_test_stac_ep()

DEFAULT_COL_HREF = "http://hello.fr/collections/collection-for-tests"
IMAGE_HREF = (
    "https://gitlab.orfeo-toolbox.org/orfeotoolbox/"
    "otb/-/raw/develop/Data/Input/Capitole_Rasterization.tif"
)
COL_ID = "collection-for-theia-dumper-tests"
items_ids = ["item_1", "item_2"]
RASTER_FILE1 = "/tmp/raster1.tif"
RASTER_FILE2 = "/tmp/folder1/raster2.tif"
RASTER_FILE3 = "/tmp/folder/raster3.tif"

handler = stac.StacUploadTransactionsHandler(
    stac_endpoint=utils.STAC_EP_DEV,
    storage_endpoint=cli.DEFAULT_S3_EP,
    storage_bucket="sm1-gdc-tests",
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
    api = pystac_client.Client.open(cli.DEFAULT_STAC_EP)
    col = api.get_collection(COL_ID)
    extent = col.extent.spatial.bboxes
    assert len(extent) == 1
    assert tuple(extent[0]) == tuple(expected_bbox), (
        f"expected BBOX: {expected_bbox}, got {extent[0]}"
    )

    # Check that assets are accessible once signed
    for i in col.get_items():
        assets = i.get_assets().values()
        for asset in assets:
            assert stac.asset_exists(asset.href)
            assert "?" not in asset.href, f"The asset URL looks signed: {asset.href}"
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
        title="Dummy collection for Theia-Dumper tests",
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


@pytest.mark.parametrize("assets_overwrite", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_item_collection(assets_overwrite, relative):
    """Test item collection."""

    handler.assets_overwrite = assets_overwrite
    # we need to create an empty collection before
    col = create_collection(DEFAULT_COL_HREF)
    handler.publish_collection(col=col)

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
        handler.load_and_publish(os.path.join(tmpdir, "collection.json"))
        remote_col_test(BBOX_ALL)
        clear()


@pytest.mark.parametrize("assets_overwrite", [False, True])
@pytest.mark.parametrize("relative", [False, True])
def test_collection_multipart(assets_overwrite, relative):
    """Test collection."""
    print(f"\nRelative: {relative}")
    handler.assets_overwrite = assets_overwrite
    for item_id in items_ids:
        with tempfile.TemporaryDirectory() as tmpdir:
            generate_collection(tmpdir, relative=relative, items=[create_item(item_id)])
            handler.load_and_publish(os.path.join(tmpdir, "collection.json"))
    remote_col_test(BBOX_ALL)
    clear()


def _test_all():
    for relative in [False, True]:
        for assets_overwrite in [False, True]:
            handler.assets_overwrite = assets_overwrite

            test_collection(assets_overwrite, relative)
            test_item_collection(assets_overwrite, relative)
            test_collection_multipart(assets_overwrite, relative)


if __name__ == "__main__":
    _test_all()
