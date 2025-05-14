# Advanced use

## Sign after the search

```python
# See search described in previous sections
items = search.item_collection()
item = items.items[0]
item = teledetection.sign_inplace(item)
print(item.assets)
```

!!! Hint

    `item = teledetection.sign(item)` also works.


## Get headers

For the developer it can be convenient just to grab headers (whatever the 
authentication method is) to use them is various API endpoints.

```python
import teledetection as tld

headers = tld.get_headers()
requests.get(..., headers=headers)
```


## Under the hood

The principle is to retrieve the signed URLs and use them to open remote
rasters in QGIS.

### Retrieve the signed URL

The following code does a STAC search and displays the assets URLs:

```python
from pystac_client import Client
from teledetection import sign_inplace

api = Client.open(
    'https://api.stac.teledetection.fr', 
    modifier=sign_inplace
)
res = api.search(
    bbox=[4, 42.99, 5, 44.05], 
    datetime=["2022-01-01", "2022-12-25"],
    collections=["spot-6-7-drs"]
)
for item in res.items():
    print(f"Links for {item.id}:")
    print(item.assets['src_pan'].href)
```

Result has the following form: `https://minio-api-dinamis.apps.okd...?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Date=...&X-Amz-Expires=28800&X-Amz-SignedHeaders=host&X-Amz-Signature=...`

### Bonus: Open COG files in QGIS

To open one COG in QGIS, follow these steps:

- Copy one link
- In QGIS: *Layer* > *Add layer* > *Add raster layer*
- In *Source type*, select *Protocol: HTTP(S), cloud, etc*
- Paste the copied link in the *url* field

You can then process the remote COGs as any raster with your favorite tool 
from QGIS.

!!! Warning

    QGIS must be at least **3.18 (Firenze)** to open remote COG files

!!! Hint

    There is actually a simpler way to fetch our data using QGIS, check our [documentation](https://home-cdos.apps.okd.crocc.meso.umontpellier.fr/en/page/qgis/).



## Environment variables

- `TLD_TTL_MARGIN`: 
Every signed URL has a TTL, returned by the signing URL API (`expiry`).
To prevent the expiry of one signed URL during a long process, a margin of 
1800 seconds (30 minutes) is used by default. This duration can be changed 
setting this environment variable to a number of seconds. When one given 
URL has to be signed again, the cached URL will not be used when the 
previous TTL minus the margin is negative. 30 minutes should be enough 
for most processing, however feel free to increase this value to prevent 
your long process crashing, if it has started with one URL with a short TTL.

- `TLD_URL_DURATION`: 
Signed URLs have a default duration set by the signing API endpoint (in 
general, a few hours). You can change the duration up to 6 days setting 
this environment variable, in seconds.

- `TLD_DISABLE_AUTH`: 
Use this environment variable to disable authentication mechanism.

- `TLD_CONFIG_DIR`: 
The default config directory used to store authentication credentials (i.e. 
jwt tokens and API key) is located in the user config folder (In linux: 
`/home/user/.config/TLD_auth`). Set this environment variable to 
set a different directory.

- `TLD_ACCESS_KEY` and `TLD_SECRET_KEY` can be used to 
set your API key from the environment.

- `TLD_RETRY_TOTAL` and `TLD_RETRY_BACKOFF` can be set to 
control the retry strategy of requests to the signing API endpoint.

- `TLD_SIGNING_ENDPOINT`: use this to change the signing endpoint.
