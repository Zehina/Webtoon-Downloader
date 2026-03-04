from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import cached_property

from bs4 import BeautifulSoup, NavigableString, Tag

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
    """Extractor for a webtoon series main page."""

    html: str | BeautifulSoup

    @cached_property
    def soup(self) -> BeautifulSoup:
        return _ensure_beautiful_soup(self.html)

    @cached_property
    def series_title(self) -> str:
        tag = self.soup.find(class_="subj")
        if not tag:
            raise ElementNotFoundError("subj")
        return tag.get_text(separator=" ").replace("\n", "").replace("\t", "")

    @cached_property
    def series_summary(self) -> str:
        tag = self.soup.find(class_="summary")
        if not tag:
            raise ElementNotFoundError("summary")
        return tag.get_text(separator=" ").replace("\n", "").replace("\t", "")

    @cached_property
    def author(self) -> str | None:
        meta_author = self._get_author_from_meta()
        if meta_author:
            return meta_author

        log.debug("Author meta tag not found; trying author_area fallback")
        area_author = self._get_author_from_author_area()
        if area_author:
            return area_author

        log.debug("Author not found in known selectors")
        return None

    @cached_property
    def genre(self) -> str | None:
        genre_tag = self.soup.find("h2", class_=re.compile(r"\bgenre\b"))
        if not isinstance(genre_tag, Tag):
            log.debug("Genre not found in known selectors")
            return None

        genre = genre_tag.get_text().strip()
        if not genre:
            log.debug("Genre not found in known selectors")
            return None

        return genre

    def _get_author_from_meta(self) -> str | None:
        meta_tag = self.soup.find("meta", attrs={"property": "com-linewebtoon:webtoon:author"})
        if not isinstance(meta_tag, Tag):
            return None

        content = meta_tag.get("content")
        if not isinstance(content, str):
            return None

        value = content.strip()
        return value or None

    def _get_author_from_author_area(self) -> str | None:
        author_area = self.soup.find("div", class_="author_area")
        if not isinstance(author_area, Tag):
            return None

        for child in author_area.children:
            if not isinstance(child, NavigableString):
                continue
            value = str(child).strip()
            if value:
                return value

        return None


@dataclass
class WebtoonViewerPageExtractor:
    """Extractor for a webtoon chapter viewer page."""

    html: str | BeautifulSoup

    @cached_property
    def soup(self) -> BeautifulSoup:
        return _ensure_beautiful_soup(self.html)

    @cached_property
    def chapter_notes(self) -> str:
        tag = self.soup.find(class_="author_text")
        if not tag:
            return ""
        return tag.get_text().strip().replace("\r\n", "\n")

    @cached_property
    def img_urls(self) -> list[str]:
        nav = self.soup.find("div", class_=re.compile(r"\bviewer_img\b.*\b_img_viewer_area\b"))
        if not nav:
            raise ElementNotFoundError("_img_viewer_area")

        if not isinstance(nav, Tag):
            log.debug("img container is not a tag object but a %s", type(nav))
            return []

        tags = nav.find_all("img")
        if not tags:
            log.debug("img tags not found in img container")
            raise ElementNotFoundError("img")

        return [tag["data-url"].replace("?type=q90", "") for tag in tags]
