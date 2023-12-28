from pathlib import Path
from typing import Protocol, runtime_checkable

from furl import furl

from webtoon_downloader.core.webtoon.models import ChapterInfo, PageInfo


@runtime_checkable
class FileNameGenerator(Protocol):
    """
    A protocol defining the interface for generating file names for chapters, pages and extractors.

    Methods:
        get_chapter_directory   : Returns a directory path for a given chapter.
        get_page_filename       : Returns a file name for a given page.
    """

    def get_chapter_directory(self, chapter_info: ChapterInfo) -> Path:
        """
        Returns the directory path for storing the given chapter's data.

        Args:
            chapter_info: The chapter information.

        Returns:
            The directory path for the chapter.
        """

    def get_page_filename(self, page_info: PageInfo) -> str:
        """
        Generates a file name for the given page.

        Args:
            page_info: The page information.

        Returns:
            The file name for the page.
        """


class SeparateFileNameGenerator(FileNameGenerator):
    """
    Name Generator for when chapters and pages are stored separately.
    """

    def get_chapter_directory(self, chapter_info: ChapterInfo) -> Path:
        """
        Returns the directory path for storing the given chapter's data.

        Args:
            chapter_info: The chapter information.

        Returns:
            The directory path for the chapter.
        """
        chapter_number = f"{chapter_info.number:0{len(str(chapter_info.total_chapters))}d}"
        return Path(chapter_number)

    def get_page_filename(self, page_info: PageInfo) -> str:
        """
        Generates a file name for a page, using the page number and the file extension from its URL.

        Args:
            page_info: The page information.

        Returns:
            The file name for the page, including its extension.
        """
        page_number = f"{page_info.page_number:0{len(str(page_info.total_pages))}d}"
        extension = furl(page_info.url).path.segments[-1].split(".")[-1]
        return f"{page_number}.{extension}"


class NonSeparateFileNameGenerator(FileNameGenerator):
    """
    Implementation of FileNameGenerator for generating file names when chapters and pages
    are stored in the same directory.
    """

    def get_chapter_directory(self, chapter_info: ChapterInfo) -> Path:  # type ignore
        """
        Returns the root directory for storing pages when they are not separated by chapters.

        Args:
            chapter_info: The chapter information.

        Returns:
            The root directory path.
        """
        return Path(".")

    def get_page_filename(self, page_info: PageInfo) -> str:
        """
        Generates a file name for a page, combining the chapter number and page number,
        along with the file extension from its URL.

        Args:
            page_info: The page information.

        Returns:
            The file name for the page, including its extension.
        """
        chapter_number = f"{page_info.chapter_info.number:0{len(str(page_info.chapter_info.total_chapters))}d}"
        page_number = f"{page_info.page_number:0{len(str(page_info.total_pages))}d}"
        extension = furl(page_info.url).path.segments[-1].split(".")[-1]
        return f"{chapter_number}_{page_number}.{extension}"
