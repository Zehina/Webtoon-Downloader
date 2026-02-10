import pytest

from webtoon_downloader.core.webtoon.client import WebtoonHttpClient
from webtoon_downloader.core.webtoon.fetchers import ChapterSelection, WebtoonFetcher

SERIES_URL = "https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95"


@pytest.mark.asyncio
async def test_get_chapters_details_episode_id_filter_e2e() -> None:
    async with WebtoonHttpClient() as client:
        fetcher = WebtoonFetcher(client, SERIES_URL)
        all_chapters = await fetcher.get_chapters_details(SERIES_URL)
        target = all_chapters[-2]

        filtered = await fetcher.get_chapters_details(
            SERIES_URL,
            selection=ChapterSelection(episode_id=target.data_episode_no),
        )

    assert len(filtered) == 1
    assert filtered[0].data_episode_no == target.data_episode_no
    assert filtered[0].number == target.number


@pytest.mark.asyncio
async def test_get_chapters_details_episode_id_range_filter_e2e() -> None:
    async with WebtoonHttpClient() as client:
        fetcher = WebtoonFetcher(client, SERIES_URL)
        all_chapters = await fetcher.get_chapters_details(SERIES_URL)

        lo = all_chapters[-4].data_episode_no
        hi = all_chapters[-2].data_episode_no

        filtered = await fetcher.get_chapters_details(
            SERIES_URL,
            selection=ChapterSelection(episode_id_start=lo, episode_id_end=hi),
        )

    assert filtered
    assert all(lo <= chapter.data_episode_no <= hi for chapter in filtered)


@pytest.mark.asyncio
async def test_get_chapters_details_applies_chapter_slice_before_episode_filter_e2e() -> None:
    async with WebtoonHttpClient() as client:
        fetcher = WebtoonFetcher(client, SERIES_URL)
        all_chapters = await fetcher.get_chapters_details(SERIES_URL)

        assert len(all_chapters) >= 3
        first = all_chapters[0]

        filtered = await fetcher.get_chapters_details(
            SERIES_URL,
            selection=ChapterSelection(start_chapter=2, end_chapter=2, episode_id=first.data_episode_no),
        )

    assert filtered == []


@pytest.mark.asyncio
async def test_get_chapters_details_latest_e2e() -> None:
    async with WebtoonHttpClient() as client:
        fetcher = WebtoonFetcher(client, SERIES_URL)
        all_chapters = await fetcher.get_chapters_details(SERIES_URL)
        latest = await fetcher.get_chapters_details(SERIES_URL, selection=ChapterSelection(end_chapter="latest"))

    assert len(latest) == 1
    assert latest[0].number == all_chapters[-1].number
    assert latest[0].data_episode_no == all_chapters[-1].data_episode_no
