from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol

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


class ImageDownloader(Protocol):
    async def run(self, url: str, target: str, storage: AioWriter, quality: int | None = 100) -> ImageDownloadResult:
        """Download an image and write it to storage."""


class HttpImageDownloader:
    def __init__(
        self,
        client: WebtoonHttpClient,
        concurrent_downloads_limit: int,
        transformers: list[AioImageTransformer] | None = None,
        progress_callback: ImageProgressCallback | None = None,
    ):
        self.client = client
        self.concurrent_downloads_limit = concurrent_downloads_limit
        self.transformers = transformers if transformers is not None else []
        self.progress_callback = progress_callback
        self._semaphore = asyncio.Semaphore(self.concurrent_downloads_limit)

    async def run(self, url: str, target: str, storage: AioWriter, quality: int | None = 100) -> ImageDownloadResult:
        """
        Initiates the downloading of an image from a specified URL.

        Args:
            url       : The URL of the image to be downloaded.
            name      : The target name of the image. Note: The extension can be mutated by the image downloader.
            storage   : The storage writer for saving the image.
            quality   : The quality of the image to download.

        Returns:
            ImageDownloadResult: The result of the download operation.

        Raises:
            ImageDownloadError: If an error occurs during the download process.
        """
        try:
            async with self._semaphore:
                return await self._download_image(url, target, storage, quality)
        except Exception as exc:
            raise ImageDownloadError(url=url, cause=exc) from exc

    async def _download_image(
        self, url: str, target: str, storage: AioWriter, quality: int | None = 100
    ) -> ImageDownloadResult:
        """
        Downloads and processes the byte image stream from a given URL.

        This also applies transformations to the stream, and saves it to the storage.

        """
        async with self.client.stream_image(url, quality) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPError as exc:
                if response.status_code == 429:
                    raise ImageDownloadError(
                        url=url, cause=RateLimitedError(f"Rate limited while downloading image from {url}")
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
