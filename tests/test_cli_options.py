from click.testing import CliRunner

from webtoon_downloader.cmd.cli import cli


def test_cli_shows_episode_options_in_help() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "--episode-id" in result.output
    assert "--episode-id-start" in result.output
    assert "--episode-id-end" in result.output
