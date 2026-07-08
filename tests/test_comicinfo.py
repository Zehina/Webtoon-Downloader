from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from webtoon_downloader.core.downloaders.image import ImageDownloadResult
from webtoon_downloader.core.webtoon.api import (
    REQUEST_ALL_EPISODES_PAGE_SIZE,
)
from webtoon_downloader.core.webtoon.client import WebtoonHttpClient
from webtoon_downloader.core.webtoon.comicinfo import ComicInfoMetadata, SeriesMetadata, build_comicinfo_xml
from webtoon_downloader.core.webtoon.downloaders.chapter import ChapterDownloader
from webtoon_downloader.core.webtoon.downloaders.comic import WebtoonDownloader
from webtoon_downloader.core.webtoon.fetchers import (
    END_CHAPTER_LATEST,
    WebtoonFetcher,
)
from webtoon_downloader.core.webtoon.models import ChapterInfo
from webtoon_downloader.core.webtoon.namer import NonSeparateFileNameGenerator
from webtoon_downloader.storage import AioWriter, AioZipWriter
from webtoon_downloader.storage.exceptions import StreamWriteError

FORCED_COMICINFO_FAILURE = "forced comicinfo write failure"


class DummyClient(WebtoonHttpClient):
    def __init__(self, responses: dict[str, httpx.Response]):
        self.responses = responses

    async def get(self, url: str) -> httpx.Response:
        if url not in self.responses:
            raise AssertionError
        return self.responses[url]


class DummyImageDownloader:
    async def run(
        self,
        url: str,
        target: str,
        storage: AioWriter,
        quality: int | None = 100,
    ) -> ImageDownloadResult:
        del url, quality

        async def _stream() -> AsyncIterator[bytes]:
            yield b"fake-image-bytes"

        size = await storage.write(_stream(), target)
        return ImageDownloadResult(name=target, size=size)


class FailingComicInfoZipWriter(AioZipWriter):
    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:
        if item_name == "ComicInfo.xml":
            raise StreamWriteError(FORCED_COMICINFO_FAILURE)
        return await super().write(stream, item_name)


def _make_response(url: str, *, text: str = "", json: dict | None = None) -> httpx.Response:
    if json is not None:
        return httpx.Response(200, json=json, request=httpx.Request("GET", url))
    return httpx.Response(200, text=text, request=httpx.Request("GET", url))


def test_build_comicinfo_xml_minimal() -> None:
    xml = build_comicinfo_xml(ComicInfoMetadata(series="Tower of God"))
    text = xml.decode("utf-8")

    assert text.startswith("<?xml version='1.0' encoding='utf-8'?>")
    assert "<Series>Tower of God</Series>" in text
    assert "<Writer>" not in text


def test_build_comicinfo_xml_omits_empty_values() -> None:
    xml = build_comicinfo_xml(
        ComicInfoMetadata(
            series="Tower of God",
            writer="",
            summary=None,
            genre="Fantasy",
        )
    )
    text = xml.decode("utf-8")

    assert "<Genre>Fantasy</Genre>" in text
    assert "<Writer>" not in text
    assert "<Summary>" not in text


def test_build_comicinfo_xml_special_chars_and_roundtrip() -> None:
    xml = build_comicinfo_xml(
        ComicInfoMetadata(
            series="Tom & Jerry <Classic>",
            title='A "quote" & <tag>',
            summary="Que désirez-vous?",
            number="1",
            writer="A & B",
        )
    )
    text = xml.decode("utf-8")

    assert "Tom &amp; Jerry &lt;Classic&gt;" in text
    assert '<Title>A "quote" &amp; &lt;tag&gt;</Title>' in text
    parsed = ET.fromstring(xml)  # noqa: S314
    assert parsed.findtext("Series") == "Tom & Jerry <Classic>"
    assert parsed.findtext("Summary") == "Que désirez-vous?"


@pytest.mark.asyncio
async def test_canvas_chapters_use_reading_language() -> None:
    url = "https://www.webtoons.com/en/canvas/frog-wizards-of-chana-tower/list?title_no=883187"
    mobile_url = "https://m.webtoons.com/en/canvas/frog-wizards-of-chana-tower/list?title_no=883187"
    api_url = (
        "https://m.webtoons.com/api/v1/canvas/883187/episodes"
        f"?pageSize={REQUEST_ALL_EPISODES_PAGE_SIZE}&readingLanguageCode=en"
    )

    main_html = """
    <html><head>
      <link rel='canonical' href='https://www.webtoons.com/en/canvas/frog-wizards-of-chana-tower/list?title_no=883187' />
    </head><body>
      <strong class='subject'>Frog Wizards of Chana Tower</strong>
    </body></html>
    """
    episodes_json = {
        "result": {
            "episodeList": [
                {
                    "episodeNo": 1,
                    "thumbnail": "",
                    "episodeTitle": "First",
                    "viewerLink": "/en/canvas/frog-wizards-of-chana-tower/first/viewer?title_no=883187&episode_no=1",
                    "exposureDateMillis": 0,
                    "displayUp": True,
                }
            ],
        }
    }

    fetcher = WebtoonFetcher(
        client=DummyClient({
            mobile_url: _make_response(mobile_url, text=main_html),
            api_url: _make_response(api_url, json=episodes_json),
        }),
        series_url=url,
    )

    chapters = await fetcher.get_chapters_details(url)

    assert [chapter.title for chapter in chapters] == ["First"]
    assert chapters[0].viewer_url == (
        "https://www.webtoons.com/en/canvas/frog-wizards-of-chana-tower/first/viewer?title_no=883187&episode_no=1"
    )


@pytest.mark.asyncio
async def test_canvas_latest_uses_single_episode_list_request() -> None:
    url = "https://www.webtoons.com/en/canvas/frog-wizards-of-chana-tower/list?title_no=883187"
    mobile_url = "https://m.webtoons.com/en/canvas/frog-wizards-of-chana-tower/list?title_no=883187"
    api_url = (
        "https://m.webtoons.com/api/v1/canvas/883187/episodes"
        f"?pageSize={REQUEST_ALL_EPISODES_PAGE_SIZE}&readingLanguageCode=en"
    )
    main_html = """
    <html><head>
      <link rel='canonical' href='https://www.webtoons.com/en/canvas/frog-wizards-of-chana-tower/list?title_no=883187' />
    </head><body>
      <strong class='subject'>Frog Wizards of Chana Tower</strong>
    </body></html>
    """
    episodes_json = {
        "result": {
            "episodeList": [
                {
                    "episodeNo": 1,
                    "thumbnail": "",
                    "episodeTitle": "First",
                    "viewerLink": "/en/canvas/frog-wizards-of-chana-tower/first/viewer?title_no=883187&episode_no=1",
                    "exposureDateMillis": 0,
                    "displayUp": True,
                },
                {
                    "episodeNo": 2,
                    "thumbnail": "",
                    "episodeTitle": "Second",
                    "viewerLink": "/en/canvas/frog-wizards-of-chana-tower/second/viewer?title_no=883187&episode_no=2",
                    "exposureDateMillis": 0,
                    "displayUp": True,
                },
            ],
        }
    }
    fetcher = WebtoonFetcher(
        client=DummyClient({
            mobile_url: _make_response(mobile_url, text=main_html),
            api_url: _make_response(api_url, json=episodes_json),
        }),
        series_url=url,
    )

    chapters = await fetcher.get_chapters_details(url, end_chapter=END_CHAPTER_LATEST)

    assert [chapter.title for chapter in chapters] == ["Second"]
    assert chapters[0].number == 2
    assert chapters[0].total_chapters == 2


@pytest.mark.asyncio
async def test_chapter_downloader_writes_comicinfo_to_cbz() -> None:
    viewer_url = "https://www.webtoons.com/en/fantasy/tower-of-god/viewer?title_no=95&episode_no=1"
    viewer_html = """
    <html><body>
      <div class='viewer_img _img_viewer_area'>
        <img data-url='https://img/1.jpg?type=q90' />
        <img data-url='https://img/2.jpg?type=q90' />
      </div>
      <div class='author_text'>Some notes</div>
    </body></html>
    """

    client = DummyClient({viewer_url: _make_response(viewer_url, text=viewer_html)})
    downloader = ChapterDownloader(
        client=client,
        image_downloader=DummyImageDownloader(),
        file_name_generator=NonSeparateFileNameGenerator(),
        concurrent_downloads_limit=1,
    )

    chapter = ChapterInfo(
        number=1,
        viewer_url=viewer_url,
        data_episode_no=1,
        title="Ep. 1",
        series_title="Tower of God",
        total_chapters=2,
    )

    series_metadata = SeriesMetadata(
        title="Tower of God",
        summary="Summary",
        author="SIU",
        genre="Fantasy",
        language="en",
        url="https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
    )

    container = io.BytesIO()
    await downloader.run(chapter, Path("unused"), AioZipWriter(container), series_metadata=series_metadata)

    container.seek(0)
    with zipfile.ZipFile(container, "r") as zf:
        names = zf.namelist()
        assert "1_1.jpg" in names
        assert "1_2.jpg" in names
        assert "ComicInfo.xml" in names

        comicinfo = zf.read("ComicInfo.xml").decode("utf-8")
        assert "<Series>Tower of God</Series>" in comicinfo
        assert "<Title>Ep. 1</Title>" in comicinfo
        assert "<PageCount>2</PageCount>" in comicinfo
        assert "<Manga>No</Manga>" in comicinfo


@pytest.mark.asyncio
async def test_chapter_downloader_without_series_metadata_does_not_write_comicinfo() -> None:
    viewer_url = "https://www.webtoons.com/en/fantasy/tower-of-god/viewer?title_no=95&episode_no=1"
    viewer_html = """
    <html><body>
      <div class='viewer_img _img_viewer_area'>
        <img data-url='https://img/1.jpg?type=q90' />
      </div>
    </body></html>
    """

    client = DummyClient({viewer_url: _make_response(viewer_url, text=viewer_html)})
    downloader = ChapterDownloader(
        client=client,
        image_downloader=DummyImageDownloader(),
        file_name_generator=NonSeparateFileNameGenerator(),
        concurrent_downloads_limit=1,
    )
    chapter = ChapterInfo(
        number=1,
        viewer_url=viewer_url,
        data_episode_no=1,
        title="Ep. 1",
        series_title="Tower of God",
        total_chapters=1,
    )

    container = io.BytesIO()
    await downloader.run(chapter, Path("unused"), AioZipWriter(container), series_metadata=None)

    container.seek(0)
    with zipfile.ZipFile(container, "r") as zf:
        assert "ComicInfo.xml" not in zf.namelist()


@pytest.mark.asyncio
async def test_chapter_downloader_logs_warning_if_comicinfo_write_fails(caplog: pytest.LogCaptureFixture) -> None:
    viewer_url = "https://www.webtoons.com/en/fantasy/tower-of-god/viewer?title_no=95&episode_no=1"
    viewer_html = """
    <html><body>
      <div class='viewer_img _img_viewer_area'>
        <img data-url='https://img/1.jpg?type=q90' />
      </div>
    </body></html>
    """
    client = DummyClient({viewer_url: _make_response(viewer_url, text=viewer_html)})
    downloader = ChapterDownloader(
        client=client,
        image_downloader=DummyImageDownloader(),
        file_name_generator=NonSeparateFileNameGenerator(),
        concurrent_downloads_limit=1,
    )
    chapter = ChapterInfo(
        number=1,
        viewer_url=viewer_url,
        data_episode_no=1,
        title="Ep. 1",
        series_title="Tower of God",
        total_chapters=1,
    )
    series_metadata = SeriesMetadata(title="Tower of God")

    caplog.set_level("WARNING")
    container = io.BytesIO()
    await downloader.run(chapter, Path("unused"), FailingComicInfoZipWriter(container), series_metadata=series_metadata)

    warning_messages = [record.getMessage() for record in caplog.records if record.levelname == "WARNING"]
    assert any("ComicInfo: failed to write ComicInfo.xml to CBZ archive" in msg for msg in warning_messages)


@pytest.mark.asyncio
async def test_webtoon_downloader_cbz_includes_series_metadata(tmp_path: Path) -> None:
    url = "https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95"
    mobile_url = "https://m.webtoons.com/en/fantasy/tower-of-god/list?title_no=95"
    api_url = (
        "https://m.webtoons.com/api/v1/webtoon/95/episodes"
        f"?pageSize={REQUEST_ALL_EPISODES_PAGE_SIZE}&readingLanguageCode=en"
    )
    viewer_url = "https://www.webtoons.com/en/fantasy/tower-of-god/ep-1/viewer?title_no=95&episode_no=1"

    main_html = """
    <html><head>
      <meta property='com-linewebtoon:webtoon:author' content='SIU' />
      <link rel='canonical' href='https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95' />
    </head><body>
      <strong class='subject'>Tower of God</strong>
      <h2 class='genre g_fantasy'>Fantasy</h2>
      <p class='summary'>Main summary text</p>
    </body></html>
    """

    viewer_html = """
    <html><body>
      <div class='viewer_img _img_viewer_area'>
        <img data-url='https://img/1.jpg?type=q90' />
      </div>
      <div class='author_text'>Viewer notes</div>
    </body></html>
    """

    episodes_json = {
        "result": {
            "episodeList": [
                {
                    "episodeNo": 1,
                    "thumbnail": "",
                    "episodeTitle": "Ep. 1",
                    "viewerLink": "/en/fantasy/tower-of-god/ep-1/viewer?title_no=95&episode_no=1",
                    "exposureDateMillis": 0,
                    "displayUp": True,
                    "hasBgm": False,
                }
            ]
        }
    }

    responses = {
        mobile_url: _make_response(mobile_url, text=main_html),
        api_url: _make_response(api_url, json=episodes_json),
        url: _make_response(url, text=main_html),
        viewer_url: _make_response(viewer_url, text=viewer_html),
    }

    client = DummyClient(responses)
    chapter_downloader = ChapterDownloader(
        client=client,
        image_downloader=DummyImageDownloader(),
        file_name_generator=NonSeparateFileNameGenerator(),
        concurrent_downloads_limit=1,
    )

    downloader = WebtoonDownloader(
        url=url,
        client=client,
        chapter_downloader=chapter_downloader,
        storage_type="cbz",
        quality=100,
        directory=str(tmp_path),
    )

    await downloader.run()

    archive = tmp_path / "1.cbz"
    assert archive.exists()
    with zipfile.ZipFile(archive, "r") as zf:
        comicinfo = zf.read("ComicInfo.xml").decode("utf-8")
        assert "<Series>Tower of God</Series>" in comicinfo
        assert "<Writer>SIU</Writer>" in comicinfo
        assert "<Genre>Fantasy</Genre>" in comicinfo
        assert "<LanguageISO>en</LanguageISO>" in comicinfo
        assert "<Summary>Main summary text</Summary>" in comicinfo
