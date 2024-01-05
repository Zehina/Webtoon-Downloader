from __future__ import annotations

import asyncio
import sys
from signal import SIGINT, SIGTERM

import rich_click as click
from rich.progress import Progress

from webtoon_downloader import logger
from webtoon_downloader.cmd.exceptions import (
    LatestWithStartOrEndError,
    SeparateOptionWithNonImageSaveAsError,
    handle_deprecated_options,
)
from webtoon_downloader.cmd.progress import ChapterProgressManager, init_progress
from webtoon_downloader.core.webtoon.downloaders import comic
from webtoon_downloader.core.webtoon.downloaders.options import StorageType, WebtoonDownloadOptions
from webtoon_downloader.core.webtoon.exporter import DataExporterFormat
from webtoon_downloader.transformers.image import ImageFormat

log, console = logger.setup()
help_config = click.RichHelpConfiguration(
    show_metavars_column=False,
    append_metavars_help=True,
    style_errors_suggestion="magenta italic",
    errors_suggestion="Try running '--help' for more information.",
)


async def download(progress: Progress, opts: WebtoonDownloadOptions) -> None:
    """The main download command"""
    with progress:
        try:
            await comic.download_webtoon(opts)
        except asyncio.CancelledError:
            if not progress:
                return
            progress.console.print("[bold red]Stopping Download[/]...")
            progress.console.print("[red]Download Stopped[/]!")


@click.command()
@click.version_option()
@click.pass_context
@click.rich_config(help_config=help_config)
@click.argument("url", required=True, type=str)
@click.option(
    "--start",
    "-s",
    type=int,
    help="Start chapter",
)
@click.option(
    "--end",
    "-e",
    type=int,
    help="End chapter",
)
@click.option(
    "--latest",
    "-l",
    is_flag=True,
    help="Download only the latest chapter",
)
@click.option(
    "--export-metadata",
    "-em",
    is_flag=True,
    help="Export texts like series summary, chapter name, or author notes into additional files",
)
@click.option(
    "--export-format",
    "-ef",
    type=click.Choice(["all", "json", "text"]),
    default="json",
    show_default=True,
    help="Format to store exported texts in",
)
@click.option(
    "--image-format",
    "-f",
    type=click.Choice(["jpg", "png"]),
    default="jpg",
    show_default=True,
    help="Image format of downloaded images",
)
@click.option(
    "--out",
    "-o",
    type=click.Path(file_okay=False, writable=True, resolve_path=True),
    help="Download parent folder path",
)
@click.option(
    "--save-as",
    "-s",
    type=click.Choice(["images", "zip", "cbz", "pdf"]),
    default="images",
    show_default=True,
    help="Choose the format to save each downloaded chapter",
)
@click.option(
    "--separate",
    is_flag=True,
    help="Download each chapter in separate folders",
)
@click.option(
    "--dest",
    callback=handle_deprecated_options,
    type=str,
    expose_value=False,
    hidden=True,
    help="[Deprecated] Use --out instead",
)
@click.option(
    "--export-texts",
    callback=handle_deprecated_options,
    is_flag=True,
    expose_value=False,
    hidden=True,
    help="[Deprecated] Use --export-metadata instead",
)
def cli(
    ctx: click.Context,
    url: str,
    start: int,
    end: int,
    latest: bool,
    out: str,
    image_format: ImageFormat,
    separate: bool,
    export_metadata: bool,
    export_format: DataExporterFormat,
    save_as: StorageType,
) -> None:
    loop = asyncio.get_event_loop()
    if not url:
        console.print(
            '[red]A Webtoon URL of the form [green]"https://www.webtoons.com/.../list?title_no=??"[/] of is required.'
        )
        ctx.exit(1)
    if latest and (start or end):
        raise LatestWithStartOrEndError(ctx)
    if separate and (save_as != "images"):
        raise SeparateOptionWithNonImageSaveAsError(ctx)

    progress = init_progress(console)
    series_download_task = progress.add_task(
        "Downloading Chapters...",
        type="Chapters",
        type_color="grey93",
        number_format=">02d",
        rendered_total="??",
    )

    progress_manager = ChapterProgressManager(progress, series_download_task)
    opts = WebtoonDownloadOptions(
        url=url,
        start=start,
        end=end,
        latest=latest,
        destination=out,
        export_metadata=export_metadata,
        exporter_format=export_format,
        separate=separate,
        image_format=image_format,
        save_as=save_as,
        chapter_progress_callback=progress_manager.advance_progress,
        on_webtoon_fetched=progress_manager.on_webtoon_fetched,
    )

    loop = asyncio.get_event_loop()
    main_task = asyncio.ensure_future(download(progress, opts))
    for signal in [SIGINT, SIGTERM]:
        loop.add_signal_handler(signal, main_task.cancel)
    try:
        loop.run_until_complete(main_task)
    finally:
        loop.close()


def run() -> None:
    """CLI entrypoint"""
    if len(sys.argv) <= 1:
        sys.argv.append("--help")
    cli()  # pylint: disable=no-value-for-parameter
