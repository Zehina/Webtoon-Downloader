from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

import httpx

from webtoon_downloader.core.exceptions import ImageDownloadError
from webtoon_downloader.storage import AioWriter
from webtoon_downloader.transformers.base import AioImageTransformer

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
    client: httpx.AsyncClient
    transformers: list[AioImageTransformer] = field(default_factory=list)
    progress_callback: ImageProgressCallback | None = None

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
            return await self._download_image(self.client, url, target, storage)
        except Exception as exc:
            raise ImageDownloadError(url=url, cause=exc) from exc

    async def _download_image(
        self, client: httpx.AsyncClient, url: str, target: str, storage: AioWriter
    ) -> ImageDownloadResult:
        """
        Downloads and processes the byte image stream from a given URL.

        This also applies transformations to the stream, and saves it to the storage.

        """
        async with client.stream("GET", url) as response:
            response.raise_for_status()
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
