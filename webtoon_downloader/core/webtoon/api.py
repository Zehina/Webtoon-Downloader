import logging
from dataclasses import dataclass
from typing import Literal

import dacite

from webtoon_downloader.core.webtoon.client import WebtoonHttpClient

log = logging.getLogger(__name__)

WebtoonType = Literal["WEBTOON", "CANVAS"]


@dataclass
class EpisodeInfo:
    episodeNo: int
    thumbnail: str
    episodeTitle: str
    viewerLink: str
    exposureDateMillis: int
    displayUp: bool
    hasBgm: bool | None  # In Canvas this is not defined


@dataclass
class GetEpisodesResponseResult:
    episodeList: list[EpisodeInfo]


@dataclass
class GetEpisodesResponse:
    result: GetEpisodesResponseResult


@dataclass
class WebtoonAPI:
    client: WebtoonHttpClient

    async def get_episodes_data(self, series_api_url: str, page_size: int = 30, cursor: int = 0) -> list[EpisodeInfo]:
        """Returns a list of episode data for a given series ID."""
        # Examples for both webtoon and canvas
        ## https://m.webtoons.com/api/v1/canvas/877457/episodes?pageSize=30
        ## https://m.webtoons.com/api/v1/webtoon/95/episodes?pageSize=30

        url = f"{series_api_url}/episodes?pageSize={page_size}"
        if cursor > 0:
            url = f"{url}&cursor={cursor}"

        resp = dacite.from_dict(data_class=GetEpisodesResponse, data=(await self.client.get(url)).json())
        data = resp.result.episodeList
        log.debug("Received %d episodes", len(data))
        return data
