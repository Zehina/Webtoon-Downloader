import logging
from dataclasses import dataclass

import dacite
import httpx

log = logging.getLogger(__name__)


@dataclass
class EpisodeInfo:
    episodeNo: int
    thumbnail: str
    episodeTitle: str
    viewerLink: str
    exposureDateMillis: int
    displayUp: bool
    hasBgm: bool


@dataclass
class GetEpisodesResponseResult:
    episodeList: list[EpisodeInfo]


@dataclass
class GetEpisodesResponse:
    result: GetEpisodesResponseResult


@dataclass
class WebtoonAPI:
    client: httpx.AsyncClient

    async def get_episode_data(self, series_id: int, page_size: int = 30, cursor: int = 0) -> list[EpisodeInfo]:
        """Returns a list of episode data for a given series ID."""
        url = f"https://m.webtoons.com/api/v1/webtoon/{series_id}/episodes?pageSize={page_size}&cursor={cursor}"
        resp = dacite.from_dict(data_class=GetEpisodesResponse, data=(await self.client.get(url)).json())
        data = resp.result.episodeList
        log.debug("Received %d episodes", len(data))
        return data


if __name__ == "__main__":
    import asyncio

    async def main():
        api = WebtoonAPI(httpx.AsyncClient())
        await api.get_episode_data(95, page_size=99999)

    asyncio.run(main())
