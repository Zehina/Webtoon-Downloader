from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Awaitable, Callable, Literal, Union

import httpx
from rich import traceback
from rich.pretty import pprint
from typing_extensions import TypeAlias

from webtoon_downloader.core import file as fileutil
from webtoon_downloader.core import webtoon
from webtoon_downloader.core.downloaders.image import ImageDownloader
from webtoon_downloader.core.exceptions import ChapterDownloadError
from webtoon_downloader.core.webtoon.exporter import TextExporter
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
from webtoon_downloader.storage import (
    AioFolderWriter,
    AioPdfWriter,
    AioWriter,
    AioZipWriter,
)
from webtoon_downloader.transformers.image import AioImageFormatTransformer

log = logging.getLogger(__name__)

DEFAULT_CHAPTER_LIMIT = 6

ChapterProgressCallback: TypeAlias = Callable[[int], Awaitable[None]]
"""
Progress callback called for each chapter download.
"""

DownloadResult: TypeAlias = Union[str, Path]
StorageType: TypeAlias = Literal["file", "zip", "cbz", "pdf"]

# FileNameMutator: TypeAlias = Callable[[WebtoonInfo, ChapterInfo, Union[PageInfo, None]], str]


@dataclass
class ChapterDownloader:
    client: httpx.AsyncClient
    image_downloader: ImageDownloader
    file_name_generator: FileNameGenerator

    exporter: TextExporter | None = None
    progress_callback: ChapterProgressCallback | None = None

    async def run(
        self, chapter_info: ChapterInfo, directory: str | PathLike[str], storage: AioWriter
    ) -> list[DownloadResult | BaseException]:
        try:
            tasks: list[asyncio.Task] = []
            resp = await self.client.get(chapter_info.viewer_url)
            extractor = WebtoonViewerPageExtractor(resp.text)
            img_urls = extractor.get_img_urls()

            chapter_directory = self.file_name_generator.get_chapter_directory(chapter_info)  # pylint: disable=assignment-from-no-return
            export_dir = directory / chapter_directory
            await self._export_data(extractor, chapter_info, export_dir, len(str(chapter_info.total_chapters)))

            async with storage:
                n_urls = len(img_urls)
                for n, url in enumerate(img_urls, start=1):
                    page = PageInfo(n, url, n_urls, chapter_info)
                    name = str(chapter_directory / self.file_name_generator.get_page_filename(page))
                    task = asyncio.create_task(self.image_downloader.run(url, name, storage))
                    tasks.append(task)
                res = await asyncio.gather(*tasks, return_exceptions=False)
            if self.progress_callback:
                await self.progress_callback(1)

            return res
        except Exception as exc:
            raise ChapterDownloadError(chapter_info.viewer_url, exc, chapter_info=chapter_info) from exc

    async def _export_data(
        self,
        extractor: WebtoonViewerPageExtractor,
        chapter_info: ChapterInfo,
        directory: str | PathLike[str],
        padding: int,
    ) -> None:
        if not self.exporter:
            return
        await self.exporter.add_chapter_details(
            chapter=chapter_info,
            notes=extractor.get_chapter_notes(),
            padding=padding,
            directory=directory,
        )


@dataclass
class WebtoonDownloader:
    url: str
    start_chapter: int
    end_chapter: int
    chapter_downloader: ChapterDownloader
    storage_type: StorageType

    concurrent_chapters: int = DEFAULT_CHAPTER_LIMIT
    directory: str | PathLike[str] | None = None
    exporter: TextExporter | None = None

    _directory: str | PathLike[str] = field(init=False)

    async def run(self) -> list[DownloadResult | BaseException]:
        async with webtoon.client.new() as client:
            fetcher = WebtoonFetcher(client)
            chapter_list = await fetcher.get_chapters_details(self.url, self.start_chapter, self.end_chapter)

            resp = await client.get(self.url)
            extractor = WebtoonMainPageExtractor(resp.text)
            self._directory = self.directory or fileutil.slugify_name(extractor.get_series_title())
            await self._export_data(extractor)

            # Semaphore to limit the number of concurrent chapter downloads
            semaphore = asyncio.Semaphore(self.concurrent_chapters)
            tasks = []
            for chapter_info in chapter_list:
                task = self._create_chapter_download_task(chapter_info, semaphore)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            if self.exporter:
                await self.exporter.write_data(self._directory)
            return results

    def _create_chapter_download_task(self, chapter_info: ChapterInfo, semaphore: asyncio.Semaphore) -> asyncio.Task:
        async def task() -> list[DownloadResult | BaseException]:
            async with semaphore:
                storage = await _get_storage(self._directory, self.storage_type, chapter_info)
                return await self.chapter_downloader.run(chapter_info, self._directory, storage)

        return asyncio.create_task(task())

    async def _export_data(self, extractor: WebtoonMainPageExtractor) -> None:
        if not self.exporter:
            return

        await self.exporter.add_series_texts(summary=extractor.get_series_summary(), directory=self._directory)


async def _get_storage(
    directory: str | PathLike[str],
    storage_type: StorageType,
    chapter_info: ChapterInfo,
) -> AioWriter:
    _dir = Path(directory)
    dest = str(chapter_info.number)
    if storage_type in ["zip", "cbz"]:
        return AioZipWriter(_dir / f"{dest}.{storage_type}")
    elif storage_type == "pdf":
        return AioPdfWriter(_dir / f"{dest}.pdf")
    else:
        return AioFolderWriter(_dir)


# def _get_file_name_mutator(separate: bool) -> FileNameMutator:
#     def _file_name_mutator(webtoon_info: WebtoonInfo, chapter_info: ChapterInfo, page_info: PageInfo | None)-> str:
#         chapter_name = f"{chapter_info.number:0{len(str(webtoon_info.total_chapters))}d}"
#         if not page_info:
#             return str(Path(chapter_name)) if separate else ""

#         name = f"{page_info.page_number:0{len(str(page_info.total_pages))}d}" if page_info else ""
#         if separate:
#             return str(Path(chapter_name) / name)
#         else:
#             return f"{chapter_name}_{name}"

#     return _file_name_mutator


async def main() -> None:
    n_chapters = 0
    n_images = 0
    separate = True
    traceback.install()

    async def _chapter_progress(progress: int) -> None:
        nonlocal n_chapters
        print(f"Chapter progress updated by: {progress}")
        n_chapters += 1

    async def _image_progress(progress: int) -> None:
        nonlocal n_images
        print(f"Image progress updated by: {progress}")
        n_images += 1

    file_name_generator = NonSeparateFileNameGenerator() if separate else SeparateFileNameGenerator()
    image_downloader = ImageDownloader(
        client=webtoon.client.new_image_client(),
        transformers=[AioImageFormatTransformer("JPEG")],
        progress_callback=_image_progress,
    )

    exporter = TextExporter("all")
    chapter_downloader = ChapterDownloader(
        client=webtoon.client.new(),
        exporter=exporter,
        progress_callback=_chapter_progress,
        image_downloader=image_downloader,
        file_name_generator=file_name_generator,
    )
    downloader = WebtoonDownloader(
        url="https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
        start_chapter=9,
        end_chapter=10,
        chapter_downloader=chapter_downloader,
        storage_type="file",
        exporter=exporter,
    )
    results = await downloader.run()

    if isinstance(results[0], Exception):
        raise results[0]

    pprint(results)
    # flattened_results = [
    #     item for sublist in results for item in sublist if item is not None
    # ]

    # pprint(flattened_results)
    # for r in flattened_results:
    #     if isinstance(r, DownloadError):
    #         print(r)
    #         raise r

    print(f"finished download of {n_chapters} with a total of {n_images} images")


if __name__ == "__main__":
    asyncio.run(main())
