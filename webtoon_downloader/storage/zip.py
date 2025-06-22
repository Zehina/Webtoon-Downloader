from __future__ import annotations

import asyncio
import io
import tempfile
import zipfile
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import AsyncIterator, Literal, Union

import aiofiles
from typing_extensions import TypeAlias

from .exceptions import stream_error_handler

ZipWriteMode: TypeAlias = Literal["a", "w"]
"""
- 'w' for write (creates a new archive or overwrites an existing one).
- 'a' for append (appends to an existing archive).
"""

ZipContainer: TypeAlias = Union[str, PathLike, io.BytesIO]
"""
Container type for Zip files
- `str | PathLike`: Path to a file either as a string, pathlib.Path or other PathLike object
- `io.BytesIO`: Any Byte like object
"""


def _open_zip_file(container: ZipContainer, mode: ZipWriteMode) -> zipfile.ZipFile:
    """Returns a ZipFile object from the provided container type and file open mode"""
    if isinstance(container, io.BytesIO):
        return zipfile.ZipFile(container, mode=mode, compression=zipfile.ZIP_DEFLATED)
    elif isinstance(container, (str, Path)):
        container_path = Path(container)
        container_path.parent.mkdir(parents=True, exist_ok=True)
        return zipfile.ZipFile(container_path, mode=mode, compression=zipfile.ZIP_DEFLATED)
    else:
        raise TypeError(container)


@dataclass
class AioZipWriter:
    """
    An asynchronous writer for creating and modifying ZIP archives. This writer
    utilizes the memory to consume the asynchronous stream before adding them to the ZIP archive.

    Attributes:
        container   : The path where the in-memory ZIP archive will be saved upon completion.
        mode        : The mode for creating the ZIP archive.
    """

    container: ZipContainer
    mode: ZipWriteMode = "w"

    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _zip_file: zipfile.ZipFile = field(init=False)

    @stream_error_handler
    async def __aenter__(self) -> AioZipWriter:
        self._zip_file = _open_zip_file(self.container, self.mode)
        return self

    @stream_error_handler
    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:
        """
        Asynchronously stores the given byte stream as a file in the in-memory ZIP archive.

        Args:
            stream      : An asynchronous iterator yielding bytes to be stored.
            item_name   : The name of the file to be created in the in-memory ZIP archive.

        Returns:
            The number of bytes written.
        """
        data = b""
        written = 0

        async for chunk in stream:
            data += chunk
            written += len(chunk)

        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._zip_file.writestr, item_name, data)

        return written

    @stream_error_handler
    async def __aexit__(self, *_: tuple) -> None:
        self._zip_file.close()


@dataclass
class AioFileBufferedZipWriter(AioZipWriter):
    """
    An asynchronous writer for creating and modifying ZIP archives. This writer
    utilizes the filesystem to store temporary files before adding them to the ZIP archive.

    Attributes:
        container   : The path to the ZIP file to be created or modified.
        mode        : The mode for creating the ZIP archive.
    """

    container: ZipContainer
    mode: ZipWriteMode = "w"

    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _zip_file: zipfile.ZipFile = field(init=False)
    _temp_files: list[Path] = field(default_factory=list)

    @stream_error_handler
    async def __aenter__(self) -> AioFileBufferedZipWriter:
        self._zip_file = _open_zip_file(self.container, self.mode)
        return self

    @stream_error_handler
    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:
        """
        Asynchronously writes the given byte stream to a file within the ZIP archive.

        Args:
            stream      : An asynchronous iterator yielding bytes to be written.
            item_name   : The name of the file to be created inside the ZIP archive.

        Returns:
            The number of bytes written.
        """
        written = 0
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webtoon_downloader.tmp") as tmp:
            temp_file = Path(tmp.name)
            self._temp_files.append(temp_file)

        try:
            async with aiofiles.open(temp_file, mode="wb") as file:
                async for chunk in stream:
                    await file.write(chunk)
                    written += len(chunk)
            await self._add_to_zip(temp_file, item_name)
        finally:
            temp_file.unlink(missing_ok=True)

        return written

    async def _add_to_zip(self, temp_file_path: Path, item_name: str) -> None:
        """
        Asynchronously adds the temporary file to the ZIP archive and deletes it.
        The Zipfile write method is synchronous, so the lock must be held before the operation.
        """

        def _write_to_zip() -> None:
            try:
                self._zip_file.write(temp_file_path, arcname=item_name)
            finally:
                temp_file_path.unlink()

        async with self._lock:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, _write_to_zip)

    @stream_error_handler
    async def __aexit__(self, *_: tuple) -> None:
        self._zip_file.close()
        # Cleanup of temporary files, if any were not handled already
        for temp_file in self._temp_files:
            temp_file.unlink(missing_ok=True)
