from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup
from furl import furl


class InvalidHTMLObject(TypeError):
    """Exception raised when variable is neither a string nor a BeautifulSoup object."""

    def __str__(self):
        return "Variable passed is neither a string nor a BeautifulSoup object"


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

    def __post_init__(self):
        self._soup = _ensure_beautiful_soup(self.html)

    def get_series_title(self) -> str:
        """Extracts the full title series."""
        return self._soup.find(class_="subj").get_text(separator=" ").replace("\n", "").replace("\t", "")

    def get_series_summary(self) -> str:
        """Extracts the series summary."""
        return self._soup.find(class_="summary").get_text(separator=" ").replace("\n", "").replace("\t", "")

    def get_chapter_viewer_url(self) -> str:
        """Extracts the URL of the webtoon chapter reader."""
        return furl(self._soup.select_one("#_btnEpisode")["href"]).remove(args=["episode_no"]).url


@dataclass
class WebtoonViewerPageExtractor:
    """Extractor for a viewer page of a Webtoon.

    Attributes:
        html: HTML content of a Webtoon viewer page. (ex: https://www.webtoons.com/en/fantasy/tower-of-god/season-3-ep-173/viewer?title_no=95&episode_no=591)
    """

    html: str | BeautifulSoup
    _soup: BeautifulSoup = field(init=False)

    def __post_init__(self):
        self._soup = _ensure_beautiful_soup(self.html)

    def get_chapter_title(self) -> str:
        """Extracts the chapter title."""
        return self._soup.find("h1").get_text().strip()

    def get_chapter_notes(self) -> str | None:
        """Extracts the chapter author notes."""
        node = self._soup.find(class_="author_text")
        return node.get_text().strip().replace("\r\n", "\n") if node else None

    def get_img_urls(self) -> list[str]:
        """Extracts image URLs from the chapter."""
        return [tag["data-url"] for tag in self._soup.find("div", class_="viewer_img _img_viewer_area").find_all("img")]
