from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from .exceptions import StreamWriteError
from .file import AioFolderWriter
from .pdf import AioPdfWriter
from .zip import AioFileBufferedZipWriter, AioZipWriter


@runtime_checkable
class AioWriter(Protocol):
    """
    Protocol for asynchronous writers.

    This protocol defines the standard interface for writers.
    Classes implementing this protocol should provide asynchronous methods for writing data,
    entering and exiting an asynchronous context.
    """

    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:  # pyright: ignore[reportReturnType]
        """
        Asynchronously writes a stream of bytes to a specified item.

        Args:
            stream      : An asynchronous iterator yielding bytes to be written.
            item_name   : The name of the item (such as a file or a page) to be written.

        Returns:
            The number of bytes written.
        """

    async def __aenter__(self) -> AioWriter:  # pyright: ignore[reportReturnType]
        """
        Asynchronous context manager entry.

        Returns:
            An instance of the class implementing the AioWriter protocol.
        """

    async def __aexit__(self, *_: tuple) -> None:
        """
        Asynchronous context manager exit, for cleaning up resources.
        """


__all__ = [
    "AioFileBufferedZipWriter",
    "AioFolderWriter",
    "AioPdfWriter",
    "AioWriter",
    "AioZipWriter",
    "StreamWriteError",
]
