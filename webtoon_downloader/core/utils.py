from __future__ import annotations

import json
import logging
import os
import queue
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, TypedDict

import requests
from PIL import Image
from rich.progress import Progress, TaskID

from webtoon_downloader.core.models import ChapterInfo

log = logging.getLogger(__name__)

USER_AGENT = (
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/92.0.4515.107 Safari/537.36"
    )
    if os.name == "nt"
    else ("Mozilla/5.0 (X11; Linux ppc64le; rv:75.0)" "Gecko/20100101 Firefox/75.0")
)

headers = {
    "dnt": "1",
    "user-agent": USER_AGENT,
    "accept-language": "en-US,en;q=0.9",
}
image_headers = {"referer": "https://www.webtoons.com/", **headers}


class ThreadPoolExecutorWithQueueSizeLimit(ThreadPoolExecutor):
    def __init__(self, *args: Any, maxsize: int = 50, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._work_queue = queue.Queue(maxsize=maxsize)  # type: ignore[assignment]


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
    dest: str | Path = field(default_factory=lambda: Path("."))
    separate: bool = True
    zeros: int = 0

    _data: ExportData = field(init=False)
    _write_json: bool = field(init=False)
    _write_text: bool = field(init=False)

    def __post_init__(self) -> None:
        self._data = {"chapters": {}, "summary": ""}
        self._write_json = self.export_format in ["json", "all"]
        self._write_text = self.export_format in ["text", "all"]

    def add_series_texts(self, summary: str | None) -> None:
        if not summary or not self._write_text:
            return
        self._data["summary"] = summary
        Path(Path(self.dest) / "summary.txt").write_text(summary + "\n", encoding="utf-8")

    def add_chapter_texts(self, chapter: int, title: str, notes: str) -> None:
        self._data["chapters"][chapter] = {"title": title, "notes": notes}

        if not self._write_text:
            return

        parent = Path(self.dest)
        if self.separate:
            parent = parent / f"{chapter:0{self.zeros}d}"

        Path(parent / f"{chapter:0{self.zeros}d}_title.txt").write_text(title + "\n", encoding="utf-8")
        if notes:
            Path(parent / f"{chapter:0{self.zeros}d}_notes.txt").write_text(notes + "\n", encoding="utf-8")

    def write_data(self) -> None:
        if not self._write_json:
            return

        Path(self.dest, "info.json").write_text(json.dumps(self._data, sort_keys=True, indent=4), encoding="utf-8")


def slugify_file_name(file_name: str) -> str:
    """
    Slugifies a file name by removing special characters, replacing spaces with underscores.
    Args:
        file_name: The original file name.

    Returns:
        str: The slugified file name.

    """
    # Replace leading/trailing whitespace and replace spaces with underscores
    # And remove special characters
    return re.sub(r"[^\w.-]", "", file_name.strip().replace(" ", "_"))


def get_chapter_dir(chapter_info: ChapterInfo, zeros: int, separate_chapters: bool) -> str:
    """
    Get the relative directory to use for a chapter, given the supplied options.

    Arguments:
        chapter_info:      Information about this chapter
        zeros:             Number of digits to use for the chapter-number
        separate_chapters: Selector if each chapter should be its own directory

    Returns:
        Relative directory for files in chapter
    """
    if not separate_chapters:
        return "."
    return f"{chapter_info.chapter_number:0{zeros}d}"


def download_image(
    chapter_download_task_id: TaskID,
    progress: Progress,
    url: str,
    dest: str,
    chapter_number: int,
    page_number: int,
    zeros: int,
    image_format: str = "jpg",
    page_digits: int = 1,
) -> None:
    """
    downloads an image using a direct url into the base path folder.

    Arguments:
    ----------
    chapter_download_task_id: int
        task of calling chapter download task

    url: str
        image direct link.

    dest: str
        folder path where to save the downloaded image.

    chapter_number: int
        chapter number used for naming the saved image file.

    page_number: str | int
        page number used for naming the saved image file.

    zeros: int
        Number of digits used for the chapter number

    image_format: str
        format of downloaded image .
        (default: jpg)

    page_digits: int
        Number of digits used for the page number inside the chapter
    """
    log.debug("Requesting chapter %d: page %d", chapter_number, page_number)
    resp = requests.get(url, headers=image_headers, stream=True, timeout=5)
    progress.update(chapter_download_task_id, advance=1)

    if resp.status_code != 200:
        log.error(
            "[bold red blink]Unable to download page[/][medium_spring_green]%d[/]"
            "from chapter [medium_spring_green]%d[/], request returned"
            "error [bold red blink]%d[/]",
            page_number,
            chapter_number,
            resp.status_code,
        )
        return

    resp.raw.decode_content = True
    file_name = f"{chapter_number:0{zeros}d}_{page_number:0{page_digits}d}"

    if image_format == "png":
        Image.open(resp.raw).save(os.path.join(dest, f"{file_name}.png"))
    else:
        with open(os.path.join(dest, f"{file_name}.jpg"), "wb") as f:
            shutil.copyfileobj(resp.raw, f)
