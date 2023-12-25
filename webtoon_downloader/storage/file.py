from __future__ import annotations

from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import AsyncIterator

import aiofiles

from .exceptions import StreamWriteError


@dataclass
class AioFileWriter:
    container: str | PathLike

    _container: Path = field(init=False)

    def __post_init__(self) -> None:
        self._container = Path(self.container)

    async def __aenter__(self) -> AioFileWriter:
        self._container.mkdir(parents=True, exist_ok=True)
        return self

    async def write(self, stream: AsyncIterator[bytes], item_name: str) -> int:
        self._container.mkdir(parents=True, exist_ok=True)
        full_path = self._container / item_name
        written = 0
        async with aiofiles.open(full_path, mode="wb") as file:
            try:
                async for chunk in stream:
                    await file.write(chunk)
                    written += len(chunk)
            except Exception as exc:
                raise StreamWriteError(full_path) from exc
        return written

    async def __aexit__(self, *_: tuple) -> None:
        pass
