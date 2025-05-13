## How to create a (very tiny) STAC catalog

In this sections we present how to create a very tiny STAC catalog from python with `pystac`.

### Code


First, we need to import `pystac` and `datetime` modules:

```python
import pystac
from datetime import datetime
```

We create a `pystac.Collection`. Note that we provide an undefined `extent` for now:

```python
col1 = pystac.Collection(
    id="collection-test1",
    extent=pystac.Extent(
        pystac.SpatialExtent(4 * [0]),
        pystac.TemporalExtent(intervals=[[None, None]]),
    ),
    description="Some collection for tests",
    title="Collection test 1",
)
```

You can take a look at the `pystac.Collection` class in the API reference [here](https://pystac.readthedocs.io/en/stable/api/collection.html#) (there is plenty of interesting stuff like `license`, `providers`, `keywords`, etc.).

Then we instantiate a `pystac.Item`. Members `datetime`, `id`, `bbox`, `properties` and `geometry` are required. We set 2 assets using the `assets` dict. In our example, both assets `media_type` are set to COG (Cloud Optimized-Geotiff), implying that the two files identified with `href` must be in COG format.

```python
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
```

We can then add `item1` to the `col1` collection:

```python
col1.add_item(item1)
```

Now we can update very conveniently the collection extents (both temporal and spatial) with the following:;

```python
col1.update_extent_from_items()
```

We can finally save our collection into a *.json* file:

```python
col1.normalize_hrefs("/tmp/collection-test1")
col1.save(pystac.CatalogType.ABSOLUTE_PUBLISHED)
```

And voila !

### Result

#### Generated files

```
/tmp/collection-test1/
├── collection.json
└── item_23102024
    └── item_23102024.json
```

#### collection.json

<details>
  <summary>Code</summary>

```json
{
  "type": "Collection",
  "id": "collection-test1",
  "stac_version": "1.1.0",
  "description": "Some collection for tests",
  "links": [
    {
      "rel": "root",
      "href": "/tmp/collection-test1/collection.json",
      "type": "application/json",
      "title": "Collection test 1"
    },
    {
      "rel": "item",
      "href": "/tmp/collection-test1/item_23102024/item_23102024.json",
      "type": "application/geo+json"
    },
    {
      "rel": "self",
      "href": "/tmp/collection-test1/collection.json",
      "type": "application/json"
    }
  ],
  "title": "Collection test 1",
  "extent": {
    "spatial": {
      "bbox": [
        [
          2.49,
          46.59,
          3.26,
          47.14
        ]
      ]
    },
    "temporal": {
      "interval": [
        [
          "2024-10-23T00:00:00Z",
          "2024-10-23T00:00:00Z"
        ]
      ]
    }
  },
  "license": "other"
}
```

</details>

#### item_23102024.json

<details>
  <summary>Code</summary>

```json
{
  "type": "Feature",
  "stac_version": "1.1.0",
  "stac_extensions": [],
  "id": "item_23102024",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [
          2.49,
          47.14
        ],
        [
          3.26,
          47.13
        ],
        [
          3.25,
          46.59
        ],
        [
          2.49,
          46.59
        ],
        [
          2.49,
          47.14
        ]
      ]
    ]
  },
  "bbox": [
    2.49,
    46.59,
    3.26,
    47.14
  ],
  "properties": {
    "datetime": "2024-10-23T00:00:00Z"
  },
  "links": [
    {
      "rel": "root",
      "href": "/tmp/collection-test1/collection.json",
      "type": "application/json",
      "title": "Collection test 1"
    },
    {
      "rel": "collection",
      "href": "/tmp/collection-test1/collection.json",
      "type": "application/json",
      "title": "Collection test 1"
    },
    {
      "rel": "parent",
      "href": "/tmp/collection-test1/collection.json",
      "type": "application/json",
      "title": "Collection test 1"
    },
    {
      "rel": "self",
      "href": "/tmp/collection-test1/item_23102024/item_23102024.json",
      "type": "application/json"
    }
  ],
  "assets": {
    "estim": {
      "href": "/tmp/estim.tif",
      "type": "image/tiff; application=geotiff; profile=cloud-optimized"
    },
    "conf": {
      "href": "/tmp/conf.tif",
      "type": "image/tiff; application=geotiff; profile=cloud-optimized"
    }
  },
  "collection": "collection-test1"
}

```
</details>

## See also

- [This tutorial](https://pystac.readthedocs.io/en/stable/tutorials/how-to-create-stac-catalogs.html) explains extensively how to create a STAC collection from local raster files,
- `pystac` [tutorials](https://pystac.readthedocs.io/en/stable/tutorials.html),
- the [test file](https://forgemia.inra.fr/cdos-pub/teledetection/-/blob/main/tests/all.py) 
of `teledetection`.
