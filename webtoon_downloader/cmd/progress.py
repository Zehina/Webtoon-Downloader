from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import NamedTuple, Sequence

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from webtoon_downloader.core.webtoon.downloaders.callbacks import ChapterProgressType
from webtoon_downloader.core.webtoon.extractor import WebtoonViewerPageExtractor
from webtoon_downloader.core.webtoon.models import ChapterInfo


class ChapterTask(NamedTuple):
    task: TaskID
    started: bool


class HumanReadableSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: Task) -> Text:
        """Calculate and display the data transfer speed in a human-readable format.

        Args:
            task: The task for which speed is being rendered.

        Returns:
            A rich Text object displaying the speed.
        """
        speed = self._calculate_readable_speed(task)
        speed_type = task.fields.get("type", "units")
        return Text(f"{speed} {speed_type}/s", style="progress.data.speed", justify="center")

    def _calculate_readable_speed(self, task: Task) -> str:
        """Calculate human-readable speed.

        Args:
            task: The task for which speed is being calculated.

        Returns:
            Human-readable speed.
        """
        speed = task.finished_speed or task.speed
        return "?" if speed is None else f"{speed:2.0f}"


def init_progress(console: Console) -> Progress:
    """
    Initialize and configure the progress bar for the webtoon downloader.

    Sets up various columns for the progress bar to display information such as
    task description, progress percentage, transfer speed, and time remaining.

    Args:
        console   : The rich console object to which the progress bar will be output.

    Returns:
        Progress  : A configured Progress object ready for use in tracking download tasks.
    """
    return Progress(
        TextColumn("[bold cyan2]{task.description}", justify="left", style="cyan2"),
        BarColumn(bar_width=None, finished_style="cyan"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        SpinnerColumn(style="progress.data.speed"),
        HumanReadableSpeedColumn(),
        "•",
        TextColumn(
            "[bold cyan2]{task.completed:>02d}[/]/[bold cyan2]{task.fields[rendered_total]}[/]",
            justify="left",
            style="cyan2",
        ),
        SpinnerColumn(style="cyan2"),
        "•",
        TimeRemainingColumn(),
        console=console,
        transient=True,
        refresh_per_second=10,
        expand=True,
    )


@dataclass
class ChapterProgressManager:
    """
    Manages the progress of chapter downloads in a webtoon downloader.

    Responsible for adding, updating, and completing tasks associated with each chapter's download process.

    Attributes:
        progress: The rich progress object used to display the download progress.
    """

    progress: Progress
    series_download_task: TaskID

    _task_ids: dict[int, ChapterTask] = field(init=False)

    def __post_init__(self) -> None:
        self._task_ids = {}

    async def on_webtoon_fetched(self, chapters: Sequence[ChapterInfo]) -> None:
        """
        Callback function to update the progress bar when a webtoon's chapters are fetched.

        Updates the task in the progress bar with the total number of chapters fetched,

        Args:
            chapters    : List of chapters that have been fetched.
            progress    : The progress bar instance to update.
            task        : The ID of the task in the progress bar being updated.
        """
        total_chapters = len(chapters)
        self.progress.update(self.series_download_task, total=total_chapters, rendered_total=f"{total_chapters:02}")

    async def advance_progress(
        self,
        chapter_info: ChapterInfo,
        progress_type: ChapterProgressType,
        extractor: WebtoonViewerPageExtractor | None,
    ) -> None:
        """
        Advance the progress of a chapter download based on its current state.

        Args:
            chapter_info    : Information about the chapter being downloaded.
            progress_type   : The type of progress update to process.
            extractor       : The extractor used for the chapter, if applicable.
        """
        if progress_type == "Start":
            self._add_task(chapter_info)
        elif progress_type == "ChapterInfoFetched" and extractor:
            total = len(extractor.get_img_urls())
            self._update_task(chapter_info, total)
        elif progress_type == "PageCompleted":
            self._start_task(chapter_info)
            self._progress_task(chapter_info)
        elif progress_type == "Completed":
            await self._complete_task(chapter_info)

    def _add_task(self, chapter_info: ChapterInfo) -> None:
        """Add a new progress task for a chapter."""
        task_id = self.progress.add_task(
            f"[plum2]Chapter {chapter_info.number}.",
            type="Pages",
            type_color="grey85",
            number_format=">02d",
            start=False,
            rendered_total="??",
        )
        self._task_ids[chapter_info.number] = ChapterTask(task_id, False)

    def _start_task(self, chapter_info: ChapterInfo) -> None:
        """Start the progress task for a chapter."""
        task = self._task_ids[chapter_info.number]
        if not task.started:
            self.progress.start_task(task.task)

    def _progress_task(self, chapter_info: ChapterInfo) -> None:
        """Advance the progress of a chapter's task by one step."""
        task = self._task_ids[chapter_info.number]
        self.progress.update(task.task, advance=1)

    def _update_task(self, chapter_info: ChapterInfo, total: int) -> None:
        """Update the progress task of a chapter with the total number of pages."""
        task = self._task_ids[chapter_info.number]
        self.progress.update(task.task, total=total, rendered_total=total)

    async def _complete_task(self, chapter_info: ChapterInfo) -> None:
        """Complete the progress task for a chapter and remove it from tracking."""
        task = self._task_ids[chapter_info.number]
        self.progress.update(self.series_download_task, advance=1)
        await asyncio.sleep(0.5)
        self.progress.remove_task(task.task)
        del self._task_ids[chapter_info.number]
