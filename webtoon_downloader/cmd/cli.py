from __future__ import annotations

import asyncio
import functools
import sys
from signal import SIGINT, SIGTERM
from typing import Any

import rich_click as click
from rich.progress import Progress

from webtoon_downloader import logger
from webtoon_downloader.cmd.exceptions import LatestWithStartOrEndError, SeparateOptionWithNonImageSaveAsError
from webtoon_downloader.cmd.progress import ChapterProgressManager, init_progress, on_webtoon_fetched
from webtoon_downloader.core.webtoon import downloader
from webtoon_downloader.core.webtoon.downloader import StorageType
from webtoon_downloader.core.webtoon.exporter import DataExporterFormat
from webtoon_downloader.transformers.image import ImageFormat

log, console = logger.setup()
help_config = click.RichHelpConfiguration(
    show_metavars_column=False,
    append_metavars_help=True,
    style_errors_suggestion="magenta italic",
    errors_suggestion="Try running '--help' for more information.",
)


def handle_deprecated_options(ctx: click.Context, param: click.Parameter, value: Any) -> Any:
    """Handler for deprecated options"""
    if param.name == "export_texts" and value:
        ctx.params["export_metadata"] = True
        log.warning("[bold][red]'--export-texts'[/red] is deprecated; use [green]'--export-metadata'[/green] instead.")
    elif param.name == "dest" and value is not None:
        ctx.params["out"] = value
        log.warning("[bold][red]'--dest'[/red] is deprecated; use [green]'--out'[/green] instead.")
    return value


async def download(progress: Progress, opts: downloader.WebtoonDownloadOptions) -> None:
    """The main download command"""
    with progress:
        try:
            await downloader.download_webtoon(opts)
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
    type=str,
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
    progress_manager = ChapterProgressManager(progress)
    series_download_task = progress.add_task(
        "[green]Downloading Chapters...",
        type="Chapters",
        type_color="grey93",
        number_format=">02d",
        rendered_total="??",
    )

    opts = downloader.WebtoonDownloadOptions(
        start=start,
        end=end,
        destination=out,
        export_texts=export_metadata,
        exporter_format=export_format,
        separate=separate,
        image_format=image_format,
        save_as=save_as,
        chapter_progress_callback=progress_manager.advance_progress,
        on_webtoon_fetched=functools.partial(on_webtoon_fetched, progress=progress, task=series_download_task),
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
