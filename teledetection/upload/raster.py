"""Raster analysis and parsing module."""

import os
from datetime import datetime
from rasterio import warp, features, open as ropen, crs, errors  # type:ignore
from rio_stac.stac import bbox_to_geom, get_projection_info  # type:ignore
import numpy
import rasterio
from rio_cogeo import cog_translate, cog_validate
from pystac.asset import Asset
from pystac.item import Item
from pystac.extensions.projection import AssetProjectionExtension
from pystac.extensions.raster import RasterBand, RasterExtension, Statistics
from pystac.extensions.timestamps import ItemTimestampsExtension
from pystac.errors import ExtensionNotImplemented

from teledetection.sdk.logger import get_logger_for

logger = get_logger_for(__name__)

EPSG_4326 = crs.CRS.from_epsg(4326)  # pylint: disable=c-extension-no-member


class NoSpatialLayerException(Exception):
    """No spatial layer exception."""


class ScalesInputFormatException(Exception):
    """No spatial layer exception."""


class OffsetsInputFormatException(Exception):
    """No spatial layer exception."""


class Info:
    """Grabs raster information."""

    def __init__(self, raster_file):
        """Init Info class.

        Args:
            raster_file: str

        Returns:
            Info class

        """
        self.raster_file = raster_file
        with ropen(self.raster_file) as src:
            bbox = src.bounds
            geom = bbox_to_geom(bbox)
            # Reproject the geometry to "epsg:4326"
            geom = warp.transform_geom(src.crs, EPSG_4326, geom)
            self.bbox = features.bounds(geom)
            self.geom = bbox_to_geom(self.bbox)
            self.meta = src.meta
            self.gsd = src.res[0]
            self.proj_ext_info = get_projection_info(src)
            self.nodata = src.nodata
            self.area_or_point = src.tags().get("AREA_OR_POINT", "").lower()
            self.bands = src.indexes
        self.stats = None

    def band_info(self, band: int):
        """Get band info.

        Args:
            band: band index

        Returns:
            band metadata and band statistics

        """
        if band <= 0:
            raise ValueError('The "band" parameter value starts at 1')

        with ropen(self.raster_file) as src_dst:
            md = {
                "data_type": src_dst.dtypes[band - 1],
                "scale": src_dst.scales[band - 1],
                "offset": src_dst.offsets[band - 1],
            }
            if self.area_or_point:
                md["sampling"] = self.area_or_point

            # If the Nodata is not set we don't forward it.
            if src_dst.nodata is not None:
                if numpy.isnan(src_dst.nodata):
                    md["nodata"] = "nan"
                elif numpy.isposinf(src_dst.nodata):
                    md["nodata"] = "inf"
                elif numpy.isneginf(src_dst.nodata):
                    md["nodata"] = "-inf"
                else:
                    md["nodata"] = src_dst.nodata

            if src_dst.units[band - 1] is not None:
                md["unit"] = src_dst.units[band - 1]

            stats = {}
            try:
                if not self.stats:
                    self.stats = src_dst.stats(approx=True)
                statistics = self.stats[band - 1]
                stats.update(
                    {
                        "mean": statistics.mean,
                        "minimum": statistics.min,
                        "maximum": statistics.max,
                        "stddev": statistics.std,
                    }
                )
            except rasterio.errors.StatisticsError as e:
                logger.warning("Unable to compute relevant statistics: %s", e)

            return md, stats


def raster2cog(
    src_raster: str,
    dst_raster: str,
):
    """Convert a raster to Cloud Optimized Geotiff.

    Args:
        src_raster: source raster file path
        dst_raster: destination raster file path
    """
    profile = {
        "driver": "GTiff",
        "interleave": "pixel",
        "tiled": True,
        "blockxsize": 512,
        "blockysize": 512,
        "compress": "DEFLATE",
        "BIGTIFF": "IF_SAFER",
    }

    config = {
        "GDAL_NUM_THREADS": os.environ.get("GDAL_NUM_THREADS") or "ALL_CPUS",
        "GDAL_TIFF_INTERNAL_MASK": True,
        "GDAL_TIFF_OVR_BLOCKSIZE": "512",
    }

    # Change output COG filename extension if not .tif
    if not dst_raster.lower().endswith(".tif"):
        pre, _ = os.path.splitext(dst_raster)
        dst_raster = f"{pre}.tif"

    cog_translate(
        source=src_raster,
        dst_path=dst_raster,
        dst_kwargs=profile,
        config=config,
        web_optimized=False,
        progress_out=None,
        in_memory=False,
        allow_intermediate_compression=True,
    )


def is_cog(src_raster: str) -> bool:
    """Check if the raster is in COG format.

    Args:
        src_raster: source raster file path

    Returns:
        True if the raster is a COG, else False
    """
    is_valid, _, _ = cog_validate(src_raster, quiet=True, strict=True)
    return is_valid


def is_raster(src_filepath: str) -> bool:
    """Check if the file is a raster.

    Args:
        src_filepath: input file path

    Returns:
        True if the provided file is a raster
    """
    try:
        Info(src_filepath)
        return True
    except (errors.RasterioIOError, errors.CRSError):
        pass
    return False


def convert_to_cog(
    local_filename: str,
    keep_cog_dir: str = "",
) -> str:
    """Convert raster to COG in a tmp directory.

    Args:
        local_filename: input file path
        keep_cog_dir: path to the directory to keep COG files (not used when "")

    Returns:
        file path of the converted raster
    """
    if keep_cog_dir:
        tmpcog = os.path.join(keep_cog_dir, os.path.basename(local_filename))
        if not os.path.exists(keep_cog_dir):
            os.makedirs(keep_cog_dir)
    else:
        tmpcog = os.path.join(
            os.path.dirname(local_filename), "TMPCOG", os.path.basename(local_filename)
        )
        if not os.path.exists(os.path.dirname(tmpcog)):
            os.makedirs(os.path.dirname(tmpcog))
    if os.path.exists(tmpcog) and keep_cog_dir:
        return tmpcog
    raster2cog(local_filename, tmpcog)
    return tmpcog


def apply_proj_extension(asset: Asset):
    """Apply projection extension.

    Args:
        asset: cog raster asset

    Returns:
        None
    """
    # Projection
    proj_ext = AssetProjectionExtension.ext(asset, add_if_missing=True)
    try:
        info = Info(raster_file=asset.href)
    except NoSpatialLayerException:
        logger.warning("Failed to retrieve spatial info for %s", asset.href)
    proj_ext_args = info.proj_ext_info
    logger.debug("Projection extension args: %s", proj_ext_args)
    if proj_ext_args is not None:
        logger.debug("Applying projection extension")
        proj_ext.apply(**proj_ext_args)


def get_args_for_raster_ext(asset_path: str):
    """This function returns the arguments, as a dict, for the raster extension.

    Args:
        asset_path: asset path

    Returns:
        Dict of arguments for the `RasterExtension.ext(...).apply()`
        function.
    """
    try:
        raster_info = Info(asset_path)
        bands = []
        for band in raster_info.bands:
            md, stats = raster_info.band_info(band=band)

            raster_stats = Statistics.create(**stats)
            bands.append(RasterBand.create(statistics=raster_stats, **md))
        return {"bands": bands}
    except (rasterio.errors.RasterioIOError, rasterio.errors.CRSError) as err:
        logger.warning(
            "Failed to retrieve raster information for %s (%s). "
            "Maybe it is expected because the file is not a raster.",
            err,
            asset_path,
        )
    return None


def _merge_raster_bands(b1: RasterBand, b2: RasterBand) -> RasterBand:
    """Merge two RasterBand instances.

    Args:
        b1: band 1
        b2: band 2

    Returns:
        Merged RasterBand instance
    """
    args = {}
    for band in [b1, b2]:
        for argn in band.to_dict().keys():
            args[argn] = getattr(band, argn)
    return RasterBand.create(**args)


def apply_raster_extension(asset: Asset):
    """Apply raster extension.

    Args:
        asset: cog raster asset

    Returns:
        None
    """
    # Raster
    # For the raster extension, we merge RasterBand arguments from
    # (1) what is implemented in the `task`, and (2) stacflow built-in
    # properties (stats, nodata, etc)
    raster_ext_args = get_args_for_raster_ext(asset.href)
    logger.debug("Built-in raster extension args: %s", raster_ext_args)
    if raster_ext_args is not None:
        logger.debug("Applying raster extension")
        try:
            raster_ext = RasterExtension.ext(asset)
            if raster_ext.bands:
                builtin_bands = raster_ext_args["bands"]

                # When a raster extension has already been applied to
                # the asset, we want to keep the information that is
                # already there.
                logger.debug(
                    "Found an existing raster extension for this asset. Merging %s and %s",
                    [band.to_dict() for band in builtin_bands],
                    [band.to_dict() for band in raster_ext.bands],
                )
                raster_ext_args = {
                    "bands": [
                        _merge_raster_bands(b1, b2)
                        for b1, b2 in zip(
                            builtin_bands,  # built-in
                            raster_ext.bands,  # in `task`
                        )
                    ]
                }
                logger.debug("Result: %s", raster_ext_args)
            else:
                logger.debug("No raster extension properties for asset")
        except ExtensionNotImplemented:
            logger.debug("No existing raster extension found. Creating.")
            raster_ext = RasterExtension.ext(asset, add_if_missing=True)

        raster_ext.apply(**raster_ext_args)


def apply_published_extension(item: Item):
    """Apply published date extension.

    Args:
        asset: cog raster asset

    Returns:
        None
    """
    # Timestamps
    logger.debug("Apply timestamp extension for published date")
    ts_ext = ItemTimestampsExtension.ext(item, add_if_missing=True)
    ts_ext.apply(published=datetime.now())
