from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import re
import sys
from dataclasses import dataclass
from logging import FileHandler, Formatter, NullHandler
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Mapping, Pattern, Sequence

import aiofiles
import dacite
import httpx
import rich_click as click
from rich import traceback
from rich.console import Console
from rich.logging import RichHandler


class AsyncLogger:
    _queue: Queue = Queue(-1)
    _listener: QueueListener | None = None

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


@dataclass(slots=True, frozen=True)
class RewriteRule:
    """
    A single rewrite rule.
    """

    pattern: str | Pattern[str]
    """
    Glob/regex pattern that is matched against `LogRecord.name`.
    • If it contains *only* ASCII glob wild-cards (`*`, `?`, `[abc]`) we
        treat it as a glob (fast path via `fnmatch`).
    • Otherwise it is compiled as a full regex.
    """
    mapping: Mapping[int, int]
    """
    Dict that maps an *original* `levelno` → *new* `levelno`.
    Example:  {logging.INFO: logging.DEBUG}
    """

    def matches(self, logger_name: str) -> bool:
        if isinstance(self.pattern, re.Pattern):
            return bool(self.pattern.match(logger_name))
        return fnmatch.fnmatch(logger_name, self.pattern)


class LevelRewriteFilter(logging.Filter):
    """
    A `logging.Filter` that mutates `LogRecord`s in-place according to rules.

    >>> filter = LevelRewriteFilter.from_mapping({
    ...     "httpx*":      {logging.INFO: logging.DEBUG},
    ... })
    >>> handler.addFilter(filter)
    """

    def __init__(self, rules: Sequence[RewriteRule] | None = None) -> None:
        super().__init__()
        self.rules: list[RewriteRule] = list(rules) if rules else []

    @classmethod
    def from_mapping(
        cls,
        mapping: Mapping[str, Mapping[int, int]],
    ) -> LevelRewriteFilter:
        """Build from ``{pattern: {old_level: new_level}}`` mapping."""
        return cls([RewriteRule(pat, lvl_map) for pat, lvl_map in mapping.items()])

    def filter(self, record: logging.LogRecord) -> bool:
        for rule in self.rules:
            if rule.matches(record.name):
                if new := rule.mapping.get(record.levelno):
                    # mutate the record in-place
                    record.levelno = new
                    record.levelname = logging.getLevelName(new)
                # we stop after first match; delete `break` to allow fall-through
                break
        return True  # never veto records – we only mutate


def shutdown() -> None:
    AsyncLogger.shutdown()


def setup(
    log_level: int = logging.DEBUG,
    log_filename: str | None = None,
    enable_console_logging: bool = False,
    enable_traceback: bool = False,
) -> tuple[logging.Logger, Console]:
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
            log_time_format="[%H:%M:%S]",
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
        rewrite_filter = LevelRewriteFilter.from_mapping(
            {
                "httpx*": {logging.INFO: logging.DEBUG},
            }
        )
        queue_handler.addFilter(rewrite_filter)
        log.addHandler(queue_handler)

    # Optional: reduce noise from common libraries
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("hpack").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.INFO)
    logging.getLogger("click").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.INFO)
    logging.getLogger("aiofiles").setLevel(logging.INFO)

    if log_level < logging.INFO:
        log.warning("Logging level is %s", logging.getLevelName(log_level))

    if log_filename:
        log.info("Logging to %s", log_filename)

    return log, console
