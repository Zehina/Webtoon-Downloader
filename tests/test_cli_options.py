from click.testing import CliRunner

from webtoon_downloader.cmd.cli import cli


def test_cli_rejects_mixing_episode_id_with_episode_id_range() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
            "--episode-id",
            "652",
            "--episode-id-start",
            "650",
        ],
    )

    assert result.exit_code != 0
    assert "--episode-id cannot be used with --episode-id-start/--episode-id-end" in result.output


def test_cli_rejects_mixing_chapter_range_with_episode_id_filters() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
            "--start",
            "10",
            "--episode-id",
            "652",
        ],
    )

    assert result.exit_code != 0
    assert "--episode-id/--episode-id-start/--episode-id-end" in result.output


def test_cli_rejects_latest_with_episode_id_filters() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
            "--latest",
            "--episode-id",
            "652",
        ],
    )

    assert result.exit_code != 0
    assert "--latest cannot be used together" in result.output
