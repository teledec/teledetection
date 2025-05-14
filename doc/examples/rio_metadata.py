"""Metadata extraction example with rasterio."""

from pystac_client import Client
import rasterio.features  # type: ignore
import rasterio.warp  # type: ignore
from teledetection import sign_inplace

api = Client.open(
    "https://api.stac.teledetection.fr",
    modifier=sign_inplace,
)

YEAR = 2022
bbox = [4, 42.99, 5, 44.05]
res = api.search(bbox=bbox, datetime=[f"{YEAR}-01-01", f"{YEAR}-12-25"])

for item in res.items():
    url = item.assets["src_xs"].href
    with rasterio.open(url) as dataset:
        # Read the dataset's valid data mask as a ndarray.
        mask = dataset.dataset_mask()

        # Extract feature shapes and values from the array.
        for geom, val in rasterio.features.shapes(mask, transform=dataset.transform):
            # Transform shapes from the dataset's own coordinate
            # reference system to CRS84 (EPSG:4326).
            geom = rasterio.warp.transform_geom(
                dataset.crs, "EPSG:4326", geom, precision=6
            )

            # Print GeoJSON shapes to stdout.
            print(geom)
