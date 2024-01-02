from __future__ import annotations

from typing import AsyncIterator, Protocol, runtime_checkable

from .exceptions import StreamWriteError
from .file import AioFileWriter
from .pdf import AioPdfWriter
from .zip import AioFileBufferedZipWriter, AioZipWriter


@runtime_checkable
class AioWriter(Protocol):
    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:
        ...

    async def __aenter__(self) -> AioWriter:
        ...

    async def __aexit__(self, *_: tuple) -> None:
        ...


__all__ = [
    "AioFileWriter",
    "AioPdfWriter",
    "AioZipWriter",
    "AioFileBufferedZipWriter",
    "AioWriter",
    "StreamWriteError",
]
