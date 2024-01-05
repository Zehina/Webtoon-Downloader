from __future__ import annotations

from typing import AsyncIterator, Protocol


class AioImageTransformer(Protocol):
    """Protocol method to transform an image stream and modify its name."""

    async def transform(self, image_stream: AsyncIterator[bytes], target_name: str) -> tuple[AsyncIterator[bytes], str]:
        """
        Transforms and returns target image and name

        Args:
            image_stream    : An asynchronous iterator of bytes representing the image.
            target_name     : The target file name for the image.

        Returns:
            The transformed image stream and modified target name.
        """
