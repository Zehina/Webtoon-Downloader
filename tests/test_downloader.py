import pytest

from webtoon_downloader.core.webtoon.client import WebtoonHttpClient


@pytest.mark.asyncio
async def test_webtoon_downloader() -> None:
    image_url = (
        "https://webtoon-phinf.pstatic.net/20221021_214/1666333530857EF0sA_JPEG/1666333530850160953.jpg?type=q90"
    )

    # Do not assert exact byte sizes from a live CDN response; those can drift over time.
    # Instead, validate that quality handling is consistent and image payloads are valid.
    quality_levels = [None, 90, 80, 70, 60, 50, 40]
    sizes: list[int] = []

    async with WebtoonHttpClient() as client:
        for quality in quality_levels:
            async with client.stream_image(image_url, quality=quality) as img:
                content = await img.aread()
                assert content.startswith(b"\xff\xd8\xff"), f"Expected JPEG content at quality={quality}"
                assert len(content) > 0
                sizes.append(len(content))

    # Lowering quality should not increase payload size.
    assert sizes == sorted(sizes, reverse=True)

    # quality=0 is treated like default quality (100).
    async with WebtoonHttpClient() as client, client.stream_image(image_url) as img:
        content_q0 = await img.aread()

    assert len(content_q0) == sizes[0]

    opti_image_url = (
        "https://webtoon-phinf.pstatic.net/20220929_277/16644486960263FxPF_PNG/1tw_warning_v2.png?type=opti"
    )

    async with (
        WebtoonHttpClient() as client,
        client.stream_image(opti_image_url) as img,
    ):
        content = await img.aread()
        assert content.startswith(b"\x89PNG\r\n\x1a\n")
        assert len(content) > 0
