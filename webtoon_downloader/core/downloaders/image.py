from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable

import httpx

from webtoon_downloader.core.exceptions import ImageDownloadError
from webtoon_downloader.storage import AioWriter
from webtoon_downloader.transformers.image import AioImageTransformer

ImageProgressCallback = Callable[[int], Awaitable[None]]
"""
Progress callback called for each image download.
"""


@dataclass
class ImageDownloadResult:
    """
    Represents the ImageDownloadResult

    Args:
        size: Size of the image downloaded/written
    """

    size: int


@dataclass
class ImageDownloader:
    client: httpx.AsyncClient
    target: str
    storage: AioWriter
    transformers: list[AioImageTransformer] = field(default_factory=list)
    progress_callback: ImageProgressCallback | None = None

    async def run(self, url: str) -> ImageDownloadResult:
        """
        Initiates the downloading of an image from a specified URL.

        Args:
            url: The URL of the image to be downloaded.

        Returns:
            ImageDownloadResult: The result of the download operation.

        Raises:
            ImageDownloadError: If an error occurs during the download process.
        """
        try:
            size = await self._download_image(url)
            return ImageDownloadResult(size=size)
        except Exception as exc:
            raise ImageDownloadError(url=url, cause=exc) from exc

    async def _download_image(self, url: str) -> int:
        """
        Downloads and processes the byte image stream from a given URL.

        This also applies transformations to the stream, and saves it to the storage.

        """
        async with self.client.stream("GET", url) as response:
            response.raise_for_status()
            response_stream = response.aiter_bytes()
            # No need to keep the stream open whilst performing all transformations
            # Better to send the stream to the first transformer then close the client stream
            if len(self.transformers) > 0:
                response_stream = await self.transformers[0].transform(response_stream)

        for transformer in self.transformers[1:]:
            response_stream = await transformer.transform(response_stream)
        size = await self.storage.write(response_stream, item_name=self.target)
        await self._update_progress()
        return size

    async def _update_progress(self) -> None:
        """
        Updates the progress of the image download if it is set
        """
        if self.progress_callback:
            await self.progress_callback(1)
