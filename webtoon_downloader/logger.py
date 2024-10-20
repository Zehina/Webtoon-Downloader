import asyncio
import logging
import sys
from logging import FileHandler
from typing import Optional, Tuple

import aiofiles
import httpx
import rich_click as click
from rich import traceback
from rich.console import Console
from rich.logging import RichHandler


def setup(
    log_level: int = logging.DEBUG,
    log_filename: Optional[str] = None,
    enable_console_logging: bool = False,
    enable_traceback: bool = False,
) -> Tuple[logging.Logger, Console]:
    """
    Sets up the logging system and a rich console for the application.

    Initializes a rich console and configures the logging to output
    logs both to a file and to the console.

    Returns:
        The configured logger and the rich console object.
    """
    console = Console()
    if not enable_traceback:
        sys.tracebacklimit = 0
    else:
        traceback.install(
            console=console,
            show_locals=False,
            suppress=[click, httpx, aiofiles, asyncio],
        )

    log = logging.getLogger()
    log.setLevel(log_level)

    # Create the console handler
    if enable_console_logging:
        console_handler = RichHandler(console=console, level=log_level, rich_tracebacks=enable_traceback, markup=True)
        log.addHandler(console_handler)
    else:
        log.addHandler(logging.NullHandler())

    # Create the file handler for logging if a filename is provided
    if log_filename:
        file_log_format = "%(asctime)s - %(levelname)-6s - [%(name)s] - %(message)s - %(filename)s - %(lineno)d"
        file_handler = FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(file_log_format))
        log.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("click").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.INFO)
    logging.getLogger("aiofiles").setLevel(logging.INFO)

    return log, console
