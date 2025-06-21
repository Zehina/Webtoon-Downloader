from __future__ import annotations

from typing import Any

import rich_click as click

from webtoon_downloader.core.exceptions import DownloadError, RateLimitedError


class CLIInvalidStartAndEndRangeError(click.UsageError):
    """
    This error is raised when the user provides a start that is greater than the end.

    Args:
        ctx: The Click context associated with the error, if any.
    """

    def __init__(self, ctx: click.Context | None = None) -> None:
        message = "Start chapter cannot be greater than end chapter."
        super().__init__(message, ctx)


class CLILatestWithStartOrEndError(click.UsageError):
    """
    This error is raised when the user attempts to use --latest in conjunction
    with either --start or --end options, which is not allowed due to their
    conflicting nature.

    Args:
        ctx: The Click context associated with the error, if any.
    """

    def __init__(self, ctx: click.Context | None = None) -> None:
        message = "Options --start/--end and --latest cannot be used together."
        super().__init__(message, ctx)


class CLISeparateOptionWithNonImageSaveAsError(click.UsageError):
    """
    This error is raised when the user attempts to use --separate with a save-as
    option other than 'images'. The --separate option is only compatible with
    saving chapters as individual images.

    Args:
        ctx: The Click context associated with the error, if any.
    """

    def __init__(self, ctx: click.Context | None = None) -> None:
        message = "Option --separate is only compatible with --save-as 'images'."
        super().__init__(message, ctx)


class CLIDeprecatedOptionError(click.UsageError):
    """
    Custom error for handling deprecated options in the CLI.
    """

    def __init__(self, deprecated_option: str, use_instead_option: str):
        message = f"{deprecated_option} is deprecated; use {use_instead_option} instead."
        super().__init__(message)


class CLIInvalidConcurrentCountError(click.BadParameter):
    """
    Custom error for handling invalid value for concurrent workers in the CLI.
    """

    def __init__(self, value: Any):
        message = f"Invalid value for concurrent workers {value}."
        super().__init__(message)


def handle_deprecated_options(_: click.Context, param: click.Parameter, value: Any) -> None:
    """Handler for deprecated options"""
    if param.name == "export_texts" and value:
        raise CLIDeprecatedOptionError(deprecated_option="--export-texts", use_instead_option="--export-metadata")
    elif param.name == "dest" and value is not None:
        raise CLIDeprecatedOptionError(deprecated_option="--dest", use_instead_option="--out")


def is_root_cause_rate_limit_error(exc: Exception | None) -> bool:
    if not isinstance(exc, DownloadError) and not isinstance(exc, RateLimitedError):
        return False

    if isinstance(exc, RateLimitedError):
        return True

    # Traverse the cause chain
    return is_root_cause_rate_limit_error(exc.cause)
