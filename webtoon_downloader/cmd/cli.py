from __future__ import annotations

import asyncio
import contextlib
import signal
import sys
from typing import Any, Literal

import rich_click as click

import webtoon_downloader.cmd.exceptions
import webtoon_downloader.logger
from webtoon_downloader.cmd.exceptions import (
    CLIInvalidConcurrentCountError,
    CLIInvalidStartAndEndRangeError,
    CLILatestWithStartOrEndError,
    CLISeparateOptionWithNonImageSaveAsError,
)
from webtoon_downloader.cmd.progress import ChapterProgressManager, init_progress
from webtoon_downloader.core.exceptions import WebtoonDownloadError
from webtoon_downloader.core.webtoon.client import RetryStrategy
from webtoon_downloader.core.webtoon.downloaders import comic
from webtoon_downloader.core.webtoon.downloaders.options import (
    DEFAULT_CONCURENT_CHAPTER_DOWNLOADS,
    DEFAULT_CONCURENT_IMAGE_DOWNLOADS,
    StorageType,
    WebtoonDownloadOptions,
)
from webtoon_downloader.core.webtoon.exporter import DataExporterFormat
from webtoon_downloader.transformers.image import ImageFormat

help_config = click.RichHelpConfiguration(
    show_metavars_column=False,
    append_metavars_help=True,
    style_errors_suggestion="magenta italic",
    errors_suggestion="Try running '--help' for more information.",
)


class GracefulExit(SystemExit):
    code = 1


def validate_concurrent_count(ctx: Any, param: Any, value: int | None) -> int | None:  # pylint: disable=unused-argument
    if value is not None and value <= 0:
        raise CLIInvalidConcurrentCountError(value)

    return value


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
@click.option("--end", "-e", type=int, help="End chapter")
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
    "-sa",
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
    callback=webtoon_downloader.cmd.exceptions.handle_deprecated_options,
    type=str,
    expose_value=False,
    hidden=True,
    help="[Deprecated] Use --out instead",
)
@click.option(
    "--export-texts",
    callback=webtoon_downloader.cmd.exceptions.handle_deprecated_options,
    is_flag=True,
    expose_value=False,
    hidden=True,
    help="[Deprecated] Use --export-metadata instead",
)
@click.option(
    "--concurrent-chapters",
    type=int,
    default=DEFAULT_CONCURENT_CHAPTER_DOWNLOADS,
    callback=validate_concurrent_count,
    help="Number of workers for concurrent chapter downloads",
)
@click.option(
    "--concurrent-pages",
    type=int,
    default=DEFAULT_CONCURENT_IMAGE_DOWNLOADS,
    callback=validate_concurrent_count,
    help="Number of workers for concurrent image downloads. This value is shared between all concurrent chapter downloads.",
)
@click.option(
    "--proxy",
    type=str,
    help="proxy address to use for making requests. e.g. http://127.0.0.1:7890",
)
@click.option(
    "--retry-strategy",
    type=click.Choice(["exponential", "linear", "fixed", "none"]),
    default="exponential",
    show_default=True,
    help="Retry strategy for failed requests",
)
@click.option("--debug", type=bool, is_flag=True, help="Enable debug mode")
def cli(  # noqa: C901
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
    concurrent_chapters: int,
    concurrent_pages: int,
    proxy: str,
    retry_strategy: RetryStrategy | Literal["none"] | None,
    debug: bool,
) -> None:
    log, console = webtoon_downloader.logger.setup(
        log_filename="webtoon_downloader.log" if debug else None,
        enable_traceback=debug,
        enable_console_logging=debug,
    )

    loop = asyncio.get_event_loop()
    if not url:
        console.print(
            '[red]A Webtoon URL of the form [green]"https://www.webtoons.com/.../list?title_no=??"[/] of is required.'
        )
        ctx.exit(1)
    if latest and (start or end):
        raise CLILatestWithStartOrEndError(ctx)
    if separate and (save_as != "images"):
        raise CLISeparateOptionWithNonImageSaveAsError(ctx)
    if start is not None and end is not None and start > end:
        raise CLIInvalidStartAndEndRangeError(ctx)

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
        concurrent_chapters=concurrent_chapters,
        concurrent_pages=concurrent_pages,
        retry_strategy=retry_strategy if retry_strategy != "none" else None,
        proxy=proxy,
    )

    loop = asyncio.get_event_loop()

    async def _shutdown() -> None:
        """Cancel remaining tasks and stop the loop *quietly*."""
        if progress:
            progress.console.print("[bold red]Stopping Download...[/]")
            progress.console.print("[red]Download Stopped![/]")

        # ➊ cancel every other task that isn't the main task
        current = asyncio.current_task()
        tasks = {t for t in asyncio.all_tasks(loop) if t is not current}
        for t in tasks:
            t.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        loop.stop()
        raise GracefulExit

    def _raise_graceful_exit(*_: Any) -> None:
        exit_tasks = set()
        shutdown_task = loop.create_task(_shutdown())
        exit_tasks.add(shutdown_task)
        shutdown_task.add_done_callback(exit_tasks.discard)

    with progress:
        main_task = loop.create_task(comic.download_webtoon(opts))
        signal.signal(signal.SIGINT, _raise_graceful_exit)
        signal.signal(signal.SIGTERM, _raise_graceful_exit)
        progress.print("Press [bold]Ctrl+C[/] to stop the download early...")
        with contextlib.suppress(GracefulExit, asyncio.CancelledError):
            try:
                loop.run_until_complete(main_task)
                progress.print("Download complete!")
            except WebtoonDownloadError as exc:
                console.print(f"[red][bold]Download error:[/bold] {exc}[/]")
                if webtoon_downloader.cmd.exceptions.is_root_cause_rate_limit_error(exc.cause):
                    console.print(
                        "[red][bold]Oh no! We got rate limited 😔 ! Please consider using a proxy or use lower --concurrent-pages/-concurrent-chapters values[/bold][/]"
                    )

                log.exception("Download error")
            finally:
                log.info("Shutting down logger")
                webtoon_downloader.logger.shutdown()


def run() -> None:
    """CLI entrypoint"""
    if len(sys.argv) <= 1:
        sys.argv.append("--help")

    cli()  # pylint: disable=no-value-for-parameter
