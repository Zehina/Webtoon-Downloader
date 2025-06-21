import asyncio
import json
import logging
import sys
from logging import FileHandler, Formatter, NullHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Optional, Tuple

import aiofiles
import dacite
import httpx
import rich_click as click
from rich import traceback
from rich.console import Console
from rich.logging import RichHandler


class AsyncLogger:
    _queue: Queue = Queue(-1)
    _listener: Optional[QueueListener] = None

    @classmethod
    def setup(cls, handlers: list[logging.Handler]) -> logging.Handler:
        queue_handler = QueueHandler(cls._queue)
        if cls._listener is None:
            cls._listener = QueueListener(cls._queue, *handlers, respect_handler_level=True)
            cls._listener.start()
        return queue_handler

    @classmethod
    def shutdown(cls) -> None:
        if cls._listener is not None:
            cls._listener.stop()
            cls._listener = None


def shutdown() -> None:
    AsyncLogger.shutdown()


def setup(
    log_level: int = logging.DEBUG,
    log_filename: Optional[str] = None,
    enable_console_logging: bool = False,
    enable_traceback: bool = False,
) -> Tuple[logging.Logger, Console]:
    """
    Sets up the logging system with non-blocking handlers and a rich console.

    Returns:
        Tuple of configured root logger and the rich Console instance.
    """
    suppress = [click, httpx, aiofiles, asyncio, json, dacite]
    console = Console()

    if not enable_traceback:
        sys.tracebacklimit = 0
    else:
        traceback.install(
            console=console,
            show_locals=False,
            suppress=suppress,
        )

    log = logging.getLogger()
    log.setLevel(log_level)

    handlers: list[logging.Handler] = []

    if enable_console_logging:
        console_handler = RichHandler(
            console=console,
            level=max(log_level, logging.INFO),  # Do not print debug messages in console
            rich_tracebacks=enable_traceback,
            markup=True,
            tracebacks_suppress=suppress,
        )
        handlers.append(console_handler)

    if log_filename:
        file_log_format = "%(asctime)s - %(levelname)-6s - [%(name)s] - %(message)s - %(filename)s - %(lineno)d"
        file_handler = FileHandler(log_filename, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(Formatter(file_log_format))
        handlers.append(file_handler)

    if not handlers:
        log.addHandler(NullHandler())
    else:
        queue_handler = AsyncLogger.setup(handlers)
        log.addHandler(queue_handler)

    # Optional: reduce noise from common libraries
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("click").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.INFO)
    logging.getLogger("aiofiles").setLevel(logging.INFO)

    return log, console
