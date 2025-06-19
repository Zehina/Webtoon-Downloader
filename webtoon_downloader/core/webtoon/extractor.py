from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag
from furl import furl

log = logging.getLogger(__name__)


class InvalidHTMLObject(TypeError):
    """Exception raised when variable is neither a string nor a BeautifulSoup object."""

    def __str__(self) -> str:
        return "Variable passed is neither a string nor a BeautifulSoup object"


class ElementNotFoundError(Exception):
    """Exception raised when an expected element is not found."""

    def __init__(self, element_name: str):
        self.element_name = element_name
        super().__init__(f"Element '{element_name}' not found")


def _ensure_beautiful_soup(html: str | BeautifulSoup) -> BeautifulSoup:
    """Ensure the provided HTML is a BeautifulSoup object."""
    if not isinstance(html, str) and not isinstance(html, BeautifulSoup):
        raise InvalidHTMLObject()

    return html if isinstance(html, BeautifulSoup) else BeautifulSoup(html, "lxml")


@dataclass(frozen=True)
class WebtoonMainPageExtractor:
    """Extractor for the main page of a Webtoon. The results are cached for faster lookup

    Attributes:
        html: HTML content of the Webtoon main page. (ex: https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95)
    """

    html: str | BeautifulSoup

    _soup: BeautifulSoup = field(init=False)
    _title: str = field(init=False)
    _summary: str = field(init=False)
    _viewer_url: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_soup", _ensure_beautiful_soup(self.html))

    def get_series_title(self) -> str:
        """Extracts the full title series."""
        if hasattr(self, "_title"):
            return self._title

        _tag = self._soup.find(class_="subj")
        if not _tag:
            raise ElementNotFoundError("subj")

        title = _tag.get_text(separator=" ").replace("\n", "").replace("\t", "")
        object.__setattr__(self, "_title", title)
        return title

    def get_series_summary(self) -> str:
        """Extracts the series summary."""
        if hasattr(self, "_summary"):
            return self._summary
        _tag = self._soup.find(class_="summary")
        if not _tag:
            raise ElementNotFoundError("summary")

        summary = _tag.get_text(separator=" ").replace("\n", "").replace("\t", "")
        object.__setattr__(self, "_summary", summary)
        return summary

    def get_chapter_viewer_url(self) -> str:
        """Extracts the URL of the webtoon chapter reader."""
        if hasattr(self, "_viewer_url"):
            return self._viewer_url
        _tag = self._soup.select_one("#_btnEpisode")
        if not _tag:
            raise ElementNotFoundError("_btnEpisode")

        _href = _tag["href"]
        if isinstance(_href, list):
            _href = _href[0]

        viewer_url = str(furl(_href).remove(args=["episode_no"]))
        object.__setattr__(self, "_viewer_url", viewer_url)
        return viewer_url


@dataclass
class WebtoonViewerPageExtractor:
    """Extractor for a viewer page of a Webtoon.

    Attributes:
        html: HTML content of a Webtoon viewer page. (ex: https://www.webtoons.com/en/fantasy/tower-of-god/season-3-ep-173/viewer?title_no=95&episode_no=591)
    """

    html: str | BeautifulSoup

    _soup: BeautifulSoup = field(init=False)
    _title: str = field(init=False)
    _notes: str = field(init=False)
    _img_urls: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self._soup = _ensure_beautiful_soup(self.html)

    def get_chapter_title(self) -> str:
        """Extracts the chapter title."""
        if hasattr(self, "_title"):
            return self._title

        _tag = self._soup.find("h1")
        if not _tag:
            raise ElementNotFoundError("title_h1")

        self._title = _tag.get_text().strip()
        return self._title

    def get_chapter_notes(self) -> str:
        """Extracts the chapter author notes if it exists. Returns an empty string otherwise"""
        if hasattr(self, "_notes"):
            return self._notes

        _tag = self._soup.find(class_="author_text")
        if not _tag:
            return ""

        self._notes = _tag.get_text().strip().replace("\r\n", "\n")
        return self._notes

    def get_img_urls(self) -> list[str]:
        """Extracts image URLs from the chapter."""
        if hasattr(self, "_img_urls"):
            log.debug("Found cached image URLs in extractor")
            return self._img_urls

        _nav = self._soup.find("div", class_=re.compile(r"\bviewer_img\b.*\b_img_viewer_area\b"))

        if not _nav:
            raise ElementNotFoundError("_img_viewer_area")

        if not isinstance(_nav, Tag):
            log.debug("img container is not a tag object but a %s", type(_nav))
            return []

        _tags = _nav.find_all("img")
        if not _tags:
            log.debug("img tags not found in img container")
            raise ElementNotFoundError("all_img")

        self._img_urls = [tag["data-url"] for tag in _tags]

        # Attempt to remove Webtoons compression by removing "?type=q90" at the end of URLs
        self._img_urls = [url.replace("?type=q90", "") for url in self._img_urls]

        return self._img_urls
