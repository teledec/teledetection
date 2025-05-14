"""NDVI loss example with pyotb."""

from pystac_client import Client
import pyotb  # type: ignore
from teledetection import sign_inplace

api = Client.open(
    "https://api.stac.teledetection.fr",
    modifier=sign_inplace,
)


def mosa(year):
    """Return a pyotb application that perform a mosaic."""
    res = api.search(
        bbox=[4, 42.99, 5, 44.05],
        datetime=[f"{year}-01-01", f"{year}-12-25"],
        collections=["spot-6-7-drs"],
    )
    urls = [f"/vsicurl/{r.assets['src_xs'].href}" for r in res.items()]
    return pyotb.Mosaic({"il": urls})


def ndvi(xs):
    """Return a pyotb application that computes NDVI."""
    return pyotb.BandMath({"il": [xs], "exp": "(im1b4-im1b1)/(im1b4+im1b1)"})


ndvi_22 = ndvi(mosa("2022"))
ndvi_21 = ndvi(mosa("2021"))
delta_ndvi = ndvi_22 - pyotb.Superimpose({"inr": ndvi_22, "inm": ndvi_21})
delta_ndvi.write("ndvi_loss.tif?&box=5000:5000:4096:4096")
