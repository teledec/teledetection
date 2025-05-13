# With rasterio

## Metadata fetching

[Source code :fontawesome-brands-github:](https://github.com/teledec/teledetection/blob/main/doc/examples/rio_metadata.py){ .md-button }

We start by importing RasterIO:

```python
import rasterio.features
import rasterio.warp
```

Like the precedent examples, we perform a STAC search over the camargue area 
during year 2022:

```python
year = 2022
bbox = [4, 42.99, 5, 44.05]
res = api.search(bbox=bbox, datetime=[f'{year}-01-01', f'{year}-12-25'])
```

We then loop over the STAC search results and fetch the metadata:

```python
for item in res.items():
    url =  item.assets["src_xs"].href
    with rasterio.open(url) as dataset:

        # Read the dataset's valid data mask as a ndarray.
        mask = dataset.dataset_mask()

        # Extract feature shapes and values from the array.
        for geom, val in rasterio.features.shapes(
                mask, transform=dataset.transform
        ):

            # Transform shapes from the dataset's own coordinate
            # reference system to CRS84 (EPSG:4326).
            geom = rasterio.warp.transform_geom(
                dataset.crs, 'EPSG:4326', geom, precision=6
            )

            # Print GeoJSON shapes to stdout.
            print(geom)
```

Which gives us:

```commandline
{'type': 'Polygon', 'coordinates': [[[3.605665, 44.238903], [3.59992, 
    43.695427], [4.323908, 43.689027], [4.336583, 44.23244], [3.605665, 
    44.238903]]]}
{'type': 'Polygon', 'coordinates': [[[3.608484, 43.752071], [3.603541, 
    43.283354], [4.321619, 43.276958], [4.332442, 43.74562], [3.608484, 
    43.752071]]]}
{'type': 'Polygon', 'coordinates': [[[4.931147, 43.761708], [4.912681, 
    43.209428], [5.64274, 43.194017], [5.668244, 43.746143], [4.931147, 
    43.761708]]]}
{'type': 'Polygon', 'coordinates': [[[4.26721, 44.244389], [4.255021, 
    43.693245], [4.984805, 43.682379], [5.004077, 44.233414], [4.26721, 
    44.244389]]]}
```

!!! Note

    As you have noticed, RasterIO transforms the input URLs, there is no need 
    to append the */vsicurl/* prefix.

## NDVI calculation

The following example shows how to fetch L2A in France, and generate a NDVI from it.

[Source code :fontawesome-brands-github:](https://github.com/teledec/teledetection/blob/main/doc/examples/rio_ndvi.py){ .md-button }

