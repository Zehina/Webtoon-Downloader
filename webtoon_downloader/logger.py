import asyncio
import logging
import tempfile
from logging import FileHandler
from pathlib import Path
from typing import Tuple

import aiofiles
import httpx
import rich_click as click
from rich import traceback
from rich.console import Console
from rich.logging import RichHandler


def setup() -> Tuple[logging.Logger, Console]:
    """
    Sets up the logging system and a rich console for the application.

    Initializes a rich console and configures the logging to output
    logs both to a file and to the console.

    Returns:
        The configured logger and the rich console object.
    """
    console = Console()
    traceback.install(
        console=console,
        show_locals=False,
        suppress=[
            click,
            httpx,
            aiofiles,
            asyncio,
        ],
    )
    log = logging.getLogger(__name__)
    log.setLevel(logging.DEBUG)

    file_format = "%(asctime)s - %(levelname)-8s - %(message)s - %(filename)s - %(lineno)d - %(name)s"
    log_filename = Path(tempfile.gettempdir()) / "webtoon_downloader.log"

    # Create file handler for logging
    file_handler = FileHandler(log_filename, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(file_format))

    # Create console handler with a higher log level
    console_handler = RichHandler(console=console, level=logging.WARNING, rich_tracebacks=True, markup=True)
    log.addHandler(file_handler)
    log.addHandler(console_handler)

    return log, console
