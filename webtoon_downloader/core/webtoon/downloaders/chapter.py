from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path

import httpx

from webtoon_downloader.core.downloaders.image import ImageDownloader, ImageDownloadResult
from webtoon_downloader.core.exceptions import ChapterDownloadError, RateLimitedError
from webtoon_downloader.core.webtoon.client import WebtoonHttpClient
from webtoon_downloader.core.webtoon.downloaders.callbacks import ChapterProgressCallback, ChapterProgressType
from webtoon_downloader.core.webtoon.downloaders.result import DownloadResult
from webtoon_downloader.core.webtoon.exporter import DataExporter
from webtoon_downloader.core.webtoon.extractor import WebtoonViewerPageExtractor
from webtoon_downloader.core.webtoon.models import ChapterInfo, PageInfo
from webtoon_downloader.core.webtoon.namer import FileNameGenerator
from webtoon_downloader.storage import AioWriter

log = logging.getLogger(__name__)


@dataclass
class ChapterDownloader:
    """
    Downloads chapters from a Webtoon.

    Attributes:
        client                      : HTTP client for making web requests.
        image_downloader            : Downloader for Webtoon images.
        file_name_generator         : Generator for file names based on chapter and page details.
        concurrent_downloads_limit  : The number of chapters to download concurrently.
        exporter                    : Optional data exporter for exporting chapter details.
        progress_callback           : Optional callback for reporting chapter download progress.
    """

    client: WebtoonHttpClient
    image_downloader: ImageDownloader
    file_name_generator: FileNameGenerator
    concurrent_downloads_limit: int

    exporter: DataExporter | None = None
    progress_callback: ChapterProgressCallback | None = None

    _semaphore: asyncio.Semaphore = field(init=False)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.concurrent_downloads_limit)

    async def run(
        self, chapter_info: ChapterInfo, directory: str | PathLike[str], storage: AioWriter
    ) -> list[DownloadResult]:
        """
        Asynchronously downloads a single chapter by downaloding all its pages.

        Args:
            chapter_info    : Information about the chapter to download.
            directory       : The directory to save downloaded images and texts.
            storage         : The storage writer to use for saving images.

        Returns:
            A list of download results.

        Raises:
            ChapterDownloadError in case of error downloading the chapter.
        """
        try:
            async with self._semaphore:
                return await self._run(chapter_info, directory, storage)
        except ChapterDownloadError:
            raise
        except Exception as exc:
            raise ChapterDownloadError(chapter_info.viewer_url, exc, chapter_info=chapter_info) from exc

    async def _run(
        self, chapter_info: ChapterInfo, directory: str | PathLike[str], storage: AioWriter
    ) -> list[DownloadResult]:
        """Internal method to handle the download logic for a Webtoon chapter."""
        tasks: list[asyncio.Task] = []
        await self._report_progress(chapter_info, "Start")

        resp = await self.client.get(chapter_info.viewer_url)
        try:
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            cause = None
            if resp.status_code == 429:
                cause = RateLimitedError(f"Rate limitied while fetching chapter info from {chapter_info.viewer_url}")
            raise ChapterDownloadError(
                chapter_info.viewer_url,
                message=f"Failed to fetch url {chapter_info.viewer_url}: status code [{resp.status_code}]",
                chapter_info=chapter_info,
                cause=cause,
            ) from exc

        log.debug(
            'Fetched: "%s" from chapter "%s" => %s', chapter_info.viewer_url, chapter_info.title, resp.status_code
        )
        extractor = WebtoonViewerPageExtractor(resp.text)
        img_urls = extractor.get_img_urls()
        if not img_urls:
            raise ChapterDownloadError(
                chapter_info.viewer_url,
                None,
                f'No images found in chapter "{chapter_info.title}"',
                chapter_info=chapter_info,
            )

        await self._report_progress(chapter_info, "ChapterInfoFetched", extractor)

        chapter_directory = self.file_name_generator.get_chapter_directory(chapter_info)  # pylint: disable=assignment-from-no-return
        export_dir = directory / chapter_directory
        await self._export_data(extractor, chapter_info, export_dir)

        async with storage:
            for n, url in enumerate(img_urls, start=1):
                page = PageInfo(n, url, len(img_urls), chapter_info)
                name = str(chapter_directory / self.file_name_generator.get_page_filename(page))
                tasks.append(self._create_task(chapter_info, url, name, storage))
            res = await asyncio.gather(*tasks, return_exceptions=False)

        await self._report_progress(chapter_info, "Completed")
        return res

    def _create_task(self, chapter_info: ChapterInfo, url: str, name: str, storage: AioWriter) -> asyncio.Task:
        """
        Creates an asynchronous task for downloading a single page of a Webtoon chapter.

        Args:
            chapter_info    : Information about the chapter.
            url             : URL of the image to download.
            name            : The name to save the image as.
            storage         : The storage writer for saving the image.

        Returns:
            An asyncio Task for downloading the image.
        """

        async def _task() -> ImageDownloadResult:
            log.debug('Downloading: "%s" from "%s" from chapter "%s"', name, url, chapter_info.viewer_url)
            res = await self.image_downloader.run(url, name, storage)
            log.debug('Finished downloading: "%s" from "%s" from chapter URL: "%s"', name, url, chapter_info.viewer_url)
            await self._report_progress(chapter_info, "PageCompleted")
            return res

        return asyncio.create_task(_task())

    async def _report_progress(
        self,
        chapter_info: ChapterInfo,
        progress_type: ChapterProgressType,
        extractor: WebtoonViewerPageExtractor | None = None,
    ) -> None:
        """
        Reports the progress of the chapter download if a progress callback is provided.

        Args:
            chapter_info    : Information about the chapter.
            progress_type   : The type of progress being reported.
            extractor       : The extractor used for the current progress step, if applicable.
        """
        if not self.progress_callback:
            return
        await self.progress_callback(chapter_info, progress_type, extractor)

    async def _export_data(
        self,
        extractor: WebtoonViewerPageExtractor,
        chapter_info: ChapterInfo,
        directory: Path,
    ) -> None:
        """
        Exports the chapter details if an exporter is provided.

        Args:
            extractor       : The extractor used for obtaining chapter details.
            chapter_info    : Information about the chapter.
            directory       : Directory to save the exported data.
        """
        if not self.exporter:
            return

        await self.exporter.add_chapter_details(
            chapter=chapter_info,
            title_path=directory / self.file_name_generator.get_title_filename(chapter_info),
            notes_path=directory / self.file_name_generator.get_title_filename(chapter_info),
            notes=extractor.get_chapter_notes(),
        )
