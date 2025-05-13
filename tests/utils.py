"""Utils file."""

from click.testing import CliRunner
from teledetection.sdk.logger import get_logger_for


log = get_logger_for(__name__)


def run_cli_cmd(command, args=None):
    """Test a CLI command."""
    log.info("Testing %s", command)
    runner = CliRunner()
    result = runner.invoke(command, args)
    log.info("Result is %s", result)
    assert result.exit_code == 0


def should_fail(func, args, exception_cls):
    """Helper with intended failing tests."""
    try:
        if isinstance(args, list):
            func(*args)
        else:
            func(**args)
        raise AssertionError("This test should fail!")
    except exception_cls:
        print("Failing as expected :)")
