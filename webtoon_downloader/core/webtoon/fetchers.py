from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Literal, Sequence

import httpx
from bs4 import BeautifulSoup, Tag
from furl import furl

from webtoon_downloader.core.exceptions import (
    ChapterDataEpisodeNumberFetchError,
    ChapterTitleFetchError,
    ChapterURLFetchError,
    SeriesTitleFetchError,
)
from webtoon_downloader.core.webtoon import client
from webtoon_downloader.core.webtoon.models import ChapterInfo

log = logging.getLogger(__name__)


class WebtoonDomain(str, Enum):
    """valid webtoon subdomains"""

    MOBILE = "m"
    STANDARD = "www"


@dataclass
class WebtoonFetcher:
    """
    Fetches details of Webtoon chapters from a given series URL.

    This class is responsible for extracting information such as chapter titles, URLs, and episode numbers from Webtoon's HTML content.

    Attributes:
        client: The HTTP client used for making requests to Webtoon.
    """

    client: httpx.AsyncClient

    def _convert_url_domain(self, series_url: str, target_subdomain: WebtoonDomain) -> str:
        """Converts the provided Webtoon URL to the specified subdomain (default 'm')."""
        f = furl(series_url)
        domain_parts = f.host.split(".")
        domain_parts = [part for part in domain_parts if part not in [WebtoonDomain.MOBILE, WebtoonDomain.STANDARD]]
        domain_parts.insert(0, target_subdomain)
        f.host = ".".join(domain_parts)
        return str(f.url)

    def _get_viewer_url(self, tag: Tag) -> str:
        """Returns the viewer URL from the scrapped tag object"""
        viewer_url_tag = tag.find("a")
        if not isinstance(viewer_url_tag, Tag):
            raise ChapterURLFetchError
        return self._convert_url_domain(str(viewer_url_tag["href"]), target_subdomain=WebtoonDomain.STANDARD)

    def _get_chapter_title(self, tag: Tag) -> str:
        """Returns the chapter title from the scrapped tag object"""
        chapter_details_tag = tag.find("p", class_="sub_title")
        if not isinstance(chapter_details_tag, Tag):
            raise ChapterTitleFetchError
        chapter_details_tag = chapter_details_tag.find("span", class_="ellipsis")
        if not isinstance(chapter_details_tag, Tag):
            raise ChapterTitleFetchError
        return chapter_details_tag.text

    def _get_data_episode_num(self, tag: Tag) -> int:
        """Returns the chapter data episode number from the scrapped tag object"""
        data_episode_no_tag = tag["data-episode-no"]
        if not isinstance(data_episode_no_tag, str):
            raise ChapterDataEpisodeNumberFetchError
        return int(data_episode_no_tag)

    def _get_series_title(self, soup: BeautifulSoup) -> str:
        """Returns the series title from the scrapped tag object"""
        series_title_tag = soup.find("p", class_="subj")
        if not isinstance(series_title_tag, Tag):
            raise SeriesTitleFetchError
        return series_title_tag.text

    async def get_chapters_details(
        self, series_url: str, start_chapter: int | None = None, end_chapter: int | None | Literal["latest"] = None
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
        response = await self.client.get(
            mobile_url, headers={**self.client.headers, "user-agent": client.get_mobile_ua()}
        )
        soup = BeautifulSoup(response.text, "html.parser")
        chapter_items: Sequence[Tag] = soup.findAll("li", class_="_episodeItem")
        series_title = self._get_series_title(soup)

        chapter_details: list[ChapterInfo] = []
        for chapter_number, chapter_detail in enumerate(chapter_items[::-1], start=1):
            chapter_info = ChapterInfo(
                number=chapter_number,
                viewer_url=self._get_viewer_url(chapter_detail),
                title=self._get_chapter_title(chapter_detail),
                data_episode_no=self._get_data_episode_num(chapter_detail),
                total_chapters=len(chapter_items),
                series_title=series_title,
            )
            chapter_details.append(chapter_info)

        if end_chapter == "latest":
            return [chapter_details[-1]]

        return chapter_details[int(start_chapter or 1) - 1 : end_chapter]
