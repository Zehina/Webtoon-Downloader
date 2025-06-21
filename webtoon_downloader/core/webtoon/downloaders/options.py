from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from typing_extensions import TypeAlias

from webtoon_downloader.core.webtoon.client import RetryStrategy
from webtoon_downloader.core.webtoon.downloaders.callbacks import ChapterProgressCallback, OnWebtoonFetchCallback
from webtoon_downloader.core.webtoon.exporter import DataExporterFormat
from webtoon_downloader.transformers.image import ImageFormat

StorageType: TypeAlias = Literal["images", "zip", "cbz", "pdf"]
"""Valid option for storing the downloaded images."""


DEFAULT_CONCURENT_IMAGE_DOWNLOADS = 120
"""Default number of asynchronous image download workers. More == More likely to get server rate limited"""

DEFAULT_CONCURENT_CHAPTER_DOWNLOADS = 6
"""Default number of asynchronous chapter download workers. This does not affect rate limiting or download speed since that is all controlled by the number of concurrent image downloads."""


@dataclass
class WebtoonDownloadOptions:
    """
    Options for downloading chapters from a Webtoon.

    Attributes:
        url                       : Webtoon URL
        start                     : Starting chapter number. If None, the download starts from the first chapter.
        end                       : Ending chapter number. If None, the download goes until the last chapter.
        latest                    : Flag to download only the latest chapter. Ignores values set by start and end.
        destination               : The directory where the chapters will be downloaded.
        export_metadata           : Flag to export webtoon and chapter metadata.
        exporter_forma            : Format for exporting metadata.
        separate                  : Flag to store each chapter in separate directories.
        save_as                   : Format to save chapters.
        image_format              : Format to save chapter images.
        chapter_progress_callback : Callback function for chapter download progress.
        on_webtoon_fetched        : function invoked after fetching Webtoon information.
        concurrent_chapters       : The number of chapters to download concurrently.
        concurrent_pages          : The number of images to download concurrently.
        retry_strategy            : The strategy to use for retrying failed downloads.
        proxy:                    : proxy address to use for making requests.
    """

    url: str

    start: int | None = None
    end: int | None = None
    latest: bool = False
    destination: str | None = None

    export_metadata: bool = False
    exporter_format: DataExporterFormat = "json"

    separate: bool = True
    save_as: StorageType = "images"
    image_format: ImageFormat = "JPG"

    chapter_progress_callback: ChapterProgressCallback | None = None
    on_webtoon_fetched: OnWebtoonFetchCallback | None = None

    concurrent_chapters: int = DEFAULT_CONCURENT_CHAPTER_DOWNLOADS
    concurrent_pages: int = DEFAULT_CONCURENT_IMAGE_DOWNLOADS

    retry_strategy: RetryStrategy | None = None
    proxy: str | None = None
