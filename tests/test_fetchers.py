import pytest

from webtoon_downloader.core.webtoon.client import WebtoonHttpClient
from webtoon_downloader.core.webtoon.fetchers import WebtoonFetcher

SERIES_URL = "https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95"


@pytest.mark.asyncio
async def test_get_chapters_details_filters_by_episode_id_live() -> None:
    async with WebtoonHttpClient() as client:
        fetcher = WebtoonFetcher(client, SERIES_URL)
        all_chapters = await fetcher.get_chapters_details(SERIES_URL)

        # pick a stable chapter from the latest area
        target = all_chapters[-2]

        filtered = await fetcher.get_chapters_details(SERIES_URL, episode_id=target.data_episode_no)

    assert len(filtered) == 1
    assert filtered[0].data_episode_no == target.data_episode_no
    assert filtered[0].number == target.number


@pytest.mark.asyncio
async def test_get_chapters_details_filters_by_episode_id_range_live() -> None:
    async with WebtoonHttpClient() as client:
        fetcher = WebtoonFetcher(client, SERIES_URL)
        all_chapters = await fetcher.get_chapters_details(SERIES_URL)

        lo = all_chapters[-4].data_episode_no
        hi = all_chapters[-2].data_episode_no

        filtered = await fetcher.get_chapters_details(
            SERIES_URL,
            episode_id_start=lo,
            episode_id_end=hi,
        )

    assert filtered
    assert all(lo <= chapter.data_episode_no <= hi for chapter in filtered)
