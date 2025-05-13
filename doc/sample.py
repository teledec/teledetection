"""An example showing how to create a tiny STAC collection with an item."""

from datetime import datetime
import pystac


# Create a collection
col1 = pystac.Collection(
    id="collection-test1",
    extent=pystac.Extent(
        pystac.SpatialExtent(4 * [0]),
        pystac.TemporalExtent(intervals=[[None, None]]),
    ),
    description="Some collection for tests",
    title="Collection test 1",
)

# Create an item
item1 = pystac.Item(
    id="item_23102024",
    datetime=datetime(year=2024, month=10, day=23),
    bbox=[2.49, 46.59, 3.26, 47.14],
    geometry={
        "type": "Polygon",
        "coordinates": [
            [[2.49, 47.14], [3.26, 47.13], [3.25, 46.59], [2.49, 46.59], [2.49, 47.14]]
        ],
    },
    assets={
        "estim": pystac.Asset(href="/tmp/estim.tif", media_type=pystac.MediaType.COG),
        "conf": pystac.Asset(href="/tmp/conf.tif", media_type=pystac.MediaType.COG),
    },
    properties={},
)

# Append item1 to collection
col1.add_item(item1)

# Update the collection spatial/temporal extent
col1.update_extent_from_items()

# Save the collection
col1.normalize_hrefs("/tmp/collection-test1")
col1.save(pystac.CatalogType.ABSOLUTE_PUBLISHED)
