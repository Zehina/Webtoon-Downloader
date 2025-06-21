from __future__ import annotations

from dataclasses import dataclass, field

from webtoon_downloader.core.webtoon.models import ChapterInfo


@dataclass
class DownloadError(Exception):
    """BaseException raised for download errors."""

    url: str
    cause: Exception | None = None
    base_message: str = "Failed to download from"
    message: str | None = field(default=None)

    def __str__(self) -> str:
        if self.message:
            return self.message

        if self.cause:
            cause_msg = str(self.cause)
            if cause_msg:
                return f'{self.base_message} "{self.url}" => {cause_msg}'

            return f'{self.base_message} "{self.url}" due to: {self.cause.__class__.__name__}'

        return f'{self.base_message}: "{self.url}"'


@dataclass
class WebtoonDownloadError(DownloadError):
    """Exception raised for Webtoon download errors"""

    base_message: str = "Failed to download Webtoon"


@dataclass
class ImageDownloadError(DownloadError):
    """Exception raised for image download errors"""

    base_message: str = "downloading image"


@dataclass
class ChapterDownloadError(DownloadError):
    """Exception raised for chapter download errors"""

    base_message: str = "downloading chapter"

    chapter_info: ChapterInfo | None = None


@dataclass
class WebtoonGetError(Exception):
    """Exception raised due to a fetch error when retreiving Webtoon information"""

    series_url: str
    status_code: int

    def __str__(self) -> str:
        return f"Failed to fetch Webtoon information from {self.series_url}. Status code: {self.status_code}"


@dataclass
class InvalidURL(Exception):
    """Exception raised due to an invalid URL"""

    url: str

    def __str__(self) -> str:
        return f"Invalid URL: {self.url}"


@dataclass
class FetchError(Exception):
    """Exception raised due to a fetch error"""

    msg: str | None = None


@dataclass
class ChapterURLFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving the chapter URL"""

    def __str__(self) -> str:
        if self.msg:
            return self.msg

        return "Failed to fetch chapter URL"


@dataclass
class ChapterTitleFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving the chapter title"""

    def __str__(self) -> str:
        if self.msg:
            return self.msg

        return "Failed to fetch chapter title"


@dataclass
class ChapterDataEpisodeNumberFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving data chapter number"""

    def __str__(self) -> str:
        if self.msg:
            return self.msg

        return "Failed to fetch data episode number"


@dataclass
class NoChaptersFoundError(FetchError):
    """Exception raised when no chapters are found"""

    def __str__(self) -> str:
        if self.msg:
            return self.msg

        return "No chapters found"


@dataclass
class SeriesTitleFetchError(FetchError):
    """Exception raised due to a fetch error when retreiving the series title"""

    def __str__(self) -> str:
        if self.msg:
            return self.msg

        return "Failed to fetch series title"


@dataclass
class RateLimitedError(FetchError):
    """Exception raised when we suspect the server is rate limiting us"""

    def __str__(self) -> str:
        if self.msg:
            return self.msg

        return "Rate limited"
