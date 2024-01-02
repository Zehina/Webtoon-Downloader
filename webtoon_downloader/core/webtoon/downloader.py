from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Awaitable, Callable, Literal, Union

import httpx
from typing_extensions import TypeAlias

from webtoon_downloader.core import file as fileutil
from webtoon_downloader.core import webtoon
from webtoon_downloader.core.downloaders.image import (
    ImageDownloader,
    ImageProgressCallback,
)
from webtoon_downloader.core.exceptions import ChapterDownloadError
from webtoon_downloader.core.webtoon.exporter import TextExporter
from webtoon_downloader.core.webtoon.extractor import (
    WebtoonMainPageExtractor,
    WebtoonViewerPageExtractor,
)
from webtoon_downloader.core.webtoon.fetchers import WebtoonFetcher
from webtoon_downloader.core.webtoon.models import ChapterInfo
from webtoon_downloader.storage import (
    AioFileWriter,
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

# TODO: make seperate option work


@dataclass
class ChapterDownloader:
    client: httpx.AsyncClient
    directory: str | PathLike[str]
    chapter_info: ChapterInfo
    writer: AioWriter
    exporter: TextExporter | None = None
    progress_callback: ImageProgressCallback | None = None

    async def run(self) -> list[DownloadResult | BaseException]:
        try:
            tasks: list[asyncio.Task] = []
            resp = await self.client.get(self.chapter_info.content_url)
            extractor = WebtoonViewerPageExtractor(resp.text)
            urls = extractor.get_img_urls()
            num_digits = len(str(len(urls)))
            await self._export_data(extractor)
            async with self.writer as writer:
                for n, url in enumerate(urls):
                    tasks.append(
                        self._create_img_download_task(
                            self.client, url, f"{n:0{num_digits}d}.jpg", writer
                        )
                    )
                return await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as exc:
            raise ChapterDownloadError(
                self.chapter_info.content_url, exc, chapter_info=self.chapter_info
            ) from exc

    def _create_img_download_task(
        self,
        client: httpx.AsyncClient,
        url: str,
        file_name: str,
        container: AioWriter,
    ) -> asyncio.Task:
        async def task() -> Path:
            await ImageDownloader(
                client,
                file_name,
                container,
                transformers=[AioImageFormatTransformer("JPEG")],
                progress_callback=self.progress_callback,
            ).run(url)
            return Path(Path(self.directory) / file_name)

        return asyncio.create_task(task())

    async def _export_data(self, extractor: WebtoonViewerPageExtractor) -> None:
        if not self.exporter:
            return
        await self.exporter.add_chapter_texts(
            chapter=self.chapter_info.chapter_number,
            title=extractor.get_chapter_title(),
            notes=extractor.get_chapter_notes(),
            directory=self.directory,
        )


@dataclass
class WebtoonDownloader:
    url: str
    storage_type: StorageType = "file"

    concurrent_chapters: int = DEFAULT_CHAPTER_LIMIT
    directory: str | PathLike[str] | None = None
    exporter: TextExporter | None = None
    image_progress_callback: ImageProgressCallback | None = None
    chapter_progress_callback: ChapterProgressCallback | None = None

    _directory: str | PathLike[str] = field(init=False)

    async def run(self) -> list[DownloadResult | BaseException]:
        headers = {
            "accept-language": "en-US,en;q=0.9",
            "dnt": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
        }
        async with httpx.AsyncClient(headers=headers) as client:
            fetcher = WebtoonFetcher(client)
            resp = await client.get(self.url)
            extractor = WebtoonMainPageExtractor(resp.text)
            self._directory = self.directory or fileutil.slugify_name(
                extractor.get_series_title()
            )

            await self._export_data(extractor)
            viewer_url = extractor.get_chapter_viewer_url()
            chapter_list = await fetcher.get_chapters_details(
                viewer_url, self.url, 500, 501
            )

            # Semaphore to limit the number of concurrent chapter downloads
            semaphore = asyncio.Semaphore(self.concurrent_chapters)
            image_client = webtoon.client.get_image_client()

            tasks = []
            for chapter_info in chapter_list:
                task = self._create_chapter_download_task(
                    image_client,
                    chapter_info,
                    semaphore,
                )
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            if self.exporter:
                await self.exporter.write_data(self._directory)
            return results

    def _create_chapter_download_task(
        self,
        client: httpx.AsyncClient,
        chapter_info: ChapterInfo,
        semaphore: asyncio.Semaphore,
    ) -> asyncio.Task:
        async def task() -> list[DownloadResult | BaseException]:
            async with semaphore:
                chapter_downloader = ChapterDownloader(
                    client=client,
                    directory=self._directory,
                    chapter_info=chapter_info,
                    exporter=self.exporter,
                    writer=(await self._get_storage(chapter_info)),
                    progress_callback=self.image_progress_callback,
                )

                res = await chapter_downloader.run()
                if self.chapter_progress_callback:
                    await self.chapter_progress_callback(1)

                return res

        return asyncio.create_task(task())

    async def _export_data(self, extractor: WebtoonMainPageExtractor) -> None:
        if not self.exporter:
            return

        await self.exporter.add_series_texts(
            summary=extractor.get_series_summary(), directory=self._directory
        )

    async def _get_storage(self, chapter_info: ChapterInfo) -> AioWriter:
        _dir = Path(self._directory)
        dest = str(chapter_info.chapter_number)
        if self.storage_type in ["zip", "cbz"]:
            return AioZipWriter(_dir / f"{dest}.{self.storage_type}")
        elif self.storage_type == "pdf":
            return AioPdfWriter(_dir / f"{dest}.pdf")
        else:
            return AioFileWriter(_dir / dest)


async def main() -> None:
    n_chapters = 0
    n_images = 0
    from rich import traceback

    traceback.install()

    async def _chapter_progress(progress: int) -> None:
        nonlocal n_chapters
        print(f"Chapter progress updated by: {progress}")
        n_chapters += 1

    async def _image_progress(progress: int) -> None:
        nonlocal n_images
        print(f"Image progress updated by: {progress}")
        n_images += 1

    downloader = WebtoonDownloader(
        url="https://www.webtoons.com/en/fantasy/tower-of-god/list?title_no=95",
        storage_type="pdf",
        exporter=TextExporter("all"),
        image_progress_callback=_image_progress,
        chapter_progress_callback=_chapter_progress,
    )
    results = await downloader.run()
    from rich.pretty import pprint

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
