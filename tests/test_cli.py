import pytest
from click.testing import CliRunner
from athena import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_main(runner):
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert not result.exception
    assert result.output.split('\n')[0].strip() == 'Usage: main [OPTIONS] COMMAND [ARGS]...'
