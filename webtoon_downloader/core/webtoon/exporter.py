from __future__ import annotations

import json
from dataclasses import dataclass, field
from os import PathLike
from pathlib import Path
from typing import Literal, TypedDict

import aiofiles

TextExporterFormat = Literal["text", "json", "all"]


class ExportChapterData(TypedDict):
    title: str
    notes: str


class ExportData(TypedDict):
    chapters: dict[int, ExportChapterData]
    summary: str


@dataclass
class TextExporter:
    """Writes text elements to files, either to multiple plain text files
    or to a single JSON file, depending on selected export format."""

    export_format: TextExporterFormat
    dest: str | PathLike[str] = field(default_factory=lambda: Path("."))
    zeros: int = 0

    _dest: Path = field(init=False)
    _data: ExportData = field(init=False)
    _write_json: bool = field(init=False)
    _write_text: bool = field(init=False)

    def __post_init__(self) -> None:
        self._data = {"chapters": {}, "summary": ""}
        self._dest = Path(self.dest)
        self._write_json = self.export_format in ["json", "all"]
        self._write_text = self.export_format in ["text", "all"]

    async def add_series_texts(
        self, summary: str | None, directory: str | PathLike[str] | None = None
    ) -> None:
        if not summary or not self._write_text:
            return

        self._data["summary"] = summary
        directory = Path(directory) if directory else self._dest
        await self._aio_write(directory / "summary.txt", summary)

    async def add_chapter_texts(
        self,
        chapter: int,
        title: str,
        notes: str,
        directory: str | PathLike[str] | None = None,
    ) -> None:
        self._data["chapters"][chapter] = {"title": title, "notes": notes}

        if not self._write_text:
            return

        directory = Path(directory) if directory else self._dest
        await self._aio_write(directory / f"{chapter:0{self.zeros}d}_title.txt", title)

        if notes:
            await self._aio_write(
                directory / f"{chapter:0{self.zeros}d}_notes.txt", notes
            )

    async def write_data(
        self,
        directory: str | PathLike[str] | None = None,
    ) -> None:
        if not self._write_json:
            return

        directory = Path(directory) if directory else self._dest
        data = json.dumps(self._data, sort_keys=True, indent=4)
        await self._aio_write(directory / "info.json", data, end="")

    async def _aio_write(
        self,
        target: str | Path,
        data: str,
        mode: Literal["a", "w"] = "w",
        end: str = "\n",
    ) -> None:
        """Asynchronously writes the given data and creates the parent path if it doesn not exist"""
        target = Path(target)
        target.parent.mkdir(exist_ok=True, parents=True)
        async with aiofiles.open(target, mode=mode) as f:
            await f.write(data + end)
