from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag
from furl import furl


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


@dataclass
class WebtoonMainPageExtractor:
    """Extractor for the main page of a Webtoon.

    Attributes:
        html: HTML content of the Webtoon main page. (ex: https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95)
    """

    html: str | BeautifulSoup
    _soup: BeautifulSoup = field(init=False)

    def __post_init__(self) -> None:
        self._soup = _ensure_beautiful_soup(self.html)

    def get_series_title(self) -> str:
        """Extracts the full title series."""
        _tag = self._soup.find(class_="subj")
        if not _tag:
            raise ElementNotFoundError("sub")

        return _tag.get_text(separator=" ").replace("\n", "").replace("\t", "")

    def get_series_summary(self) -> str:
        """Extracts the series summary."""
        _tag = self._soup.find(class_="summary")
        if not _tag:
            raise ElementNotFoundError("summary")

        return _tag.get_text(separator=" ").replace("\n", "").replace("\t", "")

    def get_chapter_viewer_url(self) -> str:
        """Extracts the URL of the webtoon chapter reader."""
        _tag = self._soup.select_one("#_btnEpisode")
        if not _tag:
            raise ElementNotFoundError("_btnEpisode")

        return str(furl(_tag["href"]).remove(args=["episode_no"]))


@dataclass
class WebtoonViewerPageExtractor:
    """Extractor for a viewer page of a Webtoon.

    Attributes:
        html: HTML content of a Webtoon viewer page. (ex: https://www.webtoons.com/en/fantasy/tower-of-god/season-3-ep-173/viewer?title_no=95&episode_no=591)
    """

    html: str | BeautifulSoup
    _soup: BeautifulSoup = field(init=False)

    def __post_init__(self) -> None:
        self._soup = _ensure_beautiful_soup(self.html)

    def get_chapter_title(self) -> str:
        """Extracts the chapter title."""
        _tag = self._soup.find("h1")
        if not _tag:
            raise ElementNotFoundError("title_h1")

        return _tag.get_text().strip()

    def get_chapter_notes(self) -> str:
        """Extracts the chapter author notes if it exists. Returns an empty string otherwise"""
        _tag = self._soup.find(class_="author_text")
        if not _tag:
            return ""

        return _tag.get_text().strip().replace("\r\n", "\n")

    def get_img_urls(self) -> list[str]:
        """Extracts image URLs from the chapter."""
        _nav = self._soup.find("div", class_="viewer_img _img_viewer_area")
        if not isinstance(_nav, Tag):
            return []

        if not _nav:
            raise ElementNotFoundError("_img_viewer_area")

        _tags = _nav.find_all("img")
        if not _tags:
            raise ElementNotFoundError("all_img")

        return [tag["data-url"] for tag in _tags]
