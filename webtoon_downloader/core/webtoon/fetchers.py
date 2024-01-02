from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup, Tag

from webtoon_downloader.core.webtoon.models import ChapterInfo

log = logging.getLogger(__name__)


@dataclass
class WebtoonFetcher:
    client: httpx.AsyncClient

    async def get_first_chapter_episode_no(self, series_url: str) -> int:
        response = await self.client.get(series_url)
        soup = BeautifulSoup(response.text, "html.parser")
        _tag = soup.find("a", id="_btnEpisode")
        if not isinstance(_tag, Tag):
            return -1

        href = str(_tag.get("href"))
        if not href:
            return -1

        episode_no = href.rsplit("episode_no=", maxsplit=1)[-1]
        if episode_no.isdigit():
            return int(episode_no)

        # Fallback method: Get the first episode from the list
        response = await self.client.get(f"{series_url}&page=9999")
        soup = BeautifulSoup(response.text, "html.parser")
        return min(
            int(episode["data-episode-no"])
            for episode in soup.find_all("li", {"class": "_episodeItem"})
        )

    async def get_chapters_details(
        self,
        viewer_url: str,
        series_url: str,
        start_chapter: int = 1,
        end_chapter: int | None = None,
    ) -> list[ChapterInfo]:
        first_chapter = await self.get_first_chapter_episode_no(series_url)
        episode_url = f"{viewer_url}&episode_no={first_chapter}"
        response = await self.client.get(episode_url)
        soup = BeautifulSoup(response.text, "lxml")
        _episode_cont = soup.find("div", class_="episode_cont")
        if not isinstance(_episode_cont, Tag):
            return []

        _chapter_items = _episode_cont.find_all("li")
        chapter_details = [
            ChapterInfo(
                episode_details.find("span", {"class": "subj"}).text,
                chapter_number,
                int(episode_details["data-episode-no"]),
                episode_details.find("a")["href"],
            )
            for chapter_number, episode_details in enumerate(_chapter_items, start=1)
        ]

        return chapter_details[int(start_chapter or 1) - 1 : end_chapter]
