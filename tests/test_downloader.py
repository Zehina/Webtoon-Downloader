import pytest

from webtoon_downloader.core.webtoon.client import WebtoonHttpClient


@pytest.mark.asyncio
async def test_webtoon_downloader() -> None:
    # We expect that even if the url contains a quality parameter, it will be ignored
    image_url = (
        "https://webtoon-phinf.pstatic.net/20221021_214/1666333530857EF0sA_JPEG/1666333530850160953.jpg?type=q90"
    )

    quality_expectations = [
        (None, 199145),  # Default quality (100)
        (90, 119596),
        (80, 83213),
        (70, 74114),
        (60, 60779),
        (50, 54285),
        (40, 51454),  # 40 seems to be the lowest quality available
        (0, 199145),  # Invalid quality, server should ignore
    ]

    async with WebtoonHttpClient() as client:
        for quality, expected_size in quality_expectations:
            async with client.stream_image(image_url, quality=quality) as img:
                content = await img.aread()
                assert len(content) == expected_size, f"Mismatch at quality={quality}"

    opti_image_url = (
        "https://webtoon-phinf.pstatic.net/20220929_277/16644486960263FxPF_PNG/1tw_warning_v2.png?type=opti"
    )

    async with WebtoonHttpClient() as client, client.stream_image(opti_image_url) as img:
        content = await img.aread()
        assert len(content) == 18102
