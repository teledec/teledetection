"""Test CLI."""

import utils  # type: ignore
from click.testing import CliRunner

from teledetection.cli import collection_diff, grab, list_col_items, list_cols

utils.set_test_stac_ep()


def _test_cli(command, args=None):
    """Test a CLI command."""
    print(f"Testing {command}")
    runner = CliRunner()
    result = runner.invoke(command, args)
    print(result)
    assert result.exit_code == 0


_test_cli(list_cols)
_test_cli(list_col_items, ["--col_id", "spot-6-7-drs"])
_test_cli(grab, ["--col_id", "spot-6-7-drs", "--out_json", "/tmp/col.json"])
_test_cli(grab, ["--col_id", "spot-6-7-drs", "--out_json", "/tmp/col.json", "--pretty"])
_test_cli(
    grab,
    [
        "--col_id",
        "spot-6-7-drs",
        "--item_id",
        "SPOT7_MS_201805051026429_SPOT7_P_201805051026429_1",
        "--out_json",
        "/tmp/item.json",
    ],
)
_test_cli(
    grab,
    [
        "--col_id",
        "spot-6-7-drs",
        "--item_id",
        "SPOT7_MS_201805051026429_SPOT7_P_201805051026429_1",
        "--out_json",
        "/tmp/item.json",
        "--pretty",
    ],
)
_test_cli(
    collection_diff, ["--remote_id", "spot-6-7-drs", "--col_path", "/tmp/col.json"]
)
