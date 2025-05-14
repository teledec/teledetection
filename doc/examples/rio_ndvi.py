"""NDVI loss example with pyotb."""

import pystac_client
import stackstac
from matplotlib import pyplot as plt

import teledetection

aoi_bounds = [3.944092, 43.526638, 4.014816, 43.568420]

# retrieving the relevant STAC Items
api = pystac_client.Client.open(
    "https://api.stac.teledetection.fr",
    modifier=teledetection.sign_inplace,
)

TIME_RANGE = "2016-04-10/2017-11-01"
search = api.search(
    collections=["sentinel2-l2a-theia"],
    datetime=TIME_RANGE,
    bbox=aoi_bounds,
    query={"sat:relative_orbit": {"eq": 8}, "eo:cloud_cover": {"lt": 50}},
    sortby="datetime",
    max_items=6,
)
items = search.item_collection()
print(f"{len(items)} items found")

time_steps_pc = len(items)

bands = ["B03", "B04", "B08", "CLM_R1"]
FILL_VALUE = 2**16 - 1
asset = items.items[0].assets["B03"]
proj_code = asset.ext.proj.code or ""
epsg = int(proj_code.replace("EPSG:", ""))
array = stackstac.stack(
    items,
    assets=bands,
    resolution=10,
    fill_value=1,
    bounds_latlon=aoi_bounds,
    epsg=epsg,
    chunksize=(time_steps_pc, 1, "auto", "auto"),
)
array.drop_duplicates("time")

CLM_R1 = array.sel(band="CLM_R1").squeeze().astype("uint8")
array = array.sel(band=~(array.band == "CLM_R1"))
array = array.assign_coords(CLM_R1=(("time", "y", "x"), CLM_R1.values))

source = array.sel(band=["B08", "B04", "B03"])

rgb = source.isel(time=range(6))
rgb.plot.imshow(col_wrap=3, col="time", rgb="band", vmax=2500, size=4)

nir, red = (
    source.sel(band="B08").astype("float"),
    source.sel(band="B04").astype("float"),
)
ndvi = (nir - red) / (nir + red)

ndvi.isel(time=range(6)).plot.imshow(col_wrap=3, col="time", size=4, cmap="RdYlGn")
plt.show()
