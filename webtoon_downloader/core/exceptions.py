from __future__ import annotations

from dataclasses import dataclass, field

from webtoon_downloader.core.webtoon.models import ChapterInfo


@dataclass
class DownloadError(Exception):
    """BaseException raised for download errors."""

    url: str
    cause: Exception
    message: str | None = field(default=None)

    def __str__(self) -> str:
        if self.message:
            return self.message

        return f"Failed to download from {self.url}"


@dataclass
class WebtoonDownloadError(DownloadError):
    """Exception raised for Webtoon download errors"""


@dataclass
class ImageDownloadError(DownloadError):
    """Exception raised for image download errors"""


@dataclass
class ChapterDownloadError(DownloadError):
    """Exception raised for chapter download errors"""

    chapter_info: ChapterInfo | None = None


@dataclass
class FetchError(Exception):
    """Exception raised due to a fetch error"""

    series_url: str
    message: str | None = None

    def __str__(self) -> str:
        if self.message:
            return self.message
        else:
            return f"Failed to fetch from {self.series_url}"


@dataclass
class WebtoonFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving Webtoon information"""

    message: str | None = None

    def __str__(self) -> str:
        if self.message:
            return self.message
        else:
            return f"Failed to fetch Webtoon information from {self.series_url}"


@dataclass
class ChapterURLFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving the chapter URL"""

    def __str__(self) -> str:
        return f"Failed to fetch chapter URL from {self.series_url}"


@dataclass
class ChapterTitleFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving the chapter title"""

    def __str__(self) -> str:
        return f"Failed to fetch chapter title from {self.series_url}"


@dataclass
class ChapterDataEpisodeNumberFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving data chapter number"""

    def __str__(self) -> str:
        return f"Failed to fetch data episode number from {self.series_url}"


@dataclass
class SeriesTitleFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving the series title"""

    def __str__(self) -> str:
        return f"Failed to fetch series title from {self.series_url}"
