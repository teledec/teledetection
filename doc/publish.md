# Upload the collection

First make sure necessary requirements are installed before uploading:

```bash
pip install teledetection[upload]
```

## Command line interface (CLI)

In the `teledetection` CLI, the `--storage_bucket` argument concatenates the actual bucket and the path prefix.

For instance if Jacques wants to upload a collection in `sm1-gdc/some-path`, he will have to call:

```commandLine
teledetection publish collection.json --storage_bucket sm1-gdc/some-path
```

In case he has an item, or an item collection, he can use the same command:

```commandLine
teledetection publish item.json --storage_bucket sm1-gdc/some-path
```
```commandLine
teledetection publish item-collection.json --storage_bucket sm1-gdc/some-path
```

For more details, see [this page](cli-ref.md).


## Python

Another way is to use the python API:

```python
from teledetection.stac import TransactionsHandler

handler = TransactionsHandler(
    stac_endpoint="https://api.stac.teledetection.fr",
    storage_endpoint="https://s3-data.meso.umontpellier.fr",
    storage_bucket="sm1-gdc/some-path",
    assets_overwrite=True
)
handler.load_and_publish("/tmp/collection.json")
```
