import pytest

from webtoon_downloader.core.webtoon.api import EpisodeInfo, WebtoonAPI
from webtoon_downloader.core.webtoon.fetchers import WebtoonFetcher


class _DummyResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


class _DummyClient:
    async def get(self, _: str) -> _DummyResponse:
        return _DummyResponse(
            '<html><head><link rel="canonical" href="https://www.webtoons.com/en/test/list?title_no=123"/></head>'
            '<body><p class="subj">Series Title</p></body></html>'
        )


@pytest.mark.asyncio
async def test_get_chapters_details_filters_by_episode_id(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_get_episodes_data(self: WebtoonAPI, series_api_url: str, page_size: int = 30, cursor: int = 0):
        _ = (self, series_api_url, page_size, cursor)
        return [
            EpisodeInfo(
                episodeNo=200,
                thumbnail="",
                episodeTitle="A",
                viewerLink="/viewer?title_no=123&episode_no=200",
                exposureDateMillis=0,
                displayUp=True,
                hasBgm=None,
            ),
            EpisodeInfo(
                episodeNo=201,
                thumbnail="",
                episodeTitle="B",
                viewerLink="/viewer?title_no=123&episode_no=201",
                exposureDateMillis=0,
                displayUp=True,
                hasBgm=None,
            ),
            EpisodeInfo(
                episodeNo=202,
                thumbnail="",
                episodeTitle="C",
                viewerLink="/viewer?title_no=123&episode_no=202",
                exposureDateMillis=0,
                displayUp=True,
                hasBgm=None,
            ),
        ]

    monkeypatch.setattr(WebtoonAPI, "get_episodes_data", _fake_get_episodes_data)

    fetcher = WebtoonFetcher(_DummyClient(), "https://www.webtoons.com/en/test/list?title_no=123")
    chapters = await fetcher.get_chapters_details(
        "https://www.webtoons.com/en/test/list?title_no=123",
        episode_id=201,
    )

    assert len(chapters) == 1
    assert chapters[0].data_episode_no == 201
    assert chapters[0].number == 2


@pytest.mark.asyncio
async def test_get_chapters_details_filters_by_episode_range(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_get_episodes_data(self: WebtoonAPI, series_api_url: str, page_size: int = 30, cursor: int = 0):
        _ = (self, series_api_url, page_size, cursor)
        return [
            EpisodeInfo(
                episodeNo=300,
                thumbnail="",
                episodeTitle="A",
                viewerLink="/viewer?title_no=123&episode_no=300",
                exposureDateMillis=0,
                displayUp=True,
                hasBgm=None,
            ),
            EpisodeInfo(
                episodeNo=301,
                thumbnail="",
                episodeTitle="B",
                viewerLink="/viewer?title_no=123&episode_no=301",
                exposureDateMillis=0,
                displayUp=True,
                hasBgm=None,
            ),
            EpisodeInfo(
                episodeNo=302,
                thumbnail="",
                episodeTitle="C",
                viewerLink="/viewer?title_no=123&episode_no=302",
                exposureDateMillis=0,
                displayUp=True,
                hasBgm=None,
            ),
            EpisodeInfo(
                episodeNo=303,
                thumbnail="",
                episodeTitle="D",
                viewerLink="/viewer?title_no=123&episode_no=303",
                exposureDateMillis=0,
                displayUp=True,
                hasBgm=None,
            ),
        ]

    monkeypatch.setattr(WebtoonAPI, "get_episodes_data", _fake_get_episodes_data)

    fetcher = WebtoonFetcher(_DummyClient(), "https://www.webtoons.com/en/test/list?title_no=123")
    chapters = await fetcher.get_chapters_details(
        "https://www.webtoons.com/en/test/list?title_no=123",
        episode_id_start=301,
        episode_id_end=302,
    )

    assert [chapter.data_episode_no for chapter in chapters] == [301, 302]
    assert [chapter.number for chapter in chapters] == [2, 3]
