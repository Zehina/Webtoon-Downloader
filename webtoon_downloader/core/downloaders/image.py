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

ImageDownloadResult = int


@dataclass
class ImageDownloader:
    client: httpx.AsyncClient
    target: str
    storage: AioWriter
    transformers: list[AioImageTransformer] = field(default_factory=list)
    progress_callback: ImageProgressCallback | None = None

    async def run(self, url: str) -> ImageDownloadResult:
        try:
            return await self._download_image(url)
        except Exception as exc:
            raise ImageDownloadError(url=url, cause=exc) from exc

    async def _download_image(self, url: str) -> int:
        """Download and processes the byte image stream. Raises any HTTP error that might occur, otherwise saves the image to the storage."""
        async with self.client.stream("GET", url) as response:
            response.raise_for_status()
            response_stream = response.aiter_bytes()
            # No need to keep the stream open whilst performing all transformations
            # Better to send the stream to the first transformer then close the client stream
            if len(self.transformers) > 0:
                response_stream = await self.transformers[0].transform(response_stream)

        for transformer in self.transformers[1:]:
            response_stream = await transformer.transform(response_stream)
        res = await self.storage.write(response_stream, item_name=self.target)
        await self._update_progress()
        return res

    async def _update_progress(self) -> None:
        """Updates the progress of the download if a callback is set."""
        if self.progress_callback:
            await self.progress_callback(1)
