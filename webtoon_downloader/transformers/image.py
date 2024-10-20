from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Literal

from PIL import Image

log = logging.getLogger(__name__)

ImageFormat = Literal["PNG", "JPG", "JPEG"]
"""
Defines the permissible image formats for transformation.
"""

_ValidImageFormats = Literal["PNG", "JPEG"]
"""
Defines the valid image formats for transformation.
"""


async def _bytesio_to_async_gen(bytes_io: BytesIO, chunk_size: int = 1024) -> AsyncIterator[bytes]:
    """
    Converts a BytesIO object to an asynchronous generator yielding bytes.

    Args:
        bytes_io    : The BytesIO object to be converted.
        chunk_size  : The size of each chunk to be yielded.

    Yields:
        bytes from the asynchronous generator.
    """
    while True:
        chunk = bytes_io.read(chunk_size)
        if not chunk:
            break
        yield chunk


@dataclass
class AioImageFormatTransformer:
    """
    Transformer class for converting image formats asynchronously.

    Args:
        target_format: The target image format to convert to.
    """

    target_format: ImageFormat

    _target_format: _ValidImageFormats = field(init=False)

    def __post_init__(self) -> None:
        if self.target_format.upper() in ["JPG", "JPEG"]:
            self._target_format = "JPEG"  # JPG is not a valid format to check. and JPG == JPEG anyways
        else:
            self._target_format = "PNG"

    async def transform(self, image_stream: AsyncIterator[bytes], target_name: str) -> tuple[AsyncIterator[bytes], str]:
        """
        Transforms the format of the given image stream to the target format and updates the target name if necessary.

        Args:
            image_stream    : The stream of bytes representing the image.
            target_name     : The initial target name of the image.

        Returns:
            The transformed image stream and the updated target name.
        """
        target_name = self._update_target_name(target_name)
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
            log.debug('No transformation needed to convert to %s the target "%s"', self.target_format, target_name)
            transformed_stream = bytes_io_stream
            transformed_stream.seek(0)

        return _bytesio_to_async_gen(transformed_stream), target_name

    def _is_transformation_needed(self, image_stream: BytesIO) -> bool:
        """
        Determines if a transformation to the target format is needed for the image.

        Args:
            image_stream: The stream of bytes representing the image.

        Returns:
            True if the image format is different from the target format, False otherwise.
        """

        try:
            with Image.open(image_stream) as image:
                return image.format != self._target_format
        except OSError:
            return True  # Proceed with transformation if format detection fails

    def _sync_transform(self, image_stream: BytesIO) -> BytesIO:
        """
        Synchronously transforms the image format.

        Args:
            image_stream: The stream of bytes representing the image.

        Returns:
            BytesIO stream of the transformed image.
        """
        with Image.open(image_stream) as image:
            if self._target_format == "JPEG" and image.mode == "P":
                image = image.convert("RGB")  # Need to convert to appropriate pallet for JPEG
            output_stream = BytesIO()
            image.save(output_stream, format=self._target_format)
            output_stream.seek(0)
            return output_stream

    def _update_target_name(self, target_name: str) -> str:
        """
        Updates the target name of the image based on the target format.

        Args:
            target_name: The initial target name of the image.

        Returns:
            Updated target name with the appropriate file extension.
        """
        return str(Path(target_name).with_suffix(self._target_format_suffix()))

    async def _run_in_executor(self, func: Callable, *args: Any) -> Any:
        """Executes a function in anexecutor"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    def _target_format_suffix(self) -> str:
        """Returns the file suffix representation for the target format"""
        return f".{self.target_format}".lower()
