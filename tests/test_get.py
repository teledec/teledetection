"""Test file."""

import pystac
import utils  # type: ignore

from teledetection import cli
from teledetection.upload import stac

utils.set_test_stac_ep()


def test_get():
    """Test get collections, items, etc."""
    handler = stac.StacTransactionsHandler(
        stac_endpoint=cli.DEFAULT_STAC_EP, sign=False
    )

    for col in handler.client.get_collections():
        col_from_handler = handler.client.get_collection(col.id)
        assert col_from_handler
        assert isinstance(col_from_handler, pystac.Collection)
        items = handler.get_items(col_id=col.id, max_items=1)  # test get_items()
        assert isinstance(items, list)
        for item in items:
            item_from_handler = handler.get_item(
                col_id=col.id, item_id=item.id
            )  # test get_item()
            assert item_from_handler
            assert isinstance(item_from_handler, pystac.Item)


if __name__ == "__main__":
    test_get()
