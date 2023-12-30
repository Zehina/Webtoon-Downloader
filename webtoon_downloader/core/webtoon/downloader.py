from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Awaitable, Callable, Literal, Sequence, Union

import httpx
from typing_extensions import TypeAlias

from webtoon_downloader.core import file as fileutil
from webtoon_downloader.core import webtoon
from webtoon_downloader.core.downloaders.image import ImageDownloader, ImageDownloadResult
from webtoon_downloader.core.exceptions import ChapterDownloadError
from webtoon_downloader.core.webtoon.exporter import DataExporter, DataExporterFormat
from webtoon_downloader.core.webtoon.extractor import (
    WebtoonMainPageExtractor,
    WebtoonViewerPageExtractor,
)
from webtoon_downloader.core.webtoon.fetchers import WebtoonFetcher
from webtoon_downloader.core.webtoon.models import ChapterInfo, PageInfo
from webtoon_downloader.core.webtoon.namer import (
    FileNameGenerator,
    NonSeparateFileNameGenerator,
    SeparateFileNameGenerator,
)
from webtoon_downloader.storage import AioFolderWriter, AioPdfWriter, AioWriter, AioZipWriter
from webtoon_downloader.transformers.image import AioImageFormatTransformer, ImageFormat

log = logging.getLogger(__name__)

DEFAULT_CHAPTER_LIMIT = 8
"""Default number of asynchronous workers. More == More likely to get server rate limited"""

OnWebtoonFetchCallback: TypeAlias = Callable[[Sequence[ChapterInfo]], Awaitable[None]]
"""
Progress callback called for each chapter download.
"""

ChapterProgressType: TypeAlias = Literal["Start", "ChapterInfoFetched", "PageCompleted", "Completed"]
"""
Type of progress being reported.
"""

ChapterProgressCallback: TypeAlias = Callable[
    [ChapterInfo, ChapterProgressType, Union[WebtoonViewerPageExtractor, None]], Awaitable[None]
]
"""
Progress callback called for each chapter download. Takes the chapter info and progress type
"""

PageProgressCallback: TypeAlias = Callable[[PageInfo], Awaitable[None]]
"""
Progress callback called for each page download. Takes the page info.
"""

DownloadResult: TypeAlias = Union[str, Path]
"""Type reprensentation the download result which can either be represented as a string or Path object"""

StorageType: TypeAlias = Literal["images", "zip", "cbz", "pdf"]
"""Valid option for storing the downloaded images."""


@dataclass
class WebtoonDownloadOptions:
    start: int
    end: int | None
    destination: str | None = None

    export_texts: bool = False
    exporter_format: DataExporterFormat = "json"

    separate: bool = True
    save_as: StorageType = "images"
    image_format: ImageFormat = "JPG"

    chapter_progress_callback: ChapterProgressCallback | None = None
    on_webtoon_fetched: OnWebtoonFetchCallback | None = None


async def _get_storage(
    directory: str | PathLike[str],
    storage_type: StorageType,
    chapter_info: ChapterInfo,
) -> AioWriter:
    _dir = Path(directory)
    dest = f"{chapter_info.number:0{len(str(chapter_info.total_chapters))}d}"
    if storage_type in ["zip", "cbz"]:
        return AioZipWriter(_dir / f"{dest}.{storage_type}")
    elif storage_type == "pdf":
        return AioPdfWriter(_dir / f"{dest}.pdf")
    else:
        return AioFolderWriter(_dir)


@dataclass
class ChapterDownloader:
    client: httpx.AsyncClient
    image_downloader: ImageDownloader
    file_name_generator: FileNameGenerator

    exporter: DataExporter | None = None
    progress_callback: ChapterProgressCallback | None = None

    async def run(
        self, chapter_info: ChapterInfo, directory: str | PathLike[str], storage: AioWriter
    ) -> list[DownloadResult | BaseException]:
        try:
            await self._report_progress(chapter_info, "Start")
            tasks: list[asyncio.Task] = []
            resp = await self.client.get(chapter_info.viewer_url)
            extractor = WebtoonViewerPageExtractor(resp.text)
            await self._report_progress(chapter_info, "ChapterInfoFetched", extractor)
            img_urls = extractor.get_img_urls()

            chapter_directory = self.file_name_generator.get_chapter_directory(chapter_info)  # pylint: disable=assignment-from-no-return
            export_dir = directory / chapter_directory
            await self._export_data(extractor, chapter_info, export_dir)

            async with storage:
                n_urls = len(img_urls)
                for n, url in enumerate(img_urls, start=1):
                    page = PageInfo(n, url, n_urls, chapter_info)
                    name = str(chapter_directory / self.file_name_generator.get_page_filename(page))
                    tasks.append(self._create_task(chapter_info, url, name, storage))
                res = await asyncio.gather(*tasks, return_exceptions=False)
            await self._report_progress(chapter_info, "Completed")
            return res
        except Exception as exc:
            raise ChapterDownloadError(chapter_info.viewer_url, exc, chapter_info=chapter_info) from exc

    def _create_task(self, chapter_info: ChapterInfo, url: str, name: str, storage: AioWriter) -> asyncio.Task:
        async def task() -> ImageDownloadResult:
            res = await self.image_downloader.run(url, name, storage)
            await self._report_progress(chapter_info, "PageCompleted")
            return res

        return asyncio.create_task(task())

    async def _report_progress(
        self,
        chapter_info: ChapterInfo,
        progress_type: ChapterProgressType,
        extractor: WebtoonViewerPageExtractor | None = None,
    ) -> None:
        if not self.progress_callback:
            return
        await self.progress_callback(chapter_info, progress_type, extractor)

    async def _export_data(
        self,
        extractor: WebtoonViewerPageExtractor,
        chapter_info: ChapterInfo,
        directory: Path,
    ) -> None:
        if not self.exporter:
            return

        await self.exporter.add_chapter_details(
            chapter=chapter_info,
            title_path=directory / self.file_name_generator.get_title_filename(chapter_info),
            notes_path=directory / self.file_name_generator.get_title_filename(chapter_info),
            notes=extractor.get_chapter_notes(),
        )


@dataclass
class WebtoonDownloader:
    url: str
    start_chapter: int
    chapter_downloader: ChapterDownloader
    storage_type: StorageType

    end_chapter: int | None = None
    concurrent_chapters: int = DEFAULT_CHAPTER_LIMIT
    directory: str | PathLike[str] | None = None
    exporter: DataExporter | None = None
    on_webtoon_fetched: OnWebtoonFetchCallback | None = None

    _directory: Path = field(init=False)

    async def run(self) -> list[DownloadResult]:
        async with webtoon.client.new() as client:
            chapter_list = await self._get_chapters(client)
            resp = await client.get(self.url)
            extractor = WebtoonMainPageExtractor(resp.text)

            if self.directory:
                self._directory = Path(self.directory)
            else:
                self._directory = Path(fileutil.slugify_name(extractor.get_series_title()))

            await self._export_data(extractor)

            # Semaphore to limit the number of concurrent chapter downloads
            semaphore = asyncio.Semaphore(self.concurrent_chapters)
            tasks = []
            for chapter_info in chapter_list:
                task = self._create_task(chapter_info, semaphore)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=False)
            if self.exporter:
                await self.exporter.write_data(self._directory)
            return results

    async def _get_chapters(self, client: httpx.AsyncClient) -> list[ChapterInfo]:
        fetcher = WebtoonFetcher(client)
        chapters = await fetcher.get_chapters_details(self.url, self.start_chapter, self.end_chapter)
        if self.on_webtoon_fetched:
            await self.on_webtoon_fetched(chapters)
        return chapters

    def _create_task(self, chapter_info: ChapterInfo, semaphore: asyncio.Semaphore) -> asyncio.Task:
        async def task() -> list[DownloadResult | BaseException]:
            async with semaphore:
                storage = await _get_storage(self._directory, self.storage_type, chapter_info)
                return await self.chapter_downloader.run(chapter_info, self._directory, storage)

        return asyncio.create_task(task())

    async def _export_data(self, extractor: WebtoonMainPageExtractor) -> None:
        if not self.exporter:
            return
        await self.exporter.add_series_summary(extractor.get_series_summary(), self._directory / "summary.txt")


async def download_webtoon(opts: WebtoonDownloadOptions) -> list[DownloadResult]:
    """Asynchronously downloads chapters of a given Webtoon based on the provided options"""
    file_name_generator = (
        SeparateFileNameGenerator(use_chapter_title_directories=True)
        if opts.separate
        else NonSeparateFileNameGenerator()
    )
    image_downloader = ImageDownloader(
        client=webtoon.client.new_image_client(),
        transformers=[AioImageFormatTransformer(opts.image_format)],
    )

    exporter = DataExporter(opts.exporter_format) if opts.export_texts else None
    chapter_downloader = ChapterDownloader(
        client=webtoon.client.new(),
        exporter=exporter,
        progress_callback=opts.chapter_progress_callback,
        image_downloader=image_downloader,
        file_name_generator=file_name_generator,
    )
    downloader = WebtoonDownloader(
        url="https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
        directory=opts.destination,
        start_chapter=opts.start,
        end_chapter=opts.end,
        chapter_downloader=chapter_downloader,
        storage_type=opts.save_as,
        exporter=exporter,
        on_webtoon_fetched=opts.on_webtoon_fetched,
    )

    return await downloader.run()
