import logging
import requests
import rich
import os
import pathlib
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass, field
from options import Options
from concurrent.futures import as_completed, ThreadPoolExecutor
from webtoon_session import WebtoonSession, Series, ChapterInfo
from download_details import DownloadSettings
from rich.progress import (
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    Progress, 
    TextColumn, 
    TimeRemainingColumn,
    ProgressColumn,
    SpinnerColumn
)
from rich.markdown import Markdown
from rich.text import Text
from rich.style import Style
from rich.console import Console
from rich.logging import RichHandler

class CustomTransferSpeedColumn(ProgressColumn):
    """Renders human readable transfer speed."""

    def render(self, task: "Task") -> Text:
        """Show data transfer speed."""
        speed = task.finished_speed or task.speed
        if speed is None:
            return Text(f"?", style="progress.data.speed", justify='center')
        return Text(f"{task.speed:2.0f} {task.fields.get('type')}/s", style="progress.data.speed", justify='center')

progress = Progress(    
    TextColumn("{task.description}", justify="right"),
    BarColumn(bar_width=None),
    "[progress.percentage]{task.percentage:>3.2f}%",
    "•",
    SpinnerColumn(style="progress.data.speed"),
    CustomTransferSpeedColumn(),
    "•",
    TextColumn("[green]{task.completed:>02d}[/]/[bold green]{task.fields[rendered_total]}[/]", justify="left"),
    SpinnerColumn(),
    "•",
    TimeRemainingColumn(),
    transient=True,
    refresh_per_second=20
)
######################## Log Configuration ################################
console = Console()
logging.getLogger("urllib3").setLevel(logging.CRITICAL)
log = logging.getLogger(__name__)
FORMAT = "%(message)s"
LOG_FILENAME = 'webtoon_downloader.log'

logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", 
    handlers=[RichHandler(
        console=progress.console, 
        rich_tracebacks=True, 
        tracebacks_show_locals= True, 
        markup=True
    )]
)
###########################################################################

n_concurrent_chapters_download = 2

class WebtoonDownloader:
    def __init__(self, series: Series, download_settings: DownloadSettings):
        self.series = series
        self.download_settings = download_settings
        self.session = WebtoonSession(download_settings)

def main():
    parser = Options()
    parser.initialize()
    try:
        args = parser.parse()
    except Exception as e:
        console.print(f'[red]Error:[/] {e}')
        return -1
    if args.readme:
        parent_path = pathlib.Path(__file__).parent.parent.resolve()     
        with open(os.path.join(parent_path, "README.md")) as readme:
            markdown = Markdown(readme.read())
            console.print(markdown)
            return
    series_url = args.url
    separate = args.seperate or args.separate
    compress_cbz = args.cbz and separate
    webtoon_downloader = WebtoonSession(
        series= Series(series_url), 
        download_settings= DownloadSettings(
            start=args.start,
            end=args.end,
            dest=args.dest,
            images_format=args.images_format,
            latest=args.latest,
            separate=separate,
            compress=compress_cbz,
            max_concurrent=n_concurrent_chapters_download
        ),
        log=log,
        progress = progress
    )
    webtoon_downloader.download()

if(__name__ == '__main__'):
    main()