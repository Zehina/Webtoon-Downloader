import logging
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

import dacite
from furl import furl

from webtoon_downloader.core.webtoon.client import WebtoonHttpClient, WebtoonMobileURL

log = logging.getLogger(__name__)

DEFAULT_EPISODE_PAGE_SIZE: Final = 30
"""Webtoon's default episode API page size."""

REQUEST_ALL_EPISODES_PAGE_SIZE: Final = 99999
"""Historical all-episodes page size used for one-call episode list requests."""

WebtoonSeriesType: TypeAlias = Literal["webtoon", "canvas"]
"""Known Webtoon episode API path segment values."""

WebtoonLanguageCode: TypeAlias = Literal["de", "en", "es", "fr", "id", "th", "zh-hant"]
"""Language path segments currently exposed by the global Webtoon site."""

WEBTOON_TYPE_ORIGINAL: Final[Literal["webtoon"]] = "webtoon"
"""Webtoon's API path segment for Originals series."""

WEBTOON_TYPE_CANVAS: Final[Literal["canvas"]] = "canvas"
"""Webtoon's API path segment for Canvas series."""

WEBTOON_API_ROOT_PATH_SEGMENTS: Final = ("api", "v1")
"""Root path segments for Webtoon's mobile API."""

WEBTOON_LANGUAGE_CODES: Final[tuple[WebtoonLanguageCode, ...]] = ("de", "en", "es", "fr", "id", "th", "zh-hant")
"""Language path segments currently exposed by the global Webtoon site."""

EPISODES_PATH_SEGMENT: Final = "episodes"
"""Webtoon's mobile API path segment for episode list requests."""


def build_series_api_url(webtoon_type: WebtoonSeriesType, series_id: int) -> str:
    """Build a Webtoon mobile series API URL."""
    url = furl(WebtoonMobileURL)
    url.path.segments = [*WEBTOON_API_ROOT_PATH_SEGMENTS, webtoon_type, str(series_id)]
    return str(url.url)


def build_episodes_url(
    series_api_url: str,
    *,
    page_size: int,
    reading_language_code: WebtoonLanguageCode | None = None,
) -> str:
    """Build a Webtoon mobile episode-list API URL."""
    url = furl(series_api_url)
    path_segments = [segment for segment in url.path.segments if segment]
    if not path_segments or path_segments[-1] != EPISODES_PATH_SEGMENT:
        path_segments.append(EPISODES_PATH_SEGMENT)

    url.path.segments = path_segments
    url.args.clear()
    url.args["pageSize"] = page_size
    if reading_language_code:
        url.args["readingLanguageCode"] = reading_language_code

    return str(url.url)


@dataclass
class EpisodeInfo:
    """Episode item returned by Webtoon's mobile episode API."""

    episodeNo: int
    thumbnail: str
    episodeTitle: str
    viewerLink: str
    exposureDateMillis: int
    displayUp: bool
    hasBgm: bool | None  # In Canvas this is not defined


@dataclass
class GetEpisodesResponseResult:
    """Payload wrapper containing the episode list returned by Webtoon."""

    episodeList: list[EpisodeInfo]


@dataclass
class GetEpisodesResponse:
    """Top-level response shape returned by Webtoon's episode API."""

    result: GetEpisodesResponseResult


@dataclass
class WebtoonAPI:
    """Small client for Webtoon's mobile API endpoints."""

    client: WebtoonHttpClient

    async def get_episodes_data(
        self,
        series_api_url: str,
        page_size: int = DEFAULT_EPISODE_PAGE_SIZE,
        reading_language_code: WebtoonLanguageCode | None = None,
    ) -> list[EpisodeInfo]:
        """Return episode data for a given series ID."""
        # Canvas series return an HTTP 500 error when readingLanguageCode is not provided.
        url = build_episodes_url(
            series_api_url,
            page_size=page_size,
            reading_language_code=reading_language_code,
        )
        response = await self.client.get(url)
        response.raise_for_status()
        resp = dacite.from_dict(data_class=GetEpisodesResponse, data=response.json())
        data = resp.result.episodeList
        log.debug("Received %d episodes", len(data))
        return data
