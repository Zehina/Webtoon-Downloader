import json
import logging
import os
import queue
import re
import shutil
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image
from rich.progress import Progress

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
    def __init__(self, *args, maxsize=50, **kwargs):
        super().__init__(*args, **kwargs)
        self._work_queue = queue.Queue(maxsize=maxsize)


class TextExporter:
    """Writes text elements to files, either to multiple plain text files
    or to a single JSON file, depending on selected export format."""

    def __init__(self, export_format: str):
        self.data = {"chapters": {}}
        self.write_json = export_format in ["json", "all"]
        self.write_text = export_format in ["text", "all"]

    def set_chapter_config(self, zeros: int, separate: bool):
        self.separate = separate
        self.zeros = zeros

    def set_dest(self, dest: str):
        self.dest = dest

    def add_series_texts(self, summary: str):
        self.data["summary"] = summary
        if self.write_text:
            with open(os.path.join(self.dest, "summary.txt"), "w") as f:
                f.write(summary + "\n")

    def add_chapter_texts(self, chapter: int, title: str, notes: str):
        self.data["chapters"][chapter] = {"title": title}
        if notes is not None:
            self.data["chapters"][chapter]["notes"] = notes
        if self.write_text:
            prefix = self.dest
            if self.separate:
                prefix = os.path.join(prefix, f"{chapter:0{self.zeros}d}")
            prefix = os.path.join(prefix, f"{chapter:0{self.zeros}d}_")
            with open(prefix + "title.txt", "w") as f:
                f.write(title + "\n")
            if notes is not None:
                with open(prefix + "notes.txt", "w") as f:
                    f.write(notes + "\n")

    def write_data(self):
        if self.write_json:
            with open(os.path.join(self.dest, "info.json"), "w") as f:
                json.dump(self.data, f, sort_keys=True)


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
    chapter_download_task_id: int,
    progress: Progress,
    url: str,
    dest: str,
    chapter_number: int,
    page_number: int,
    zeros: int,
    image_format: str = "jpg",
    page_digits: int = 1,
):
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
    if resp.status_code == 200:
        resp.raw.decode_content = True
        file_name = f"{chapter_number:0{zeros}d}_{page_number:0{page_digits}d}"
        if image_format == "png":
            Image.open(resp.raw).save(os.path.join(dest, f"{file_name}.png"))
        else:
            with open(os.path.join(dest, f"{file_name}.jpg"), "wb") as f:
                shutil.copyfileobj(resp.raw, f)
    else:
        log.error(
            "[bold red blink]Unable to download page[/][medium_spring_green]%d[/]"
            "from chapter [medium_spring_green]%d[/], request returned"
            "error [bold red blink]%d[/]",
            page_number,
            chapter_number,
            resp.status_code,
        )
