import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO
from typing import Any, AsyncIterator, Callable, Literal, Protocol

from PIL import Image

ImageFormats = Literal["PNG", "JPEG"]


log = logging.getLogger(__name__)


async def _bytesio_to_async_gen(bytes_io: BytesIO, chunk_size: int = 1024) -> AsyncIterator[bytes]:
    while True:
        chunk = bytes_io.read(chunk_size)
        if not chunk:
            break
        yield chunk


class AioImageTransformer(Protocol):
    async def transform(self, image_stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        """Transforms and returns the given image"""


@dataclass
class AioImageFormatTransformer:
    target_format: ImageFormats

    async def transform(self, image_stream: AsyncIterator[bytes]) -> AsyncIterator[bytes]:
        bytes_io_stream = BytesIO()
        async for chunk in image_stream:
            bytes_io_stream.write(chunk)
        bytes_io_stream.seek(0)

        # Determine if transformation is necessary
        transform_needed = await self._run_in_executor(self._is_transformation_needed, bytes_io_stream)

        if transform_needed:
            log.debug("Running image convertion to %s", self.target_format)
            transformed_stream = await self._run_in_executor(self._sync_transform, bytes_io_stream)
        else:
            log.debug("No transformation needed")
            transformed_stream = bytes_io_stream
            transformed_stream.seek(0)

        return _bytesio_to_async_gen(transformed_stream)

    def _is_transformation_needed(self, image_stream: BytesIO) -> bool:
        try:
            with Image.open(image_stream) as image:
                return image.format != self.target_format
        except OSError:
            return True  # Proceed with transformation if format detection fails

    def _sync_transform(self, image_stream: BytesIO) -> BytesIO:
        with Image.open(image_stream) as image:
            output_stream = BytesIO()
            image.save(output_stream, format=self.target_format)
            output_stream.seek(0)
            return output_stream

    async def _run_in_executor(self, func: Callable, *args: Any) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)
