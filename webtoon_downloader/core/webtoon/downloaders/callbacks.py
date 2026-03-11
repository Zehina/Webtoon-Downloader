from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Literal, TypeAlias

from webtoon_downloader.core.webtoon.extractor import WebtoonViewerPageExtractor
from webtoon_downloader.core.webtoon.models import ChapterInfo, PageInfo

OnWebtoonFetchCallback: TypeAlias = Callable[[Sequence[ChapterInfo]], Awaitable[None]]
"""
Progress callback called for each chapter download.
"""

ChapterProgressType: TypeAlias = Literal["Start", "ChapterInfoFetched", "PageCompleted", "Completed"]
"""
Type of progress being reported.
"""

ChapterProgressCallback: TypeAlias = Callable[
    [ChapterInfo, ChapterProgressType, WebtoonViewerPageExtractor | None], Awaitable[None]
]
"""
Progress callback called for each chapter download. Takes the chapter info and progress type
"""

PageProgressCallback: TypeAlias = Callable[[PageInfo], Awaitable[None]]
"""
Progress callback called for each page download. Takes the page info.
"""
