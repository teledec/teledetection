# Basic example

The following example does a Stac search and returns usable Stac objects (Stac assets URLs are signed).

```python
from pystac_client import Client
from teledetection import sign_inplace

api = Client.open(
    'https://stacapi.stac.teledetection.fr', 
    modifier=sign_inplace
)

res = api.search(
    bbox=[4, 42.99, 5, 44.05], 
    datetime=["2022-01-01", "2022-12-25"],
    collections=["spot-6-7-drs"]
)
items = search.item_collection()
print(f"{len(items)} items found")
item = items.items[0]
```

