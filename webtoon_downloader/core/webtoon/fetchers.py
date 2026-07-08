from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal, TypeAlias, cast

from bs4 import BeautifulSoup, Tag
from furl import furl

from webtoon_downloader.core.exceptions import (
    InvalidURL,
    SeriesTitleFetchError,
    WebtoonGetError,
)
from webtoon_downloader.core.webtoon.api import (
    REQUEST_ALL_EPISODES_PAGE_SIZE,
    WEBTOON_LANGUAGE_CODES,
    WEBTOON_TYPE_CANVAS,
    WEBTOON_TYPE_ORIGINAL,
    WebtoonAPI,
    WebtoonLanguageCode,
    WebtoonSeriesType,
    build_series_api_url,
)
from webtoon_downloader.core.webtoon.client import WebtoonHttpClient, WebtoonURL
from webtoon_downloader.core.webtoon.models import ChapterInfo

log = logging.getLogger(__name__)

END_CHAPTER_LATEST: Final = "latest"
"""Sentinel used internally when the caller requests only the latest episode."""

EndChapter: TypeAlias = int | None | Literal["latest"]
"""Chapter range end value accepted by downloader/fetcher APIs."""


class WebtoonDomain(str, Enum):
    """valid webtoon subdomains"""

    MOBILE = "m"
    STANDARD = "www"


class TitleNoFetchError(Exception):
    """Custom exception for when the title number cannot be found."""


@dataclass
class WebtoonFetcher:
    """
    Fetches details of Webtoon chapters from a given series URL.

    This class is responsible for extracting information such as chapter titles, URLs, and episode numbers from Webtoon's HTML content.

    Attributes:
        client: The HTTP client used for making requests to Webtoon.
        series_url: The URL of the Webtoon series from which to fetch details.
    """

    client: WebtoonHttpClient
    series_url: str

    def _convert_url_domain(self, viewer_url: str, target_subdomain: WebtoonDomain) -> str:
        """Converts the provided Webtoon URL to the specified subdomain (default 'm')."""
        viewer_url = viewer_url.replace("\\", "/")

        f = furl(viewer_url)
        if not f.scheme or not f.host:
            raise InvalidURL(viewer_url)

        domain_parts = f.host.split(".")
        domain_parts = [part for part in domain_parts if part not in [WebtoonDomain.MOBILE, WebtoonDomain.STANDARD]]
        domain_parts.insert(0, target_subdomain)
        f.host = ".".join(domain_parts)
        return str(f.url)

    def _get_title_no(self, soup: BeautifulSoup) -> int:
        """
        Returns the title number by parsing the canonical link tag object
        """
        canonical_link_tag = soup.find("link", rel="canonical")
        if not isinstance(canonical_link_tag, Tag):
            raise TitleNoFetchError

        if not canonical_link_tag.has_attr("href"):
            raise TitleNoFetchError("Could not find the canonical link tag in the HTML.")  # noqa: TRY003

        f = furl(str(canonical_link_tag["href"]))
        title = f.args.get("title_no")
        if not title:
            raise TitleNoFetchError

        return int(title)

    def _get_series_title(self, soup: BeautifulSoup) -> str:
        """Returns the series title from the scrapped tag object"""
        # Look for the new format used in the provided HTML.
        series_title_tag = soup.find("strong", class_="subject")
        # Fallback: If the new format isn't found, look for the older format.
        if not series_title_tag:
            series_title_tag = soup.find("p", class_="subj")

        if not isinstance(series_title_tag, Tag):
            raise SeriesTitleFetchError("Failed to find series title with any known tag.")  # noqa: TRY003

        return series_title_tag.text

    def _get_webtoon_type(self, series_url: str) -> WebtoonSeriesType:
        path_segments = [segment for segment in furl(series_url).path.segments if segment]
        return WEBTOON_TYPE_CANVAS if WEBTOON_TYPE_CANVAS in path_segments else WEBTOON_TYPE_ORIGINAL

    def get_series_api_url(self, series_url: str, series_id: int) -> str:
        """Return the mobile API URL for a Webtoon series."""
        return build_series_api_url(self._get_webtoon_type(series_url), series_id)

    def _get_series_api_url(self, series_url: str, series_id: int) -> str:
        return self.get_series_api_url(series_url, series_id)

    def _get_reading_language_code(self, series_url: str) -> WebtoonLanguageCode | None:
        """Return the URL language segment Webtoon's episode API expects."""
        path_segments = [segment for segment in furl(series_url).path.segments if segment]
        if path_segments and path_segments[0] in WEBTOON_LANGUAGE_CODES:
            return cast("WebtoonLanguageCode", path_segments[0])
        return None

    def get_reading_language_code(self, series_url: str) -> WebtoonLanguageCode | None:
        """Return the language segment from a Webtoon URL."""
        return self._get_reading_language_code(series_url)

    async def get_chapters_details(
        self, series_url: str, start_chapter: int | None = None, end_chapter: EndChapter = None
    ) -> list[ChapterInfo]:
        """
        fetches and parses chapter details from a given Webtoon series URL.

        This method retrieves chapter information, including chapter numbers, URLs, titles, and total chapter count.

        Args:
            series_url      : The URL of the Webtoon series from which to fetch chapter details.
            start_chapter   : The starting chapter number from which to begin fetching details.
            end_chapter     : chapter number up to which details should be fetched.

        Returns:
            A list of ChapterInfo objects containing details for each chapter.
            If end_chapter None, fetches all chapters up to the last available.
            If end_chapter is set to latest and start_chapter is None then returns the last chapter
            If both `start_chapter` and `end_chapter` are None, returns all chapters.
        """
        mobile_url = self._convert_url_domain(series_url, WebtoonDomain.MOBILE)
        webtoon_api = WebtoonAPI(self.client)
        response = await self.client.get(mobile_url)
        if response.status_code != 200:
            raise WebtoonGetError(series_url, response.status_code)

        soup = BeautifulSoup(response.text, "html.parser")
        title_id = self._get_title_no(soup)
        log.debug("Title ID: %s", title_id)
        series_title = self._get_series_title(soup)

        chapter_items = await webtoon_api.get_episodes_data(
            (self._get_series_api_url(mobile_url, title_id)),
            page_size=REQUEST_ALL_EPISODES_PAGE_SIZE,
            reading_language_code=self._get_reading_language_code(mobile_url),
        )

        chapter_details: list[ChapterInfo] = []
        for chapter_number, chapter_detail in enumerate(chapter_items, start=1):
            chapter_info = ChapterInfo(
                number=chapter_number,
                viewer_url=f"{WebtoonURL}{chapter_detail.viewerLink}",
                title=chapter_detail.episodeTitle.strip(),
                data_episode_no=chapter_detail.episodeNo,
                total_chapters=len(chapter_items),
                series_title=series_title.strip(),
            )
            chapter_details.append(chapter_info)

        if end_chapter == END_CHAPTER_LATEST:
            return [chapter_details[-1]]

        return chapter_details[int(start_chapter or 1) - 1 : end_chapter]
