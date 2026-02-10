from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from bs4 import BeautifulSoup, Tag
from furl import furl

from webtoon_downloader.core.exceptions import (
    ChapterDataEpisodeNumberFetchError,
    ChapterTitleFetchError,
    ChapterURLFetchError,
    InvalidURL,
    SeriesTitleFetchError,
    WebtoonGetError,
)
from webtoon_downloader.core.webtoon.api import WebtoonAPI
from webtoon_downloader.core.webtoon.client import WebtoonHttpClient, WebtoonURL
from webtoon_downloader.core.webtoon.models import ChapterInfo

log = logging.getLogger(__name__)

ERR_CHAPTER_SELECTION_MIN = "{name} must be >= 1"
ERR_CHAPTER_SELECTION_RANGE = "start_chapter cannot be greater than end_chapter"
ERR_EPISODE_SELECTION_RANGE = "episode_id_start cannot be greater than episode_id_end"
ERR_EPISODE_EXCLUSIVE = "episode_id cannot be combined with episode_id_start/episode_id_end"
ERR_CHAPTER_EPISODE_EXCLUSIVE = "chapter index filters cannot be combined with episode-id filters"
ERR_LATEST_EXCLUSIVE = "latest selection cannot be combined with other chapter filters"


@dataclass(frozen=True)
class ChapterSelection:
    """Represents a single, explicit chapter-selection mode."""

    start_chapter: int | None = None
    end_chapter: int | None | Literal["latest"] = None
    episode_id: int | None = None
    episode_id_start: int | None = None
    episode_id_end: int | None = None

    def __post_init__(self) -> None:
        for value_name, value in (
            ("start_chapter", self.start_chapter),
            ("end_chapter", self.end_chapter),
            ("episode_id", self.episode_id),
            ("episode_id_start", self.episode_id_start),
            ("episode_id_end", self.episode_id_end),
        ):
            if isinstance(value, int) and value < 1:
                raise ValueError(ERR_CHAPTER_SELECTION_MIN.format(name=value_name))

        if (
            self.start_chapter is not None
            and isinstance(self.end_chapter, int)
            and self.start_chapter > self.end_chapter
        ):
            raise ValueError(ERR_CHAPTER_SELECTION_RANGE)

        if (
            self.episode_id_start is not None
            and self.episode_id_end is not None
            and self.episode_id_start > self.episode_id_end
        ):
            raise ValueError(ERR_EPISODE_SELECTION_RANGE)

        if self.episode_id is not None and (self.episode_id_start is not None or self.episode_id_end is not None):
            raise ValueError(ERR_EPISODE_EXCLUSIVE)

        has_episode_filters = (
            self.episode_id is not None
            or self.episode_id_start is not None
            or self.episode_id_end is not None
        )
        has_chapter_range = self.start_chapter is not None or isinstance(self.end_chapter, int)

        if has_chapter_range and has_episode_filters:
            raise ValueError(ERR_CHAPTER_EPISODE_EXCLUSIVE)

        if self.end_chapter == "latest" and (self.start_chapter is not None or has_episode_filters):
            raise ValueError(ERR_LATEST_EXCLUSIVE)


def apply_chapter_filters(chapter_details: list[ChapterInfo], selection: ChapterSelection) -> list[ChapterInfo]:
    """Apply chapter index and episode-id filters in a single place."""
    if not chapter_details:
        return []

    if selection.end_chapter == "latest":
        return [chapter_details[-1]]

    filtered = chapter_details[int(selection.start_chapter or 1) - 1 : selection.end_chapter]

    if selection.episode_id is not None:
        return [chapter for chapter in filtered if chapter.data_episode_no == selection.episode_id]

    if selection.episode_id_start is not None:
        filtered = [chapter for chapter in filtered if chapter.data_episode_no >= selection.episode_id_start]

    if selection.episode_id_end is not None:
        filtered = [chapter for chapter in filtered if chapter.data_episode_no <= selection.episode_id_end]

    return filtered


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
        # Look for the new format used in the provided HTML.
        series_title_tag = soup.find("strong", class_="subject")
        # Fallback: If the new format isn't found, look for the older format.
        if not series_title_tag:
            series_title_tag = soup.find("p", class_="subj")

        if not isinstance(series_title_tag, Tag):
            raise SeriesTitleFetchError("Failed to find series title with any known tag.")  # noqa: TRY003

        return series_title_tag.text

    def _get_webtoon_type(self, series_url: str) -> Literal["webtoon", "canvas"]:
        if "canvas" in series_url:
            return "canvas"
        return "webtoon"

    def _get_series_api_url(self, series_url: str, series_id: int) -> str:
        return f"https://m.webtoons.com/api/v1/{self._get_webtoon_type(series_url)}/{series_id}"

    async def get_chapters_details(
        self,
        series_url: str,
        selection: ChapterSelection | None = None,
    ) -> list[ChapterInfo]:
        """
        fetches and parses chapter details from a given Webtoon series URL.

        This method retrieves chapter information, including chapter numbers, URLs, titles, and total chapter count.

        Args:
            series_url      : The URL of the Webtoon series from which to fetch chapter details.
            selection       : Chapter selection criteria. Defaults to all chapters.

        Returns:
            A list of ChapterInfo objects containing details for each chapter.
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
            (self._get_series_api_url(mobile_url, title_id)), page_size=99999
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

        return apply_chapter_filters(chapter_details=chapter_details, selection=selection or ChapterSelection())
