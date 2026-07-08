from __future__ import annotations

import httpx

from webtoon_downloader.core.webtoon.api import (
    REQUEST_ALL_EPISODES_PAGE_SIZE,
    WEBTOON_TYPE_CANVAS,
    WEBTOON_TYPE_ORIGINAL,
    WebtoonSeriesType,
    build_episodes_url,
    build_series_api_url,
)
from webtoon_downloader.core.webtoon.client import WebtoonHttpClient
from webtoon_downloader.core.webtoon.fetchers import WebtoonFetcher

GLOBAL_WEBTOON_LANGUAGE_CODES = ("de", "en", "es", "fr", "id", "th", "zh-hant")
ORIGINALS_GENRE_SEGMENTS = (
    "action",
    "comedy",
    "drama",
    "fantasy",
    "horror",
    "romance",
    "super-hero",
    "supernatural",
    "thriller",
)


class DummyClient(WebtoonHttpClient):
    async def get(self, url: str) -> httpx.Response:
        raise AssertionError(url)


def test_url_builder() -> None:
    series_cases: tuple[tuple[WebtoonSeriesType, int, str], ...] = (
        (WEBTOON_TYPE_ORIGINAL, 95, "https://m.webtoons.com/api/v1/webtoon/95"),
        (WEBTOON_TYPE_CANVAS, 883187, "https://m.webtoons.com/api/v1/canvas/883187"),
    )
    for webtoon_type, series_id, expected_url in series_cases:
        assert build_series_api_url(webtoon_type, series_id) == expected_url

    for language_code in GLOBAL_WEBTOON_LANGUAGE_CODES:
        url = build_episodes_url(
            build_series_api_url(WEBTOON_TYPE_CANVAS, 883187),
            page_size=REQUEST_ALL_EPISODES_PAGE_SIZE,
            reading_language_code=language_code,
        )
        assert (
            url == "https://m.webtoons.com/api/v1/canvas/883187/episodes"
            f"?pageSize={REQUEST_ALL_EPISODES_PAGE_SIZE}&readingLanguageCode={language_code}"
        )

    assert (
        build_episodes_url(
            "https://m.webtoons.com/api/v1/canvas/883187/",
            page_size=REQUEST_ALL_EPISODES_PAGE_SIZE,
            reading_language_code="en",
        )
        == "https://m.webtoons.com/api/v1/canvas/883187/episodes"
        f"?pageSize={REQUEST_ALL_EPISODES_PAGE_SIZE}&readingLanguageCode=en"
    )
    assert (
        build_episodes_url(
            "https://m.webtoons.com/api/v1/canvas/883187/episodes",
            page_size=REQUEST_ALL_EPISODES_PAGE_SIZE,
            reading_language_code="en",
        )
        == "https://m.webtoons.com/api/v1/canvas/883187/episodes"
        f"?pageSize={REQUEST_ALL_EPISODES_PAGE_SIZE}&readingLanguageCode=en"
    )
    assert (
        build_episodes_url(
            build_series_api_url(WEBTOON_TYPE_ORIGINAL, 95),
            page_size=REQUEST_ALL_EPISODES_PAGE_SIZE,
        )
        == f"https://m.webtoons.com/api/v1/webtoon/95/episodes?pageSize={REQUEST_ALL_EPISODES_PAGE_SIZE}"
    )
    assert (
        build_episodes_url(
            "https://m.webtoons.com/api/v1/canvas/883187/episodes?pageSize=1&readingLanguageCode=fr",
            page_size=REQUEST_ALL_EPISODES_PAGE_SIZE,
            reading_language_code="en",
        )
        == "https://m.webtoons.com/api/v1/canvas/883187/episodes"
        f"?pageSize={REQUEST_ALL_EPISODES_PAGE_SIZE}&readingLanguageCode=en"
    )


def test_webtoon_url_parsing() -> None:
    fetcher = WebtoonFetcher(client=DummyClient(), series_url="https://www.webtoons.com")

    assert fetcher.get_series_api_url(
        "https://www.webtoons.com/en/canvas/frog-wizards/list?title_no=883187", 883187
    ) == build_series_api_url(WEBTOON_TYPE_CANVAS, 883187)
    for genre_segment in ORIGINALS_GENRE_SEGMENTS:
        url = f"https://www.webtoons.com/en/{genre_segment}/canvas-knight/list?title_no=95"
        assert fetcher.get_series_api_url(url, 95) == build_series_api_url(WEBTOON_TYPE_ORIGINAL, 95)

    for language_code in GLOBAL_WEBTOON_LANGUAGE_CODES:
        url = f"https://www.webtoons.com/{language_code}/canvas/frog-wizards/list?title_no=883187"
        assert fetcher.get_reading_language_code(url) == language_code
