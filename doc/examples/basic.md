# Basic example

The following example does a STAC search and returns usable Stac objects (Stac assets URLs are signed).

```python
from pystac_client import Client
from teledetection import sign_inplace

api = Client.open('https://api.stac.teledetection.fr', modifier=sign_inplace)
res = api.search(datetime="2022-01-01/2022-12-25", collections=["spot-6-7-drs"])
items = res.item_collection()  # List of items with signed assets HREFs
```

Note that you can also sign objects only when needed, for instance here 
after a simple STAC search:

```python
api = Client.open('https://api.stac.teledetection.fr')  # no modifier here!
res = api.search(...)  # same arguments as before
items = res.item_collection()  # Items assets HREFs are not signed yet
sign_inplace(items[0])  # Item 0 assets HREFs are now signed !
another_signed_item = sign(items[1])  # Another way to sign with copy
```

This should be the privileged way when you don't need to sign every single 
asset HREF of the STAC objects you are crawling, because the signing 
request will slow things down.

!!! Info

    `teledetection.sign_inplace()` can also be applied directly on a particular 
    `pystac.item`, `pystac.collection`, `pystac.asset` or any URL as `str`, 
    with the same outcome in term of expiry.

## Signed URLs expiry

The signed URLs for STAC objects assets are valid during 8 hours after 
`teledetection.sign_inplace` or `teledetection.sign` is called. You can 
change this duration changing the environment variable `TLD_URL_DURATION` 
(in seconds, up to 8 days).
