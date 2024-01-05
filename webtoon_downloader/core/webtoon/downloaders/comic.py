from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Literal

import httpx

from webtoon_downloader.core import file as fileutil
from webtoon_downloader.core import webtoon
from webtoon_downloader.core.downloaders.image import ImageDownloader
from webtoon_downloader.core.webtoon.downloaders.callbacks import OnWebtoonFetchCallback
from webtoon_downloader.core.webtoon.downloaders.chapter import ChapterDownloader
from webtoon_downloader.core.webtoon.downloaders.options import StorageType, WebtoonDownloadOptions
from webtoon_downloader.core.webtoon.downloaders.result import DownloadResult
from webtoon_downloader.core.webtoon.exporter import DataExporter
from webtoon_downloader.core.webtoon.extractor import WebtoonMainPageExtractor
from webtoon_downloader.core.webtoon.fetchers import WebtoonFetcher
from webtoon_downloader.core.webtoon.models import ChapterInfo
from webtoon_downloader.core.webtoon.namer import NonSeparateFileNameGenerator, SeparateFileNameGenerator
from webtoon_downloader.storage import AioFolderWriter, AioPdfWriter, AioWriter, AioZipWriter
from webtoon_downloader.transformers.image import AioImageFormatTransformer

log = logging.getLogger(__name__)

DEFAULT_CHAPTER_LIMIT = 8
"""Default number of asynchronous workers. More == More likely to get server rate limited"""


@dataclass
class WebtoonDownloader:
    """
    Facilitates the downloading of Webtoon chapters.

    Manages the entire process of downloading multiple chapters from a Webtoon series, including fetching chapter details, setting up storage, and handling concurrency.

    Attributes:
        url                  : URL of the Webtoon series to download.
        chapter_downloader   : The downloader responsible for individual chapters.
        storage_type         : The type of storage to use for the downloaded chapters.
        start_chapter        : The first chapter to download.
        end_chapter          : The last chapter to download.
        concurrent_chapters  : The number of chapters to download concurrently.
        directory            : The directory where the downloaded chapters will be stored.
        exporter             : Optional data exporter for exporting series details.
        on_webtoon_fetched   : Optional callback executed after fetching Webtoon information.
    """

    url: str
    chapter_downloader: ChapterDownloader
    storage_type: StorageType

    start_chapter: int | None = None
    end_chapter: int | None | Literal["latest"] = None
    concurrent_chapters: int = DEFAULT_CHAPTER_LIMIT
    directory: str | PathLike[str] | None = None
    exporter: DataExporter | None = None
    on_webtoon_fetched: OnWebtoonFetchCallback | None = None

    _directory: Path = field(init=False)

    async def run(self) -> list[DownloadResult]:
        """
        Asynchronously downloads chapters from a Webtoon series.

        Orchestrates the downloading process by initializing the client, fetching chapter details, setting up storage, and managing concurrent downloads.

        Returns:
            A list containing download results for each chapter.
        """
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
        """
        Fetches chapter information for the specified Webtoon series.

        Args:
            client: The HTTP client used for making web requests.

        Returns:
            A list of `ChapterInfo` objects containing information about each chapter.
        """
        fetcher = WebtoonFetcher(client)
        chapters = await fetcher.get_chapters_details(self.url, self.start_chapter, self.end_chapter)
        if self.on_webtoon_fetched:
            await self.on_webtoon_fetched(chapters)

        return chapters

    def _create_task(self, chapter_info: ChapterInfo, semaphore: asyncio.Semaphore) -> asyncio.Task:
        """
        Creates an asynchronous task for downloading a Webtoon chapter.

        Args:
            chapter_info    : Information about the specific chapter to download.
            semaphore       : The semaphore to attach to the task to limit concurrent downloads.

        Returns:
            An asyncio Task object for downloading the chapter.
        """

        async def task() -> list[DownloadResult]:
            async with semaphore:
                storage = await self._get_storage(chapter_info)
                return await self.chapter_downloader.run(chapter_info, self._directory, storage)

        return asyncio.create_task(task())

    async def _get_storage(self, chapter_info: ChapterInfo) -> AioWriter:
        """
        Determines the appropriate storage writer based on the specified storage type.

        Args:
            chapter_info: Information about the chapter for which storage is being set up.

        Returns:
            An instance of a storage writer (`AioWriter` subclass) appropriate for the storage type.
        """
        dest = f"{chapter_info.number:0{len(str(chapter_info.total_chapters))}d}"
        if self.storage_type in ["zip", "cbz"]:
            return AioZipWriter(self._directory / f"{dest}.{self.storage_type}")
        elif self.storage_type == "pdf":
            return AioPdfWriter(self._directory / f"{dest}.pdf")
        else:
            return AioFolderWriter(self._directory)

    async def _export_data(self, extractor: WebtoonMainPageExtractor) -> None:
        """
        Exports series summary data if an exporter is set.

        Args:
            extractor: The extractor used to obtain the series summary.
        """
        if not self.exporter:
            return
        await self.exporter.add_series_summary(extractor.get_series_summary(), self._directory / "summary.txt")


async def download_webtoon(opts: WebtoonDownloadOptions) -> list[DownloadResult]:
    """
    Asynchronously downloads chapters of a given Webtoon based on the provided options.

    Args:
        opts: Options for downloading the Webtoon.

    Returns:
        A list of download results for each chapter.
    """
    file_name_generator = (
        SeparateFileNameGenerator(use_chapter_title_directories=True)
        if opts.separate
        else NonSeparateFileNameGenerator()
    )
    image_downloader = ImageDownloader(
        client=webtoon.client.new_image_client(),
        transformers=[AioImageFormatTransformer(opts.image_format)],
    )

    exporter = DataExporter(opts.exporter_format) if opts.export_metadata else None
    chapter_downloader = ChapterDownloader(
        client=webtoon.client.new(),
        exporter=exporter,
        progress_callback=opts.chapter_progress_callback,
        image_downloader=image_downloader,
        file_name_generator=file_name_generator,
    )

    end: int | None | Literal["latest"]
    if opts.latest:
        start, end = None, "latest"
    else:
        start, end = opts.start, opts.end

    downloader = WebtoonDownloader(
        url=opts.url,
        directory=opts.destination,
        start_chapter=start,
        end_chapter=end,
        chapter_downloader=chapter_downloader,
        storage_type=opts.save_as,
        exporter=exporter,
        on_webtoon_fetched=opts.on_webtoon_fetched,
    )

    return await downloader.run()
