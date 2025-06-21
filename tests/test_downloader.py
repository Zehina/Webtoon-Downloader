import pytest

from webtoon_downloader.core.webtoon.client import WebtoonHttpClient


@pytest.mark.asyncio
async def test_webtoon_downloader() -> None:
    image_url = "https://webtoon-phinf.pstatic.net/20221021_214/1666333530857EF0sA_JPEG/1666333530850160953.jpg"

    async with WebtoonHttpClient() as client, client.stream("GET", image_url) as resp:
        assert len(await resp.aread()) == 199145
