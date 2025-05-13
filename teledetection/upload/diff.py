"""STAC diff tool."""

from typing import Tuple, List, cast
from pystac import Collection, Item
from rich import print
from teledetection.sdk.logger import get_logger_for

from . import stac

logger = get_logger_for(__name__)

UNIQUE_SEP = "___"


def collections_defs_are_different(col1: Collection, col2: Collection) -> bool:
    """Compute the diff between 2 STAC collections."""

    def fields_are_different(col1: Collection, col2: Collection, field_name: str):
        recursive_fields = field_name.split(".")

        f1 = col1
        f2 = col2
        for f in recursive_fields:
            f1 = getattr(f1, f)
            f2 = getattr(f2, f)

        if f1 != f2:
            logger.info(f"{field_name} is different: '{f1}' != '{f2}'")
            return True
        return False

    fields = [
        "extent.spatial.bboxes",
        "extent.temporal.intervals",
        "description",
        "id",
        "keywords",
        "license",
        "strategy",
        "providers",
        "title",
    ]
    return any(fields_are_different(col1, col2, field) for field in fields)


def generate_items_diff(
    col1: Collection, col2: Collection
) -> Tuple[List[Item], List[Item]]:
    """Compute the diff between 2 STAC collections.

    Returns:
    - list of items only in collection 1
    - list of items only in collection 2
    """

    def item_get_unique(i: Item) -> str:
        return i.id + UNIQUE_SEP + str(i.datetime.isoformat() if i.datetime else "")

    col1_ids = [item_get_unique(i) for i in col1.get_items()]
    col2_ids = [item_get_unique(i) for i in col2.get_items()]

    only_in_1 = set(col1_ids) - set(col2_ids)
    only_in_2 = set(col2_ids) - set(col1_ids)

    def unique_retrieve_info(unique: str, col: Collection) -> Item:
        id = unique.split(UNIQUE_SEP)[0]
        item = col.get_item(id)
        if not item:
            raise Exception(f"Item {id} not found")
        return item

    list_only_in_1 = [unique_retrieve_info(unique, col1) for unique in only_in_1]
    list_only_in_2 = [unique_retrieve_info(unique, col2) for unique in only_in_2]

    return list_only_in_1, list_only_in_2


def compare_local_and_upstream(
    handler: stac.StacTransactionsHandler,
    local_col_path: str,
    remote_col_id: str = "",
):
    """Compare a local and a remote collection.

    Args:
        handler (stac.StacTransactionHandler): object to handle the connection
        local_col_path (str): path to local collection path
        remote_col_id (str, optional): Remote collection identifier.
            If unset, will take the same id as the local collection
    """
    col_local = cast(Collection, stac.load_stac_obj(obj_pth=local_col_path))
    col_remote = handler.client.get_collection(remote_col_id or col_local.id)

    only_local, only_remote = generate_items_diff(col_local, col_remote)

    collections_defs_are_different(col_local, col_remote)

    print(f"Only local ({len(only_local)}):")
    print(only_local[:20])

    print(f"Only remote ({len(only_remote)}):")
    print(only_remote[:20])
