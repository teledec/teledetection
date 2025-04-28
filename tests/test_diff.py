"""Test file."""

import pystac
import test_upload  # type: ignore
import utils  # type: ignore

from teledetection.upload import diff, stac

utils.set_test_stac_ep()


def test_diff():
    """Test diff."""

    col1, items = test_upload.create_items_and_collection(
        relative=True, col_href="/tmp/collection.json"
    )
    col2 = col1.full_copy()

    item = items[0].full_copy()
    item.id += "_test"
    col2.add_item(item, item.id)

    item = items[0].full_copy()
    item.id += "_test_other"
    col1.add_item(item, item.id)

    diff.generate_items_diff(col1, col2)
    diff.collections_defs_are_different(col1, col2)

    col1_filepath = "/tmp/col1.json"
    col1.set_self_href(col1_filepath)
    col1.save(catalog_type=pystac.CatalogType.RELATIVE_PUBLISHED)

    diff.compare_local_and_upstream(
        stac.StacTransactionsHandler(stac.DEFAULT_STAC_EP, sign=False),
        col1_filepath,
        "costarica-sentinel-2-l3-seasonal-spectral-indices-M",
    )


if __name__ == "__main__":
    test_diff()
