from __future__ import annotations

from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import AsyncIterator

import aiofiles

from .exceptions import stream_error_handler


@dataclass
class AioFolderWriter:
    """
    Asynchronous file writer for handling byte streams and writing them to files.

    Args:
        container: The directory path where files will be written.
    """

    container: str | PathLike

    _container: Path = field(init=False)

    def __post_init__(self) -> None:
        self._container = Path(self.container)

    @stream_error_handler
    async def __aenter__(self) -> AioFolderWriter:
        self._container.mkdir(parents=True, exist_ok=True)
        return self

    @stream_error_handler
    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:
        """
        Writes an asynchronous byte stream to a file.

        Args:
            stream: The asynchronous byte stream to write.
            item_name: The name of the file to be written.

        Returns:
            The total number of bytes written to the file.

        Raises:
            StreamWriteError: If an error occurs during writing to the stream.
        """
        full_path = self._container / item_name
        full_path.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        async with aiofiles.open(full_path, mode="wb") as file:
            async for chunk in stream:
                await file.write(chunk)
                written += len(chunk)
        return written

    @stream_error_handler
    async def __aexit__(self, *_: tuple) -> None:
        pass
