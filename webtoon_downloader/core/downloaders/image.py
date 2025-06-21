from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

import httpx

from webtoon_downloader.core.exceptions import ImageDownloadError, RateLimitedError
from webtoon_downloader.core.webtoon.client import WebtoonHttpClient
from webtoon_downloader.storage import AioWriter
from webtoon_downloader.transformers.base import AioImageTransformer

log = logging.getLogger(__name__)

ImageProgressCallback = Callable[[int], Awaitable[None]]
"""
Progress callback called for each image download.
"""


@dataclass
class ImageDownloadResult:
    """
    Represents the ImageDownloadResult

    Args:
        name: Name of downloaded image.
        size: Size of the image downloaded/written.
    """

    name: str
    size: int


@dataclass
class ImageDownloader:
    client: WebtoonHttpClient
    concurent_downloads_limit: int
    transformers: list[AioImageTransformer] = field(default_factory=list)
    progress_callback: ImageProgressCallback | None = None

    _semaphore: asyncio.Semaphore = field(init=False)

    def __post_init__(self) -> None:
        self._semaphore = asyncio.Semaphore(self.concurent_downloads_limit)

    async def run(self, url: str, target: str, storage: AioWriter) -> ImageDownloadResult:
        """
        Initiates the downloading of an image from a specified URL.

        Args:
            url       : The URL of the image to be downloaded.
            name      : The target name of the image. Note: The extension can be mutated by the image downloader.

        Returns:
            ImageDownloadResult: The result of the download operation.

        Raises:
            ImageDownloadError: If an error occurs during the download process.
        """
        try:
            async with self._semaphore:
                return await self._download_image(url, target, storage)
        except Exception as exc:
            raise ImageDownloadError(url=url, cause=exc) from exc

    async def _download_image(self, url: str, target: str, storage: AioWriter) -> ImageDownloadResult:
        """
        Downloads and processes the byte image stream from a given URL.

        This also applies transformations to the stream, and saves it to the storage.

        """
        async with self.client.stream("GET", url) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPError as exc:
                if response.status_code == 429:
                    raise ImageDownloadError(
                        url=url, cause=RateLimitedError(f"Rate limitied while downloading image from {url}")
                    ) from exc

            size = 0
            response_stream = response.aiter_bytes()
            for transformer in self.transformers:
                response_stream, target = await transformer.transform(response_stream, target)

            size = await storage.write(response_stream, target)
        await self._update_progress()
        return ImageDownloadResult(target, size)

    async def _update_progress(self) -> None:
        """
        Updates the progress of the image download if it is set
        """
        if self.progress_callback:
            await self.progress_callback(1)
