# Advanced use

## Sign inplace

```python
items = search.item_collection()
item = items.items[0]
teledetection.sign_inplace(item)
print(item.assets)
```

## Sign with copy

```python
items = search.item_collection()
item = items.items[0]
signed_item = teledetection.sign(item)
print(signed_item.assets)
```

## Get headers

For the developer it can be convenient just to grab headers (whatever the 
authentication method is) to use them is various API endpoints.

```python
import teledetection as tld

headers = tld.get_headers()
requests.get(..., headers=headers)
```

## QGIS

QGIS has a STAC browser plugin that can be used to access the MTD geospatial 
data center.

Follow these steps:

1. Generate an API key using `tld` in command line interface: `tld apikey create "my key for QGIS"`, or [from your browser](https://gate.stac.teledetection.fr),
2. Open QGIS,
3. First step in QGIS is to set the API key in the QGIS authentication framework. 
Go to `Preferences` > `Options` and select `Authentication` tab on the left panel.
Note that you might need to set a general password for QGIS authentication framework, in case it's not already done.
4. Click on `+`, on the top-right of the panel, select API header, set a name (e.g. *CDS MTD Auth*) and optionally a description.
5. Use the `+` button on the top-right side of the table, to add the following keys/values:

    - key: access-key, *enter the access key generated in (1)*
    - key: secret-key, *enter the secret key generated in (1)*

6. Now the next step in QGIS consist in installing the STAC plugin and add the MTD STAC endpoint. Click on *Extensions* > *Install/manage* and search and install the **STAC API Browser** plugin.
7. Start the plugin, from the **STAC API Browser** shortcut icon (also available from *Internet* > *STAC API Browser*),
8. In the *Connections* tab, click on *new*, then add the following:

    - name: `CDS MTD` or anything you want
    - url: `https://qgis.stac.teledetection.fr`
    - authentifaction: select the authentication method you named in the QGIS authentication framework in step (4), e.g. *CDS MTD Auth*

9. You can now select the STAC provider in the list and use it !

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
