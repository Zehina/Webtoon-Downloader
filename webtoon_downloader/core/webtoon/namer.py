import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from furl import furl

from webtoon_downloader.core.webtoon.models import ChapterInfo, PageInfo


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename by replacing all non-alphanumeric characters with underscores on Windows.
    """
    if os.name == "nt":
        filename = re.sub(r"[^\w\.-]", "_", filename)
        if filename[-1] == "_":
            filename = filename[:-1]

    return filename


@runtime_checkable
class FileNameGenerator(Protocol):
    """
    A protocol defining the interface for generating file names for chapters, pages and exporters.
    """

    def get_chapter_directory(self, chapter_info: ChapterInfo) -> Path:
        """
        Returns the directory path for storing the given chapter's data.
        """

    def get_page_filename(self, page_info: PageInfo) -> str:
        """
        Generates a file name for the given page.
        """

    def get_title_filename(self, chapter_info: ChapterInfo) -> str:
        """
        Generates a file name for the title exporter of the given chapter.
        """

    def get_notes_filename(self, chapter_info: ChapterInfo) -> str:
        """
        Generates a file name for the notes exporter of the given chapter.
        """


@dataclass
class SeparateFileNameGenerator(FileNameGenerator):
    """
    Name Generator for when chapters and pages are stored separately.
    """

    use_chapter_title_directories: bool = False

    def get_chapter_directory(self, chapter_info: ChapterInfo) -> Path:
        """
        Returns the directory path for storing the given chapter's data.
        """
        if self.use_chapter_title_directories:
            return Path(sanitize_filename(chapter_info.title))

        return Path(f"{chapter_info.number:0{len(str(chapter_info.total_chapters))}d}")

    def get_page_filename(self, page_info: PageInfo) -> str:
        """
        Generates a file name for a page, using the page number and the file extension from its URL.
        """
        page_number = f"{page_info.page_number:0{len(str(page_info.total_pages))}d}"
        extension = furl(page_info.url).path.segments[-1].split(".")[-1]
        return f"{page_number}.{extension}"

    def get_title_filename(self, chapter_info: ChapterInfo) -> str:
        """
        Generates a file name for the title exporter of the given chapter.
        """
        return "title.txt"

    def get_notes_filename(self, chapter_info: ChapterInfo) -> str:
        """
        Generates a file name for the notes exporter of the given chapter.
        """
        return "notes.txt"


class NonSeparateFileNameGenerator(FileNameGenerator):
    """
    Implementation of FileNameGenerator for generating file names when chapters and pages
    are stored in the same directory.
    """

    def get_chapter_directory(self, _: ChapterInfo) -> Path:  # type ignore
        """
        Returns the root directory for storing pages when they are not separated by chapters.
        """
        return Path(".")

    def get_page_filename(self, page_info: PageInfo) -> str:
        """
        Generates a file name for a page, combining the chapter number and page number,
        along with the file extension from its URL.
        """
        chapter_number = f"{page_info.chapter_info.number:0{len(str(page_info.chapter_info.total_chapters))}d}"
        page_number = f"{page_info.page_number:0{len(str(page_info.total_pages))}d}"
        extension = furl(page_info.url).path.segments[-1].split(".")[-1]
        return f"{chapter_number}_{page_number}.{extension}"

    def get_title_filename(self, chapter_info: ChapterInfo) -> str:
        """
        Generates a file name for the title exporter of the given chapter.
        """
        return f"{chapter_info.number:0{len(str(chapter_info.total_chapters))}d}_title.txt"

    def get_notes_filename(self, chapter_info: ChapterInfo) -> str:
        """
        Generates a file name for the notes exporter of the given chapter.
        """
        return f"{chapter_info.number:0{len(str(chapter_info.total_chapters))}d}_notes.txt"
